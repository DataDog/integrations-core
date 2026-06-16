# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

from .statements import NOT_TRUNCATED, STMT_TEXT_LIMIT, TRUNCATED, UNKNOWN_TRUNCATED

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

DEFAULT_ACTIVITY_COLLECTION_INTERVAL = 10
DEFAULT_ACTIVITY_PAYLOAD_ROW_LIMIT = 3500

APPLICATION_HANDLE_QUERY = 'SELECT MON_GET_APPLICATION_HANDLE() AS application_handle FROM SYSIBM.SYSDUMMY1'

ACTIVITY_QUERY = """\
SELECT
    CURRENT TIMESTAMP AS now,
    A.APPLICATION_HANDLE,
    C.APPLICATION_ID,
    C.APPLICATION_NAME,
    C.SESSION_AUTH_ID,
    C.CLIENT_APPLNAME,
    A.UOW_ID,
    A.ACTIVITY_ID,
    A.COORD_MEMBER,
    A.LOCAL_START_TIME,
    A.ACTIVITY_STATE,
    A.ACTIVITY_TYPE,
    HEX(A.EXECUTABLE_ID) AS executable_id,
    A.STMT_PKG_CACHE_ID,
    A.TOTAL_ACT_TIME,
    A.TOTAL_ACT_WAIT_TIME,
    A.TOTAL_CPU_TIME,
    A.QUERY_COST_ESTIMATE,
    A.ROWS_READ,
    A.ROWS_RETURNED,
    A.EFFECTIVE_ISOLATION,
    SUBSTR(A.STMT_TEXT, 1, {stmt_text_limit}) AS stmt_text,
    LENGTH(A.STMT_TEXT) AS stmt_text_length
FROM TABLE(MON_GET_ACTIVITY(NULL, -2)) A
JOIN TABLE(MON_GET_CONNECTION(NULL, -2)) C
  ON C.APPLICATION_HANDLE = A.APPLICATION_HANDLE
 AND C.MEMBER = A.COORD_MEMBER
WHERE A.MEMBER = A.COORD_MEMBER
  AND A.APPLICATION_HANDLE <> ?
  AND A.STMT_TEXT IS NOT NULL
ORDER BY A.LOCAL_START_TIME ASC
FETCH FIRST {row_limit} ROWS ONLY
"""

UOW_QUERY = """\
SELECT
    APPLICATION_HANDLE,
    UOW_ID,
    WORKLOAD_OCCURRENCE_STATE,
    UOW_START_TIME,
    TOTAL_RQST_TIME,
    TOTAL_WAIT_TIME,
    TOTAL_APP_COMMITS,
    TOTAL_APP_ROLLBACKS
FROM TABLE(MON_GET_UNIT_OF_WORK(NULL, -1))
WHERE APPLICATION_HANDLE <> ?
"""

CONNECTION_COUNTS_QUERY = """\
SELECT
    C.APPLICATION_NAME AS application_name,
    C.SESSION_AUTH_ID AS user,
    U.WORKLOAD_OCCURRENCE_STATE AS state,
    COUNT(*) AS connections
FROM TABLE(MON_GET_UNIT_OF_WORK(NULL, -1)) U
JOIN TABLE(MON_GET_CONNECTION(NULL, -1)) C
  ON C.APPLICATION_HANDLE = U.APPLICATION_HANDLE
WHERE U.APPLICATION_HANDLE <> ?
GROUP BY C.APPLICATION_NAME, C.SESSION_AUTH_ID, U.WORKLOAD_OCCURRENCE_STATE
"""

ACTIVITY_ROW_KEYS = (
    'application_handle',
    'application_id',
    'application_name',
    'session_auth_id',
    'client_applname',
    'uow_id',
    'activity_id',
    'coord_member',
    'local_start_time',
    'activity_state',
    'activity_type',
    'executable_id',
    'stmt_pkg_cache_id',
    'total_act_time',
    'total_act_wait_time',
    'total_cpu_time',
    'query_cost_estimate',
    'rows_read',
    'rows_returned',
    'effective_isolation',
    'elapsed_time_msec',
    'workload_occurrence_state',
    'uow_start_time',
    'total_rqst_time',
    'total_wait_time',
    'total_app_commits',
    'total_app_rollbacks',
    'db',
    'statement',
    'query_signature',
    'query_truncated',
    'dd_tables',
    'dd_commands',
    'dd_comments',
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


class Db2StatementSamples(DBMAsyncJob):
    """Collect Db2 active query snapshots for DBM activity."""

    def __init__(self, check, config) -> None:
        self.log = check.log
        self._check = check
        self._config = config
        activity_config = config.activity_config
        self._activity_collection_interval = _positive_float(
            activity_config.get('collection_interval'), DEFAULT_ACTIVITY_COLLECTION_INTERVAL
        )
        self._activity_enabled = config.dbm_enabled and is_affirmative(activity_config.get('enabled', True))
        self._activity_payload_row_limit = _positive_int(
            activity_config.get('payload_row_limit'), DEFAULT_ACTIVITY_PAYLOAD_ROW_LIMIT
        )
        self._conn_key_prefix = 'dbm-query-activity-'
        self._agent_application_handle: Any | None = None
        self._obfuscate_options = config.obfuscator_options
        self.tags: list[str] = []

        super().__init__(
            check,
            run_sync=is_affirmative(activity_config.get('run_sync', False)),
            enabled=self._activity_enabled,
            expected_db_exceptions=(),
            min_collection_interval=config.min_collection_interval,
            dbms='db2',
            rate_limit=1 / self._activity_collection_interval,
            job_name='query-activity',
            shutdown_callback=self._close_db_conn,
        )

    def _close_db_conn(self) -> None:
        self._check.connection.close(self._conn_key_prefix)

    def run_job(self) -> None:
        source_tags = self._tags or self._check.tag_manager.get_tags()
        self.tags = [tag for tag in source_tags if not tag.startswith('dd.internal')]
        if not self._activity_enabled:
            return

        self._collect_query_activity()

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_query_activity(self) -> None:
        try:
            application_handle = self._get_agent_application_handle()
            activity_rows = self._get_activity_rows(application_handle)
            uow_rows = self._get_uow_rows(application_handle)
            normalized_rows = self._normalize_activity_rows(activity_rows, uow_rows)
            connections = self._get_connection_counts(application_handle)
            self._submit_activity_event(normalized_rows, connections)
        except Exception as e:
            self.log.warning('Unable to collect Db2 query activity: %s', e)
            self._check.count(
                'dd.db2.query_activity.error',
                1,
                tags=self.tags + ['error:database-{}'.format(type(e).__name__)] + self._get_debug_tags(),
                hostname=self._check.reported_hostname,
                raw=True,
            )

    def _get_agent_application_handle(self) -> Any:
        if self._agent_application_handle is not None:
            return self._agent_application_handle

        rows, _ = self._check.connection.query(self._conn_key_prefix, APPLICATION_HANDLE_QUERY)
        if rows:
            self._agent_application_handle = _lowercase_row(rows[0]).get('application_handle')
        if self._agent_application_handle is None:
            self._agent_application_handle = 0
        return self._agent_application_handle

    def _get_activity_rows(self, application_handle: Any) -> list[dict[str, Any]]:
        rows, _ = self._check.connection.query(
            self._conn_key_prefix,
            ACTIVITY_QUERY.format(stmt_text_limit=STMT_TEXT_LIMIT, row_limit=self._activity_payload_row_limit),
            params=[application_handle],
        )
        return [_lowercase_row(row) for row in rows]

    def _get_uow_rows(self, application_handle: Any) -> dict[tuple[Any, Any], dict[str, Any]]:
        rows, _ = self._check.connection.query(self._conn_key_prefix, UOW_QUERY, params=[application_handle])
        return {
            (row.get('application_handle'), row.get('uow_id')): row for row in (_lowercase_row(row) for row in rows)
        }

    def _get_connection_counts(self, application_handle: Any) -> list[dict[str, Any]]:
        rows, _ = self._check.connection.query(
            self._conn_key_prefix,
            CONNECTION_COUNTS_QUERY,
            params=[application_handle],
        )
        return [_strip_none_values(_lowercase_row(row)) for row in rows]

    def _normalize_activity_rows(
        self, activity_rows: list[dict[str, Any]], uow_rows: dict[tuple[Any, Any], dict[str, Any]]
    ) -> list[dict[str, Any]]:
        normalized_rows = []
        for row in activity_rows:
            row.update(uow_rows.get((row.get('application_handle'), row.get('uow_id')), {}))
            row['db'] = self._config.db
            row['elapsed_time_msec'] = _elapsed_time_msec(row.get('now'), row.get('local_start_time'))
            row['query_truncated'] = _query_truncated(row.get('stmt_text'), row.get('stmt_text_length'))
            try:
                statement = obfuscate_sql_with_metadata(
                    row.get('stmt_text'), self._obfuscate_options, replace_null_character=True
                )
            except Exception as e:
                self.log.debug('Failed to obfuscate Db2 activity query | err=[%s]', e)
                self._check.count(
                    'dd.db2.query_activity.error',
                    1,
                    tags=self.tags + ['error:obfuscate-query-{}'.format(type(e).__name__)] + self._get_debug_tags(),
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                continue

            obfuscated_query = statement['query']
            row['statement'] = obfuscated_query
            row['query_signature'] = compute_sql_signature(obfuscated_query)
            metadata = statement['metadata']
            row['dd_tables'] = metadata.get('tables')
            row['dd_commands'] = metadata.get('commands')
            row['dd_comments'] = metadata.get('comments')
            normalized_rows.append(_to_activity_payload_row(row))
        return normalized_rows

    def _submit_activity_event(self, activity_rows: list[dict[str, Any]], connections: list[dict[str, Any]]) -> None:
        event = {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': datadog_agent.get_version(),
            'ddsource': 'db2',
            'dbm_type': 'activity',
            'collection_interval': self._activity_collection_interval,
            'ddtags': self.tags,
            'timestamp': time.time() * 1000,
            'cloud_metadata': self._check.cloud_metadata,
            'service': self._config.service,
            'db2_version': self._check.dbms_version,
            'db2_activity': activity_rows,
            'db2_connections': connections,
        }
        self._check.database_monitoring_query_activity(json.dumps(event, default=default_json_event_encoding))

    def _get_debug_tags(self) -> list[str]:
        if hasattr(self._check, '_get_debug_tags'):
            return self._check._get_debug_tags()
        return []


def _to_activity_payload_row(row: dict[str, Any]) -> dict[str, Any]:
    return _strip_none_values({key: row.get(key) for key in ACTIVITY_ROW_KEYS})


def _lowercase_row(row: dict[str, Any]) -> dict[str, Any]:
    return {str(key).lower(): value for key, value in row.items()}


def _strip_none_values(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}


def _elapsed_time_msec(now: Any, local_start_time: Any) -> int | None:
    if not isinstance(now, datetime) or not isinstance(local_start_time, datetime):
        return None
    return max(int((now - local_start_time).total_seconds() * 1000), 0)


def _query_truncated(stmt_text: Any, stmt_text_length: Any) -> str:
    if stmt_text_length is None:
        return UNKNOWN_TRUNCATED
    try:
        return TRUNCATED if int(stmt_text_length) > STMT_TEXT_LIMIT else NOT_TRUNCATED
    except (TypeError, ValueError):
        if stmt_text:
            return TRUNCATED if len(stmt_text) >= STMT_TEXT_LIMIT else UNKNOWN_TRUNCATED
        return UNKNOWN_TRUNCATED
