# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json as stdlib_json
import re
from enum import Enum
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import RateLimitingTTLCache
from datadog_checks.base.utils.serialization import json

SUPPORTED_EXPLAIN_STATEMENTS = frozenset({'select', 'with'})

_CLICKHOUSE_PLAN_STATS_KEYS = frozenset(
    {
        'Estimated Rows',
        'Estimated Cost',
        'Estimated Total Rows',
    }
)


def _normalize_clickhouse_plan(node: object) -> object:
    """Recursively strip cost/stats fields from a ClickHouse plan node."""
    if isinstance(node, dict):
        return {k: _normalize_clickhouse_plan(v) for k, v in node.items() if k not in _CLICKHOUSE_PLAN_STATS_KEYS}
    if isinstance(node, list):
        return [_normalize_clickhouse_plan(item) for item in node]
    return node


_FORMAT_SUFFIX_RE = re.compile(r'\s+FORMAT\s+\w+\s*$', re.IGNORECASE)

_SECONDS_PER_HOUR = 60 * 60


class DBExplainError(Enum):
    connection_error = 'connection_error'
    no_plans_possible = 'no_plans_possible'
    query_truncated = 'query_truncated'
    unknown_error = 'unknown_error'
    invalid_result = 'invalid_result'
    database_error = 'database_error'


class ClickhouseExplainPlans:
    """Collects execution plans for completed ClickHouse queries."""

    def __init__(self, check: ClickhouseCheck, config, execute_query_fn: Callable) -> None:
        self._check = check
        self._config = config
        self._log = check.log
        self._execute_query_fn = execute_query_fn

        plan_ttl = _SECONDS_PER_HOUR / float(config.explained_queries_per_hour_per_query)

        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.explained_queries_cache_maxsize),
            ttl=plan_ttl,
        )
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.seen_samples_cache_maxsize),
            ttl=plan_ttl,
        )

    def _can_explain_statement(self, statement: str) -> bool:
        """Return True if this statement type supports EXPLAIN PLAN."""
        if not statement:
            return False
        first_token = statement.strip().split()[0].lower()
        return first_token in SUPPORTED_EXPLAIN_STATEMENTS

    @staticmethod
    def _strip_format_clause(query: str) -> str:
        """Strip trailing FORMAT clause that clickhouse_connect appends to queries."""
        return _FORMAT_SUFFIX_RE.sub('', query)

    def _run_explain(self, statement: str) -> dict:
        """Execute EXPLAIN PLAN json = 1 and return the parsed plan as a dict."""
        statement = self._strip_format_clause(statement)
        explain_query = "EXPLAIN PLAN json = 1, indexes = 1, actions = 1 " + statement
        rows = self._execute_query_fn(explain_query)
        if not rows:
            raise ValueError("EXPLAIN PLAN returned no rows")
        plan_text = '\n'.join(str(row[0]) for row in rows if row)
        result = stdlib_json.loads(plan_text)
        if isinstance(result, list):
            if not result:
                raise ValueError("EXPLAIN PLAN returned empty JSON array")
            return result[0]
        return result

    def _run_explain_safe(self, row: dict) -> tuple[dict | None, DBExplainError | None, str | None]:
        """
        Run EXPLAIN for a row, returning (plan_dict, error_code, error_msg).

        Uses the obfuscated statement to check supportability and the raw query for execution.
        """
        obfuscated_statement = row.get('statement', '')
        if not self._can_explain_statement(obfuscated_statement):
            return None, DBExplainError.no_plans_possible, None

        raw_query = row.get('query', '')
        try:
            plan_dict = self._run_explain(raw_query)
            return plan_dict, None, None
        except Exception as e:
            self._log.debug(
                "Failed to collect explain plan for query_signature=%s: %s",
                row.get('query_signature', ''),
                e,
            )
            return None, DBExplainError.database_error, str(type(e))

    def _collect_plan_for_statement(self, row: dict, tags_no_db: list[str]) -> dict | None:
        """
        Build a plan event dict for a row.

        Returns None if the plan should not be emitted (unsupported, rate limited, or obfuscation failed).
        """
        plan_dict, error_code, error_msg = self._run_explain_safe(row)

        if error_code == DBExplainError.no_plans_possible:
            return None

        collection_errors: list[dict] = []
        obfuscated_plan: str | None = None
        plan_signature: str | None = None

        if plan_dict is not None:
            try:
                obfuscated_plan = json.dumps(plan_dict)
                if isinstance(obfuscated_plan, bytes):
                    obfuscated_plan = obfuscated_plan.decode('utf-8')
                normalized_plan = json.dumps(_normalize_clickhouse_plan(plan_dict))
                if isinstance(normalized_plan, bytes):
                    normalized_plan = normalized_plan.decode('utf-8')
                plan_signature = compute_exec_plan_signature(normalized_plan)
            except Exception as e:
                self._log.debug("Failed to serialize explain plan: %s", e)
                collection_errors.append({'code': DBExplainError.invalid_result.value, 'message': str(e)})
        elif error_code is not None:
            collection_errors.append({'code': error_code.value, 'message': error_msg or ''})

        if plan_signature:
            statement_plan_sig = (row.get('databases', ''), row.get('query_signature', ''), plan_signature)
            if not self._seen_samples_ratelimiter.acquire(statement_plan_sig):
                return None

        return {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddsource': 'clickhouse',
            'ddagentversion': datadog_agent.get_version(),
            'dbm_type': 'plan',
            'timestamp': row.get('event_time_microseconds', 0) / 1000,
            'ddtags': ','.join(tags_no_db),
            'db': {
                'instance': row.get('databases', ''),
                'query_signature': row.get('query_signature', ''),
                'statement': row.get('statement', ''),
                'plan': {
                    'definition': obfuscated_plan,
                    'signature': plan_signature,
                    'collection_errors': collection_errors if collection_errors else None,
                },
                'metadata': {
                    'tables': row.get('dd_tables'),
                    'commands': row.get('dd_commands'),
                },
            },
            'clickhouse': {
                'user': row.get('user', ''),
                'query_kind': row.get('query_kind', ''),
                'query_duration_ms': row.get('query_duration_ms', 0),
            },
        }

    def _collect_plans(self, rows: list[dict], tags_no_db: list[str]) -> Iterator[dict]:
        """
        Yield plan events for rows that pass rate limiting.

        Uses two caches:
        - _explained_statements_ratelimiter: limits EXPLAIN execution per (databases, query_signature)
        - _seen_samples_ratelimiter: deduplicates per (databases, query_signature, plan_signature)
        """
        for row in rows:
            query_signature = row.get('query_signature', '')
            if not query_signature:
                continue
            if not self._can_explain_statement(row.get('statement', '')):
                continue
            rate_limit_key = (row.get('databases', ''), query_signature)
            if not self._explained_statements_ratelimiter.acquire(rate_limit_key):
                continue

            plan_event = self._collect_plan_for_statement(row, tags_no_db)
            if plan_event is not None:
                yield plan_event
