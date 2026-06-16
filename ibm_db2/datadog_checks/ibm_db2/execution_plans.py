# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import re
import time
from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from cachetools import TTLCache

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import RateLimitingTTLCache
from datadog_checks.base.utils.format import json as format_json
from datadog_checks.base.utils.tracking import tracked_method

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

DEFAULT_EXPLAINED_QUERIES_PER_HOUR_PER_QUERY = 60
DEFAULT_EXPLAINED_QUERIES_CACHE_MAXSIZE = 5000
DEFAULT_SAMPLES_PER_HOUR_PER_QUERY = 15
DEFAULT_SEEN_SAMPLES_CACHE_MAXSIZE = 10000
DEFAULT_EXPLAIN_ERRORS_CACHE_MAXSIZE = 5000
DEFAULT_EXPLAIN_ERRORS_CACHE_TTL = 7200
EXPLAIN_TABLE_TOOL_NAME = 'EXPLAIN'
EXPLAIN_SCHEMA_PATTERN = re.compile(r'^[A-Za-z][A-Za-z0-9_#$@]{0,127}$')
EXECUTABLE_ID_PATTERN = re.compile(r'^[0-9A-Fa-f]{64}$')
UNKNOWN_TRUNCATED = 'unknown'

PLAN_KEY_EXPLAIN_TABLES = (
    'EXPLAIN_ACTUALS',
    'EXPLAIN_ARGUMENT',
    'EXPLAIN_DIAGNOSTIC_DATA',
    'EXPLAIN_DIAGNOSTIC',
    'EXPLAIN_PREDICATE',
    'EXPLAIN_STREAM',
    'EXPLAIN_OPERATOR',
    'EXPLAIN_OBJECT',
    'EXPLAIN_STATEMENT',
)
RUN_KEY_EXPLAIN_TABLES = ('EXPLAIN_INSTANCE',)
EXECUTABLE_ID_TABLES = ('OBJECT_METRICS',)

PLAN_KEY_COLUMNS = (
    'explain_requester',
    'explain_time',
    'source_name',
    'source_schema',
    'source_version',
    'explain_level',
    'stmtno',
    'sectno',
)

RUN_KEY_COLUMNS = (
    'explain_requester',
    'explain_time',
    'source_name',
    'source_schema',
    'source_version',
)

PLAN_KEY_CONDITION = (
    'EXPLAIN_REQUESTER = ? AND EXPLAIN_TIME = ? AND SOURCE_NAME = ? AND SOURCE_SCHEMA = ? '
    'AND SOURCE_VERSION = ? AND EXPLAIN_LEVEL = ? AND STMTNO = ? AND SECTNO = ?'
)
RUN_KEY_CONDITION = (
    'EXPLAIN_REQUESTER = ? AND EXPLAIN_TIME = ? AND SOURCE_NAME = ? AND SOURCE_SCHEMA = ? AND SOURCE_VERSION = ?'
)


def agent_check_getter(dbm_job):
    return dbm_job._check


def _positive_float(value: Any, default: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _positive_int(value: Any, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class Db2ExecutionPlans:
    """Collect Db2 execution plans from EXPLAIN tables."""

    def __init__(self, check, config) -> None:
        self.log = check.log
        self._check = check
        self._config = config
        self._conn_key_prefix = 'dbm-query-plans-'
        query_samples_config = config.query_samples_config
        self._explain_schema = self._normalize_schema(
            query_samples_config.get('explain_schema') or config.username or 'DATADOG'
        )
        self._collect_raw_query_statement = bool((config.collect_raw_query_statement or {}).get('enabled', False))
        self._explained_statements_ratelimiter = RateLimitingTTLCache(
            maxsize=_positive_int(
                query_samples_config.get('explained_queries_cache_maxsize'),
                DEFAULT_EXPLAINED_QUERIES_CACHE_MAXSIZE,
            ),
            ttl=60
            * 60
            / _positive_float(
                query_samples_config.get('explained_queries_per_hour_per_query'),
                DEFAULT_EXPLAINED_QUERIES_PER_HOUR_PER_QUERY,
            ),
        )
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=_positive_int(
                query_samples_config.get('seen_samples_cache_maxsize'),
                DEFAULT_SEEN_SAMPLES_CACHE_MAXSIZE,
            ),
            ttl=60
            * 60
            / _positive_float(
                query_samples_config.get('samples_per_hour_per_query'),
                DEFAULT_SAMPLES_PER_HOUR_PER_QUERY,
            ),
        )
        self._explain_errors_cache = TTLCache(
            maxsize=_positive_int(
                query_samples_config.get('explain_errors_cache_maxsize'),
                DEFAULT_EXPLAIN_ERRORS_CACHE_MAXSIZE,
            ),
            ttl=_positive_float(
                query_samples_config.get('explain_errors_cache_ttl'),
                DEFAULT_EXPLAIN_ERRORS_CACHE_TTL,
            ),
        )
        self._explain_tables_ready = False

    def close(self) -> None:
        self._check.connection.close(self._conn_key_prefix)

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_plan_events(self, rows: Iterable[dict[str, Any]], tags_no_db: list[str]) -> list[dict[str, Any]]:
        events = []
        for row in rows:
            query_signature = row.get('query_signature')
            query_cache_key = (row.get('db'), query_signature)
            if query_signature in self._explain_errors_cache:
                continue
            if not self._explained_statements_ratelimiter.acquire(query_cache_key):
                continue

            plan_result = self._collect_plan(row)
            collection_errors = None
            if plan_result['error_code']:
                collection_errors = [{'code': plan_result['error_code'], 'message': plan_result['error_message']}]

            event = self._build_plan_event(row, tags_no_db, plan_result, collection_errors)
            sample_key = (
                row.get('db'),
                query_signature,
                plan_result.get('plan_signature'),
                tuple(error['code'] for error in collection_errors or []),
            )
            if self._seen_samples_ratelimiter.acquire(sample_key):
                events.append(event)
                raw_event = self._build_raw_plan_event(event, plan_result)
                if raw_event is not None:
                    events.append(raw_event)
        return events

    def _collect_plan(self, row: dict[str, Any]) -> dict[str, Any]:
        executable_id = row.get('executable_id')
        if not self._is_valid_executable_id(executable_id):
            return self._error_result(row, 'invalid_executable_id', 'executable_id is missing or invalid')

        try:
            self._ensure_explain_tables()
            run_key = self._explain_from_section(str(executable_id), row.get('member'))
            plan_key = self._read_plan_key(run_key)
            if not plan_key:
                return self._error_result(row, 'empty_plan', 'EXPLAIN_FROM_SECTION produced no operator rows')

            try:
                raw_plan = self._build_raw_plan(plan_key)
            finally:
                self._delete_explain_rows(plan_key, str(executable_id))

            if not raw_plan:
                return self._error_result(row, 'empty_plan', 'EXPLAIN_OPERATOR produced no plan tree')

            raw_plan_json = format_json.encode(raw_plan, sort_keys=True)
            normalized_plan = datadog_agent.obfuscate_sql_exec_plan(raw_plan_json, normalize=True)
            obfuscated_plan = datadog_agent.obfuscate_sql_exec_plan(raw_plan_json)
            plan_signature = compute_exec_plan_signature(normalized_plan)
            raw_plan_signature = compute_exec_plan_signature(raw_plan_json)

            return {
                'raw_plan': raw_plan_json,
                'raw_statement': row.get('stmt_text'),
                'obfuscated_plan': obfuscated_plan,
                'plan_signature': plan_signature,
                'raw_plan_signature': raw_plan_signature,
                'plan_key': plan_key,
                'error_code': None,
                'error_message': None,
            }
        except Exception as e:
            self._emit_error(row, 'database_error', e)
            self._explain_errors_cache[row.get('query_signature')] = True
            return self._error_result(row, 'database_error', _safe_error_message(e))

    def _ensure_explain_tables(self) -> None:
        if self._explain_tables_ready:
            return

        try:
            self._check.connection.query(
                self._conn_key_prefix,
                'SELECT 1 FROM {}.EXPLAIN_OPERATOR FETCH FIRST 0 ROWS ONLY'.format(self._explain_schema),
            )
            self._explain_tables_ready = True
            return
        except Exception as e:
            if not _has_sqlstate(e, ('42704', '42705')):
                raise

        try:
            self._check.connection.callproc(
                self._conn_key_prefix,
                'SYSPROC.SYSINSTALLOBJECTS',
                (EXPLAIN_TABLE_TOOL_NAME, 'C', None, self._explain_schema),
            )
        except Exception as e:
            if not _has_sqlstate(e, ('42710',)):
                raise

        self._check.connection.query(
            self._conn_key_prefix,
            'SELECT 1 FROM {}.EXPLAIN_OPERATOR FETCH FIRST 0 ROWS ONLY'.format(self._explain_schema),
        )
        self._explain_tables_ready = True

    def _explain_from_section(self, executable_id: str, member: Any) -> dict[str, Any] | None:
        result = self._check.connection.callproc(
            self._conn_key_prefix,
            'SYSPROC.EXPLAIN_FROM_SECTION',
            (
                bytes.fromhex(executable_id),
                'M',
                None,
                _int_or_default(member, -1),
                self._explain_schema,
                None,
                None,
                None,
                None,
                None,
            ),
        )
        return _extract_explain_run_key(result)

    def _read_plan_key(self, run_key: dict[str, Any] | None) -> dict[str, Any] | None:
        if run_key:
            return self._read_plan_key_for_run(run_key)
        return self._read_latest_plan_key()

    def _read_plan_key_for_run(self, run_key: dict[str, Any]) -> dict[str, Any] | None:
        query = """\
SELECT
    S.EXPLAIN_REQUESTER,
    S.EXPLAIN_TIME,
    S.SOURCE_NAME,
    S.SOURCE_SCHEMA,
    S.SOURCE_VERSION,
    S.EXPLAIN_LEVEL,
    S.STMTNO,
    S.SECTNO,
    S.STATEMENT_TEXT,
    S.TOTAL_COST,
    S.QUERY_DEGREE
FROM {schema}.EXPLAIN_STATEMENT S
WHERE {run_key_condition}
  AND EXISTS (
        SELECT 1
        FROM {schema}.EXPLAIN_OPERATOR O
        WHERE O.EXPLAIN_REQUESTER = S.EXPLAIN_REQUESTER
          AND O.EXPLAIN_TIME = S.EXPLAIN_TIME
          AND O.SOURCE_NAME = S.SOURCE_NAME
          AND O.SOURCE_SCHEMA = S.SOURCE_SCHEMA
          AND O.SOURCE_VERSION = S.SOURCE_VERSION
          AND O.EXPLAIN_LEVEL = S.EXPLAIN_LEVEL
          AND O.STMTNO = S.STMTNO
          AND O.SECTNO = S.SECTNO
  )
ORDER BY S.EXPLAIN_LEVEL DESC, S.STMTNO DESC, S.SECTNO DESC
FETCH FIRST 1 ROW ONLY
""".format(schema=self._explain_schema, run_key_condition=RUN_KEY_CONDITION)
        rows, _ = self._check.connection.query(self._conn_key_prefix, query, params=_run_key_params(run_key))
        if not rows:
            return None
        return _lowercase_row(rows[0])

    def _read_latest_plan_key(self) -> dict[str, Any] | None:
        query = """\
SELECT
    S.EXPLAIN_REQUESTER,
    S.EXPLAIN_TIME,
    S.SOURCE_NAME,
    S.SOURCE_SCHEMA,
    S.SOURCE_VERSION,
    S.EXPLAIN_LEVEL,
    S.STMTNO,
    S.SECTNO,
    S.STATEMENT_TEXT,
    S.TOTAL_COST,
    S.QUERY_DEGREE
FROM {schema}.EXPLAIN_STATEMENT S
WHERE RTRIM(S.EXPLAIN_REQUESTER) = CURRENT USER
  AND EXISTS (
        SELECT 1
        FROM {schema}.EXPLAIN_OPERATOR O
        WHERE O.EXPLAIN_REQUESTER = S.EXPLAIN_REQUESTER
          AND O.EXPLAIN_TIME = S.EXPLAIN_TIME
          AND O.SOURCE_NAME = S.SOURCE_NAME
          AND O.SOURCE_SCHEMA = S.SOURCE_SCHEMA
          AND O.SOURCE_VERSION = S.SOURCE_VERSION
          AND O.EXPLAIN_LEVEL = S.EXPLAIN_LEVEL
          AND O.STMTNO = S.STMTNO
          AND O.SECTNO = S.SECTNO
  )
ORDER BY S.EXPLAIN_TIME DESC
FETCH FIRST 1 ROW ONLY
""".format(schema=self._explain_schema)
        rows, _ = self._check.connection.query(self._conn_key_prefix, query)
        if not rows:
            return None
        return _lowercase_row(rows[0])

    def _build_raw_plan(self, plan_key: dict[str, Any]) -> dict[str, Any] | None:
        operators = self._get_plan_rows('EXPLAIN_OPERATOR', plan_key, 'OPERATOR_ID')
        if not operators:
            return None

        streams = self._get_plan_rows('EXPLAIN_STREAM', plan_key, 'STREAM_ID')
        predicates = self._get_plan_rows('EXPLAIN_PREDICATE', plan_key, 'OPERATOR_ID, PREDICATE_ID')
        plan = _assemble_plan(plan_key, operators, streams, predicates)
        return {'Plan': plan}

    def _get_plan_rows(self, table: str, plan_key: dict[str, Any], order_by: str) -> list[dict[str, Any]]:
        rows, _ = self._check.connection.query(
            self._conn_key_prefix,
            'SELECT * FROM {}.{} WHERE {} ORDER BY {}'.format(
                self._explain_schema, table, PLAN_KEY_CONDITION, order_by
            ),
            params=_plan_key_params(plan_key),
        )
        return [_lowercase_row(row) for row in rows]

    def _delete_explain_rows(self, plan_key: dict[str, Any], executable_id: str) -> None:
        plan_key_params = _plan_key_params(plan_key)
        for table in PLAN_KEY_EXPLAIN_TABLES:
            try:
                self._check.connection.execute(
                    self._conn_key_prefix,
                    'DELETE FROM {}.{} WHERE {}'.format(self._explain_schema, table, PLAN_KEY_CONDITION),
                    params=plan_key_params,
                )
            except Exception:
                self.log.debug(
                    'Unable to delete Db2 explain rows from %s.%s', self._explain_schema, table, exc_info=True
                )

        run_key_params = _run_key_params(plan_key)
        for table in RUN_KEY_EXPLAIN_TABLES:
            try:
                self._check.connection.execute(
                    self._conn_key_prefix,
                    'DELETE FROM {}.{} WHERE {}'.format(self._explain_schema, table, RUN_KEY_CONDITION),
                    params=run_key_params,
                )
            except Exception:
                self.log.debug(
                    'Unable to delete Db2 explain rows from %s.%s', self._explain_schema, table, exc_info=True
                )

        for table in EXECUTABLE_ID_TABLES:
            try:
                self._check.connection.execute(
                    self._conn_key_prefix,
                    "DELETE FROM {}.{} WHERE EXECUTABLE_ID = x'{}'".format(self._explain_schema, table, executable_id),
                )
            except Exception:
                self.log.debug(
                    'Unable to delete Db2 explain rows from %s.%s', self._explain_schema, table, exc_info=True
                )

    def _build_plan_event(
        self,
        row: dict[str, Any],
        tags_no_db: list[str],
        plan_result: dict[str, Any],
        collection_errors: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        row_tags = list(tags_no_db) + ['db:{}'.format(row.get('db'))]
        member = row.get('member')
        if member is not None:
            row_tags.append('member:{}'.format(member))

        plan_key = plan_result.get('plan_key') or {}
        plan = {
            'definition': plan_result.get('obfuscated_plan'),
            'signature': plan_result.get('plan_signature'),
            'collection_errors': collection_errors,
        }
        if self._collect_raw_query_statement and plan_result.get('plan_signature'):
            plan['raw_signature'] = plan_result.get('raw_plan_signature')

        return {
            'timestamp': time.time() * 1000,
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': datadog_agent.get_version(),
            'ddsource': 'db2',
            'ddtags': ','.join(row_tags),
            'dbm_type': 'plan',
            'cloud_metadata': self._check.cloud_metadata,
            'service': self._config.service,
            'db2_version': self._check.dbms_version,
            'db': {
                'instance': row.get('db'),
                'plan': plan,
                'query_signature': row.get('query_signature'),
                'resource_hash': row.get('query_signature'),
                'statement': row.get('query'),
                'metadata': {
                    'tables': row.get('dd_tables'),
                    'commands': row.get('dd_commands'),
                    'comments': row.get('dd_comments'),
                },
                'query_truncated': row.get('query_truncated', UNKNOWN_TRUNCATED),
            },
            'db2': {
                'executable_id': row.get('executable_id'),
                'section_type': row.get('section_type'),
                'member': member,
                'explain_schema': self._explain_schema,
                'explain_level': _strip(plan_key.get('explain_level')),
            },
        }

    def _build_raw_plan_event(self, event: dict[str, Any], plan_result: dict[str, Any]) -> dict[str, Any] | None:
        if not self._collect_raw_query_statement or not plan_result.get('raw_plan'):
            return None

        raw_event = copy.deepcopy(event)
        raw_event['dbm_type'] = 'rqp'
        raw_event['db']['statement'] = plan_result.get('raw_statement') or raw_event['db']['statement']
        raw_event['db']['plan']['definition'] = plan_result.get('raw_plan')
        raw_event['db']['plan']['raw_signature'] = plan_result.get('raw_plan_signature')
        return raw_event

    def _error_result(self, row: dict[str, Any], code: str, message: str) -> dict[str, Any]:
        if code != 'invalid_executable_id':
            self._explain_errors_cache[row.get('query_signature')] = True
        return {
            'raw_plan': None,
            'raw_statement': row.get('stmt_text'),
            'obfuscated_plan': None,
            'plan_signature': None,
            'raw_plan_signature': None,
            'plan_key': None,
            'error_code': code,
            'error_message': message,
        }

    def _emit_error(self, row: dict[str, Any], code: str, error: Exception) -> None:
        self._check.count(
            'dd.db2.query_samples.error',
            1,
            tags=['error:explain-{}-{}'.format(code, type(error).__name__)] + self._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )

    def _get_debug_tags(self) -> list[str]:
        if hasattr(self._check, '_get_debug_tags'):
            return self._check._get_debug_tags()
        return []

    @staticmethod
    def _is_valid_executable_id(executable_id: Any) -> bool:
        return isinstance(executable_id, str) and EXECUTABLE_ID_PATTERN.match(executable_id) is not None

    def _normalize_schema(self, schema: Any) -> str:
        schema = str(schema or '').strip()
        if EXPLAIN_SCHEMA_PATTERN.match(schema):
            return schema.upper()
        self.log.warning('Invalid Db2 explain schema %r, defaulting to the configured user schema', schema)
        return str(self._config.username or 'DATADOG').upper()


def _assemble_plan(
    plan_key: dict[str, Any],
    operators: list[dict[str, Any]],
    streams: list[dict[str, Any]],
    predicates: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes = {_int_or_default(row.get('operator_id'), 0): _operator_node(row) for row in operators}
    predicate_rows = defaultdict(list)
    for row in predicates:
        predicate_rows[_int_or_default(row.get('operator_id'), 0)].append(row)

    children_by_parent = defaultdict(list)
    child_ids = set()
    for row in streams:
        source_type = _strip(row.get('source_type'))
        target_type = _strip(row.get('target_type'))
        source_id = _int_or_default(row.get('source_id'), 0)
        target_id = _int_or_default(row.get('target_id'), 0)
        if target_type != 'O' or target_id not in nodes:
            continue

        stream_count = _to_float(row.get('stream_count'))
        if stream_count is not None:
            nodes[target_id].setdefault('Plan Rows', stream_count)

        object_name = _strip(row.get('object_name'))
        if object_name:
            nodes[target_id].setdefault('Relation Name', object_name)
            nodes[target_id].setdefault('Schema', _strip(row.get('object_schema')))

        if source_type == 'O' and source_id in nodes:
            children_by_parent[target_id].append(source_id)
            child_ids.add(source_id)

    for operator_id, node in nodes.items():
        predicate_texts = [_strip(row.get('predicate_text')) for row in predicate_rows.get(operator_id, [])]
        predicate_texts = [predicate for predicate in predicate_texts if predicate]
        if predicate_texts:
            node['Predicate'] = ' AND '.join(predicate_texts)

    for operator_id, node in nodes.items():
        children = [_clean_plan(nodes[child_id]) for child_id in sorted(children_by_parent.get(operator_id, []))]
        if children:
            node['Plans'] = children

    root_ids = sorted(set(nodes) - child_ids)
    if not root_ids:
        root_ids = sorted(nodes)
    root_plans = [_clean_plan(nodes[root_id]) for root_id in root_ids]
    if len(root_plans) == 1:
        plan = root_plans[0]
    else:
        plan = {'Node Type': 'Db2 Plan', 'Plans': root_plans}

    total_cost = _to_float(plan_key.get('total_cost'))
    if total_cost is not None:
        plan['Total Cost'] = total_cost
    query_degree = _int_or_none(plan_key.get('query_degree'))
    if query_degree is not None:
        plan['Query Degree'] = query_degree
    return _clean_plan(plan)


def _operator_node(row: dict[str, Any]) -> dict[str, Any]:
    node = {
        'Node Type': _strip(row.get('operator_type')),
        'Total Cost': _to_float(row.get('total_cost')),
        'IO Cost': _to_float(row.get('io_cost')),
        'CPU Cost': _to_float(row.get('cpu_cost')),
        'First Row Cost': _to_float(row.get('first_row_cost')),
        'Re Total Cost': _to_float(row.get('re_total_cost')),
        'Buffers': _to_float(row.get('buffers')),
        'operator_id': _int_or_none(row.get('operator_id')),
    }
    return _clean_plan(node)


def _clean_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in plan.items() if value is not None and value != []}


def _strip(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _int_or_default(value: Any, default: int) -> int:
    result = _int_or_none(value)
    return default if result is None else result


def _lowercase_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key).lower(): value for key, value in row.items()}


def _plan_key_params(plan_key: dict[str, Any]) -> list[Any]:
    return [plan_key.get(column) for column in PLAN_KEY_COLUMNS]


def _run_key_params(plan_key: dict[str, Any]) -> list[Any]:
    return [plan_key.get(column) for column in RUN_KEY_COLUMNS]


def _extract_explain_run_key(callproc_result: Any) -> dict[str, Any] | None:
    if not isinstance(callproc_result, tuple):
        return None

    offset = 1 if len(callproc_result) == 11 else 0
    if len(callproc_result) < offset + 10:
        return None

    run_key = {
        'explain_requester': callproc_result[offset + 5],
        'explain_time': callproc_result[offset + 6],
        'source_name': callproc_result[offset + 7],
        'source_schema': callproc_result[offset + 8],
        'source_version': callproc_result[offset + 9] or '',
    }
    if any(run_key[column] is None for column in ('explain_requester', 'explain_time', 'source_name', 'source_schema')):
        return None
    return run_key


def _has_sqlstate(error: Exception, sqlstates: tuple[str, ...]) -> bool:
    message = str(error)
    return any('SQLSTATE={}'.format(sqlstate) in message for sqlstate in sqlstates)


def _safe_error_message(error: Exception) -> str:
    return ' '.join(str(error).split())[:500] or type(error).__name__
