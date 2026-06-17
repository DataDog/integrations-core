# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import math
import time
from typing import TYPE_CHECKING, Any

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding

from .connection import split_sqlserver_host_port

try:
    import pyodbc
except ImportError:
    pyodbc = None  # type: ignore[assignment]

try:
    import adodbapi
except ImportError:
    adodbapi = None

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer
    from datadog_checks.sqlserver.config_models.instance import InstanceConfig, Query

EVENT_TRACK_TYPE = 'do-query-results'

# Cap the number of rows fetched per query to prevent unbounded memory usage.
MAX_RESULT_ROWS = 10_000

CONN_KEY_PREFIX = "dbm-do-"

_EXPECTED_DB_EXCEPTIONS: list[type[Exception]] = []
if pyodbc is not None:
    _EXPECTED_DB_EXCEPTIONS.append(pyodbc.Error)
if adodbapi is not None:
    _EXPECTED_DB_EXCEPTIONS.append(adodbapi.DatabaseError)


class SqlServerDataObservability(DBMAsyncJob):
    def __init__(self, check: SQLServer, config: InstanceConfig):
        self._check = check
        self._config = config
        self._last_execution: dict[int, float] = {}
        collection_interval = config.data_observability.collection_interval or 10
        super(SqlServerDataObservability, self).__init__(
            check,
            rate_limit=1 / float(collection_interval),
            run_sync=config.data_observability.run_sync,
            enabled=config.data_observability.enabled,
            dbms="sqlserver",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=tuple(_EXPECTED_DB_EXCEPTIONS),
            job_name="data-observability",
        )

    def _shutdown(self):
        self._check = None

    @property
    def _do_config(self):
        return self._config.data_observability

    def _get_due_queries(self) -> list[Query]:
        queries = self._do_config.queries or ()
        now = time.time()
        due = []
        for q in queries:
            last_run = self._last_execution.get(q.monitor_id, 0.0)
            if now - last_run >= q.interval_seconds:
                due.append(q)
        return due

    def _build_base_tags(self) -> list[str]:
        tags = [t for t in self._tags if not t.startswith('dd.internal')] if self._tags else []
        config_id = self._do_config.config_id
        if config_id:
            tags.append(f'config_id:{config_id}')
        tags.append('db_type:sqlserver')
        return tags

    def _get_db_port(self) -> int | None:
        host = getattr(self._config, 'connection_host', None)
        if not host:
            return None
        _, port = split_sqlserver_host_port(host)
        try:
            return int(port) if port is not None else 1433
        except (ValueError, TypeError):
            return 1433

    def _execute_single_query(self, cursor: Any, query_spec: Query) -> dict[str, Any]:
        """Execute a query, catching pyodbc.Error per-query so the loop continues."""
        monitor_id = query_spec.monitor_id
        start = time.time()
        try:
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")
            cursor.execute(query_spec.query)
            # cursor.description is None when the query produced no result set
            # (e.g. INSERT, UPDATE, DELETE, or a syntax error that executed without
            # raising). RC-delivered queries must be SELECTs; treat this as a
            # per-query error so subsequent queries in the list still run.
            if cursor.description is None:
                raise (pyodbc.ProgrammingError if pyodbc else Exception)(
                    "Query returned no result set — only SELECT statements are supported"
                )
            columns = [d[0] for d in cursor.description]
            rows = [list(r) for r in cursor.fetchmany(MAX_RESULT_ROWS)]
            duration = time.time() - start
            return {
                'status': 'success',
                'columns': columns,
                'rows': rows,
                'row_count': len(rows),
                'duration_s': duration,
                'error': None,
            }
        except Exception as e:
            if not _EXPECTED_DB_EXCEPTIONS or not isinstance(e, tuple(_EXPECTED_DB_EXCEPTIONS)):
                raise
            duration = time.time() - start
            self._log.warning(
                "Query failed for monitor_id=%d (%.3fs): %s | SQL: %s",
                monitor_id,
                duration,
                e,
                query_spec.query,
            )
            return {
                'status': 'error',
                'columns': [],
                'rows': [],
                'row_count': 0,
                'duration_s': duration,
                'error': str(e),
            }

    def _build_event_payload(self, query_spec: Query, result: dict[str, Any]) -> dict[str, Any]:
        entity = query_spec.entity.model_dump(exclude_none=True, by_alias=True) if query_spec.entity else {}
        custom_fields = (
            query_spec.custom_sql_select_fields.model_dump(exclude_none=True)
            if query_spec.custom_sql_select_fields
            else None
        )
        payload: dict[str, Any] = {
            'timestamp': int(time.time() * 1000),
            'config_id': self._do_config.config_id or '',
            'db_type': 'sqlserver',
            'db_host': self._check.reported_hostname,
            'db_port': self._get_db_port(),
            'db_name': query_spec.dbname,
            'monitor_id': query_spec.monitor_id,
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            **result,
        }
        cloud_metadata = getattr(self._config, 'cloud_metadata', None)
        if cloud_metadata:
            payload['cloud_metadata'] = cloud_metadata
        return payload

    def run_job(self):
        # Connection errors propagate to _job_loop, which handles
        # expected_db_exceptions with retry semantics.
        due_queries = self._get_due_queries()
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()

        for q in due_queries:
            tags = base_tags + [f'monitor_id:{q.monitor_id}']

            with self._check.connection._open_managed_db_connections(
                self._check.connection.DEFAULT_DB_KEY,
                db_name=q.dbname,
                key_prefix=CONN_KEY_PREFIX,
            ):
                if q.query_timeout:
                    timeout_s = max(1, math.ceil(q.query_timeout / 1000))
                    self._check.connection.set_command_timeout(CONN_KEY_PREFIX, timeout_s, db_name=q.dbname)

                cursor = self._check.connection.get_cursor(
                    self._check.connection.DEFAULT_DB_KEY,
                    db_name=q.dbname,
                    key_prefix=CONN_KEY_PREFIX,
                )
                try:
                    result = self._execute_single_query(cursor, q)
                finally:
                    self._check.connection.close_cursor(cursor)

            # Update scheduling timestamp after execution, before metric/event emission,
            # so a serialization failure cannot cause infinite re-execution of the same query.
            self._last_execution[q.monitor_id] = time.time()

            try:
                self._check.gauge(
                    'dd.sqlserver.data_observability.query_execution_time',
                    result['duration_s'],
                    tags=tags,
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                self._check.count(
                    'dd.sqlserver.data_observability.query_executions',
                    1,
                    tags=tags + [f'status:{result["status"]}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )

                payload = self._build_event_payload(q, result)
                raw_event = json.dumps(payload, default=default_json_event_encoding)
                self._log.debug(
                    "Query result for monitor_id=%d: status=%s row_count=%d",
                    q.monitor_id,
                    result['status'],
                    result['row_count'],
                )
                self._check.event_platform_event(raw_event, EVENT_TRACK_TYPE)
            except Exception:
                self._log.exception(
                    "Failed to emit metrics/event for monitor_id=%d",
                    q.monitor_id,
                )
