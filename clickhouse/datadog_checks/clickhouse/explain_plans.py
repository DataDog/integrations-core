# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json as stdlib_json
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

SUPPORTED_EXPLAIN_STATEMENTS = frozenset({'select', 'insert', 'with'})

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

        # Gates EXPLAIN execution per query_signature
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.explained_queries_cache_maxsize),
            ttl=plan_ttl,
        )
        # Deduplicates per (query_signature, plan_signature) to avoid re-emitting unchanged plans
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

    def _run_explain(self, statement: str) -> dict:
        """Execute EXPLAIN PLAN json = 1 and return the parsed plan as a dict."""
        explain_query = "EXPLAIN PLAN json = 1 " + statement
        rows = self._execute_query_fn(explain_query)
        if not rows:
            raise ValueError("EXPLAIN PLAN returned no rows")
        # ClickHouse returns the JSON plan across one or more text rows; join and parse
        plan_text = '\n'.join(str(row[0]) for row in rows if row)
        return stdlib_json.loads(plan_text)

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
            raw_plan = json.dumps(plan_dict)
            if isinstance(raw_plan, bytes):
                raw_plan = raw_plan.decode('utf-8')
            try:
                obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(raw_plan)
                normalized_plan = datadog_agent.obfuscate_sql_exec_plan(raw_plan, normalize=True)
                plan_signature = compute_exec_plan_signature(normalized_plan)
            except Exception as e:
                self._log.debug("Failed to obfuscate explain plan: %s", e)
                collection_errors.append({'code': DBExplainError.invalid_result.value, 'message': str(e)})
        elif error_code is not None:
            collection_errors.append({'code': error_code.value, 'message': error_msg or ''})

        if plan_signature:
            statement_plan_sig = (row.get('query_signature', ''), plan_signature)
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
        - _explained_statements_ratelimiter: limits EXPLAIN execution per query_signature
        - _seen_samples_ratelimiter: deduplicates per (query_signature, plan_signature)
        """
        for row in rows:
            query_signature = row.get('query_signature', '')
            if not query_signature:
                continue
            if not self._explained_statements_ratelimiter.acquire(query_signature):
                continue

            plan_event = self._collect_plan_for_statement(row, tags_no_db)
            if plan_event is not None:
                yield plan_event
