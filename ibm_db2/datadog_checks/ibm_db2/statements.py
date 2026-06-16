# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import re
import time
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from cachetools import TTLCache

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

from .execution_plans import Db2ExecutionPlans

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

DEFAULT_COLLECTION_INTERVAL = 60
DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL = 10
DEFAULT_BATCH_MAX_CONTENT_SIZE = 20_000_000
STMT_TEXT_LIMIT = 16384
TRUNCATED = 'truncated'
NOT_TRUNCATED = 'not_truncated'
UNKNOWN_TRUNCATED = 'unknown'

PKG_CACHE_INTROSPECTION_QUERY = (
    'SELECT * FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1)) FETCH FIRST 0 ROWS ONLY'
)

PKG_CACHE_IDENTITY_COLUMNS = (
    'executable_id',
    'section_type',
    'member',
    'stmt_text',
)

PKG_CACHE_METRIC_COLUMNS = (
    'num_exec_with_metrics',
    'num_executions',
    'total_cpu_time',
    'stmt_exec_time',
    'coord_stmt_exec_time',
    'total_act_time',
    'total_act_wait_time',
    'lock_wait_time',
    'total_section_sort_time',
    'rows_read',
    'rows_returned',
    'rows_modified',
    'rows_inserted',
    'rows_updated',
    'rows_deleted',
    'pool_data_l_reads',
    'pool_data_p_reads',
    'pool_index_l_reads',
    'pool_index_p_reads',
    'direct_reads',
    'direct_writes',
    'total_sorts',
    'sort_overflows',
    'lock_waits',
    'lock_timeouts',
    'deadlocks',
)

PKG_CACHE_TIMING_COLUMNS = frozenset(
    {
        'total_cpu_time',
        'stmt_exec_time',
        'coord_stmt_exec_time',
        'total_act_time',
        'total_act_wait_time',
        'lock_wait_time',
        'total_section_sort_time',
    }
)
PKG_CACHE_REQUIRED_COLUMNS = frozenset({'executable_id', 'stmt_text', 'num_exec_with_metrics'})
PKG_CACHE_DESIRED_COLUMNS = frozenset(PKG_CACHE_IDENTITY_COLUMNS) | frozenset(PKG_CACHE_METRIC_COLUMNS)
MONITOR_METRICS_CONFIG_QUERY = (
    "SELECT NAME, VALUE FROM SYSIBMADM.DBCFG WHERE NAME IN ('mon_act_metrics', 'mon_req_metrics', 'mon_obj_metrics')"
)
EXECUTABLE_ID_PATTERN = re.compile(r'^[0-9A-Fa-f]+$')

STMT_TEXT_QUERY = """\
SELECT
    HEX(EXECUTABLE_ID) AS executable_id,
    SUBSTR(STMT_TEXT, 1, {stmt_text_limit}) AS stmt_text,
    LENGTH(STMT_TEXT) AS stmt_text_length
FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL, x'{executable_id}', NULL, -1))
FETCH FIRST 1 ROW ONLY
"""


def agent_check_getter(dbm_job):
    return dbm_job._check


def _row_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return row.get('executable_id'), row.get('member'), row.get('db')


def _positive_float(value: Any, default: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


class Db2StatementMetrics(DBMAsyncJob):
    """Collect query metrics from MON_GET_PKG_CACHE_STMT."""

    def __init__(self, check, config) -> None:
        self.log = check.log
        self._config = config
        self._check = check
        query_metrics_config = config.query_metrics_config
        query_samples_config = config.query_samples_config
        collection_interval = _positive_float(
            query_metrics_config.get('collection_interval'), DEFAULT_COLLECTION_INTERVAL
        )
        self._query_metrics_enabled = config.dbm_enabled and is_affirmative(query_metrics_config.get('enabled', True))
        self._query_samples_enabled = config.dbm_enabled and is_affirmative(query_samples_config.get('enabled', False))
        if not self._query_metrics_enabled:
            collection_interval = _positive_float(
                query_samples_config.get('collection_interval'), DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL
            )
        enabled = self._query_metrics_enabled or self._query_samples_enabled
        super().__init__(
            check,
            run_sync=(
                is_affirmative(query_metrics_config.get('run_sync', False))
                or is_affirmative(query_samples_config.get('run_sync', False))
            ),
            enabled=enabled,
            expected_db_exceptions=(),
            min_collection_interval=config.min_collection_interval,
            dbms='db2',
            rate_limit=1 / collection_interval,
            job_name='query-metrics',
            shutdown_callback=self._close_db_conn,
        )
        self._metrics_collection_interval = collection_interval
        self.batch_max_content_size = int(
            query_metrics_config.get('batch_max_content_size', DEFAULT_BATCH_MAX_CONTENT_SIZE)
        )
        self._max_statements = int(query_metrics_config.get('max_statements', 10000))
        self._state = StatementMetrics()
        self._conn_key_prefix = 'dbm-query-metrics-'
        self._pkg_cache_columns: list[str] = []
        self._metric_columns: list[str] = []
        self._timing_columns_enabled: bool | None = None
        self._obfuscate_options = config.obfuscator_options
        self._execution_plans = Db2ExecutionPlans(check, config)
        self._full_statement_text_cache = TTLCache(
            maxsize=int(query_metrics_config.get('full_statement_text_cache_max_size', 10000)),
            ttl=60
            * 60
            / _positive_float(query_metrics_config.get('full_statement_text_samples_per_hour_per_query'), 1),
        )

    def _close_db_conn(self) -> None:
        self._check.connection.close(self._conn_key_prefix)
        self._execution_plans.close()

    def run_job(self) -> None:
        source_tags = self._tags or self._check.tag_manager.get_tags()
        self.tags = [tag for tag in source_tags if not tag.startswith('dd.internal')]
        self._tags_no_db = [tag for tag in self.tags if not tag.startswith('db:')]
        self.collect_per_statement_metrics()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _submit_full_query_text_events(self, rows: Iterable[dict[str, Any]]) -> None:
        for event in self._rows_to_fqt_events(rows):
            self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

    @tracked_method(agent_check_getter=agent_check_getter)
    def _submit_query_plan_events(self, rows: Iterable[dict[str, Any]]) -> None:
        for event in self._execution_plans.collect_plan_events(rows, self._tags_no_db):
            self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

    @tracked_method(agent_check_getter=agent_check_getter)
    def _submit_query_metrics_payloads(self, rows: list[dict[str, Any]]) -> None:
        payload_wrapper = {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'timestamp': time.time() * 1000,
            'min_collection_interval': self._metrics_collection_interval,
            'tags': self._tags_no_db,
            'kind': 'query_metrics',
            'cloud_metadata': self._check.cloud_metadata,
            'db2_version': self._check.dbms_version,
            'ddagentversion': datadog_agent.get_version(),
            'service': self._config.service,
        }
        for payload in self._get_query_metrics_payloads(payload_wrapper, rows):
            self._check.database_monitoring_query_metrics(payload)

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_per_statement_metrics(self) -> None:
        try:
            rows = self._collect_metrics_rows()
            if not rows:
                return

            if self._query_metrics_enabled:
                self._submit_full_query_text_events(rows)

            if self._query_samples_enabled:
                self._submit_query_plan_events(rows)

            if self._query_metrics_enabled:
                self._submit_query_metrics_payloads(rows)
        except Exception as e:
            self._handle_collection_error(e)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_metrics_rows(self) -> list[dict[str, Any]]:
        rows = self._load_pkg_cache_stmt_rows()
        if not rows:
            return []

        rows = self._state.compute_derivative_rows(
            rows,
            self._metric_columns,
            key=_row_key,
            execution_indicators=['num_exec_with_metrics'],
        )
        rows = self._load_statement_text(rows)
        rows = self._normalize_queries(rows)
        rows = self._merge_by_query_signature(rows)
        self._check.gauge(
            'dd.db2.statement_metrics.query_rows',
            len(rows),
            tags=self.tags + self._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )
        return rows

    def _load_pkg_cache_stmt_rows(self) -> list[dict[str, Any]]:
        columns = self._get_pkg_cache_columns()
        missing_required_columns = PKG_CACHE_REQUIRED_COLUMNS - set(columns)
        if missing_required_columns:
            self.log.warning(
                'Unable to collect Db2 statement metrics because required columns are unavailable: %s',
                ', '.join(sorted(missing_required_columns)),
            )
            return []

        self._metric_columns = self._get_metric_columns(columns)
        desired_identity_columns = [column for column in PKG_CACHE_IDENTITY_COLUMNS if column != 'stmt_text']
        desired_columns = [column for column in desired_identity_columns if column in columns] + self._metric_columns

        select_columns = [self._column_select_sql(column) for column in desired_columns]
        query = (
            'SELECT {} FROM TABLE(MON_GET_PKG_CACHE_STMT(NULL, NULL, NULL, -1)) WHERE NUM_EXEC_WITH_METRICS > 0'.format(
                ', '.join(select_columns)
            )
        )
        if self._max_statements > 0:
            query = '{} ORDER BY NUM_EXEC_WITH_METRICS DESC FETCH FIRST {} ROWS ONLY'.format(
                query, self._max_statements
            )

        rows, _ = self._check.connection.query(self._conn_key_prefix, query)
        return [self._prepare_raw_row(row) for row in rows]

    def _load_statement_text(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not rows:
            return []

        rows_with_text = []
        for row in rows:
            statement_text = self._fetch_statement_text(row.get('executable_id'))
            if not statement_text:
                self.log.debug('Unable to fetch Db2 statement text for executable_id=%s', row.get('executable_id'))
                continue
            enriched_row = dict(row)
            enriched_row.update(statement_text)
            rows_with_text.append(enriched_row)
        return rows_with_text

    def _fetch_statement_text(self, executable_id: Any) -> dict[str, Any]:
        if executable_id is None:
            return {}

        executable_id = str(executable_id)
        if not EXECUTABLE_ID_PATTERN.match(executable_id):
            self.log.debug('Skipping Db2 statement text fetch for invalid executable_id=%s', executable_id)
            return {}

        query = STMT_TEXT_QUERY.format(executable_id=executable_id, stmt_text_limit=STMT_TEXT_LIMIT)
        rows, _ = self._check.connection.query(self._conn_key_prefix, query)
        if not rows:
            return {}

        statement_text = {str(key).lower(): value for key, value in rows[0].items()}
        statement_text['query_truncated'] = self._query_truncated(
            statement_text.get('stmt_text'), statement_text.get('stmt_text_length')
        )
        return statement_text

    def _get_pkg_cache_columns(self) -> list[str]:
        if self._pkg_cache_columns:
            return self._pkg_cache_columns

        _, columns = self._check.connection.query(self._conn_key_prefix, PKG_CACHE_INTROSPECTION_QUERY)
        available_columns = sorted(set(columns) & PKG_CACHE_DESIRED_COLUMNS)
        missing_columns = PKG_CACHE_DESIRED_COLUMNS - set(available_columns)
        if missing_columns:
            self.log.debug(
                'Missing expected MON_GET_PKG_CACHE_STMT columns: %s',
                ', '.join(sorted(missing_columns)),
            )
        self._pkg_cache_columns = available_columns
        return available_columns

    def _get_metric_columns(self, columns: list[str]) -> list[str]:
        available_metrics = [column for column in PKG_CACHE_METRIC_COLUMNS if column in columns]
        if self._get_timing_columns_enabled():
            return available_metrics
        return [column for column in available_metrics if column not in PKG_CACHE_TIMING_COLUMNS]

    def _get_timing_columns_enabled(self) -> bool:
        if self._timing_columns_enabled is not None:
            return self._timing_columns_enabled

        try:
            rows, _ = self._check.connection.query(self._conn_key_prefix, MONITOR_METRICS_CONFIG_QUERY)
        except Exception as e:
            self.log.debug('Unable to read Db2 monitor metric settings: %s', e)
            self._timing_columns_enabled = True
            return self._timing_columns_enabled

        settings = {str(row.get('name')).lower(): str(row.get('value')).upper() for row in rows}
        self._timing_columns_enabled = settings.get('mon_act_metrics') != 'NONE'
        if not self._timing_columns_enabled:
            self.log.warning(
                'Db2 statement timing metrics are disabled because mon_act_metrics is NONE. '
                'Set mon_act_metrics to BASE or EXTENDED to collect timing metrics.'
            )
        return self._timing_columns_enabled

    @staticmethod
    def _column_select_sql(column: str) -> str:
        if column == 'executable_id':
            return 'HEX(EXECUTABLE_ID) AS executable_id'
        if column == 'stmt_text':
            return 'SUBSTR(STMT_TEXT, 1, {}) AS stmt_text'.format(STMT_TEXT_LIMIT)
        return column

    def _prepare_raw_row(self, row: dict[str, Any]) -> dict[str, Any]:
        prepared = {str(key).lower(): value for key, value in row.items()}
        prepared['db'] = self._config.db
        for metric in self._metric_columns:
            prepared[metric] = self._coerce_metric_value(prepared.get(metric))
        if 'total_cpu_time' in prepared:
            prepared['total_cpu_time'] = prepared['total_cpu_time'] / 1000
        if 'stmt_text' in prepared or 'stmt_text_length' in prepared:
            prepared['query_truncated'] = self._query_truncated(
                prepared.get('stmt_text'), prepared.get('stmt_text_length')
            )
        return prepared

    @staticmethod
    def _coerce_metric_value(value: Any) -> Decimal | int | float:
        if value is None:
            return 0
        return value

    @staticmethod
    def _query_truncated(stmt_text: Any, stmt_text_length: Any) -> str:
        if stmt_text_length is None:
            return UNKNOWN_TRUNCATED
        try:
            return TRUNCATED if int(stmt_text_length) > STMT_TEXT_LIMIT else NOT_TRUNCATED
        except (TypeError, ValueError):
            if stmt_text:
                return TRUNCATED if len(stmt_text) >= STMT_TEXT_LIMIT else UNKNOWN_TRUNCATED
            return UNKNOWN_TRUNCATED

    def _normalize_queries(self, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized_rows = []
        for row in rows:
            normalized_row = dict(copy.copy(row))
            try:
                statement = obfuscate_sql_with_metadata(
                    row.get('stmt_text'), self._obfuscate_options, replace_null_character=True
                )
            except Exception as e:
                if self._config.log_unobfuscated_queries:
                    self.log.warning('Failed to obfuscate query=[%s] | err=[%s]', row.get('stmt_text'), e)
                else:
                    self.log.debug('Failed to obfuscate query | err=[%s]', e)
                self._check.count(
                    'dd.db2.statement_metrics.error',
                    1,
                    tags=self.tags + ['error:obfuscate-query-{}'.format(type(e).__name__)] + self._get_debug_tags(),
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                continue

            obfuscated_query = statement['query']
            normalized_row['query'] = obfuscated_query
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_query)
            metadata = statement['metadata']
            normalized_row['dd_tables'] = metadata.get('tables', None)
            normalized_row['dd_commands'] = metadata.get('commands', None)
            normalized_row['dd_comments'] = metadata.get('comments', None)
            normalized_rows.append(normalized_row)
        return normalized_rows

    def _merge_by_query_signature(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged_rows: dict[tuple[Any, ...], dict[str, Any]] = {}
        for row in rows:
            key = (row.get('query_signature'), row.get('db'))
            if key in merged_rows:
                existing_row = merged_rows[key]
                for metric in self._metric_columns:
                    existing_row[metric] = existing_row.get(metric, 0) + row.get(metric, 0)
            else:
                merged_rows[key] = dict(row)
        return list(merged_rows.values())

    @staticmethod
    def _to_metrics_payload_row(row: dict[str, Any]) -> dict[str, Any]:
        payload_row = dict(row)
        payload_row.pop('stmt_text', None)
        payload_row.pop('stmt_text_length', None)
        return payload_row

    def _get_query_metrics_payloads(self, payload_wrapper: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
        payloads = []
        queue = [rows]
        while queue:
            current = queue.pop()
            if not current:
                continue

            payload = copy.deepcopy(payload_wrapper)
            payload['db2_rows'] = [self._to_metrics_payload_row(row) for row in current]
            serialized_payload = json.dumps(payload, default=default_json_event_encoding)
            if len(serialized_payload) < self.batch_max_content_size:
                payloads.append(serialized_payload)
                continue

            if len(current) == 1:
                self.log.warning(
                    'A single Db2 query metrics row is too large to send to Datadog. This row will be dropped.'
                )
                continue

            midpoint = len(current) // 2
            queue.append(current[:midpoint])
            queue.append(current[midpoint:])
        return payloads

    def _rows_to_fqt_events(self, rows: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
        for row in rows:
            query_cache_key = (row.get('query_signature'), row.get('db'))
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True

            row_tags = list(self._tags_no_db) + ['db:{}'.format(row.get('db'))]
            member = row.get('member')
            if member is not None:
                row_tags.append('member:{}'.format(member))

            yield {
                'timestamp': time.time() * 1000,
                'host': self._check.reported_hostname,
                'database_instance': self._check.database_identifier,
                'ddagentversion': datadog_agent.get_version(),
                'ddsource': 'db2',
                'ddtags': ','.join(row_tags),
                'dbm_type': 'fqt',
                'cloud_metadata': self._check.cloud_metadata,
                'service': self._config.service,
                'db': {
                    'instance': row.get('db'),
                    'query_signature': row['query_signature'],
                    'resource_hash': row['query_signature'],
                    'statement': row['query'],
                    'metadata': {
                        'tables': row['dd_tables'],
                        'commands': row['dd_commands'],
                        'comments': row['dd_comments'],
                    },
                    'query_truncated': row.get('query_truncated', UNKNOWN_TRUNCATED),
                },
                'db2': {
                    'executable_id': row.get('executable_id'),
                    'section_type': row.get('section_type'),
                    'member': member,
                },
            }

    def _get_debug_tags(self) -> list[str]:
        if hasattr(self._check, '_get_debug_tags'):
            return self._check._get_debug_tags()
        return []

    def _handle_collection_error(self, error: Exception) -> None:
        self.log.warning('Unable to collect Db2 statement metrics: %s', error)
        self._check.count(
            'dd.db2.statement_metrics.error',
            1,
            tags=(getattr(self, 'tags', None) or [])
            + ['error:database-{}'.format(type(error).__name__)]
            + self._get_debug_tags(),
            hostname=self._check.reported_hostname,
            raw=True,
        )
