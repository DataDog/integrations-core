# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Any

import psycopg

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql
    from datadog_checks.postgres.config_models.instance import InstanceConfig, Query

EVENT_TRACK_TYPE = 'do-query-results'

# Cap the number of rows returned per query to prevent unbounded memory usage.
# Applied both at the database level (subquery LIMIT) and as a Python-side safety net.
MAX_RESULT_ROWS = 10_000


class PostgresDataObservability(DBMAsyncJob):
    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self._check = check
        self._config = config
        self._last_execution: dict[int, float] = {}
        collection_interval = config.data_observability.collection_interval or 10
        super(PostgresDataObservability, self).__init__(
            check,
            rate_limit=1 / float(collection_interval),
            run_sync=config.data_observability.run_sync,
            enabled=config.data_observability.enabled,
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="data-observability",
        )

    @property
    def _do_config(self):
        return self._config.data_observability

    def _get_due_queries(self) -> list[Any]:
        queries = self._do_config.queries or ()
        now = time.time()
        due = []
        for q in queries:
            last_run = self._last_execution.get(q.monitor_id, 0.0)
            if now - last_run >= q.interval_seconds:
                due.append(q)
        return due

    def _build_base_tags(self) -> list[str]:
        # self._tags is set by run_job_loop(tags) in the DBMAsyncJob parent; it may be
        # None if run_job() is called directly (e.g. in tests), so we guard with a fallback.
        tags = [t for t in self._tags if not t.startswith('dd.internal')] if self._tags else []
        config_id = self._do_config.config_id
        if config_id:
            tags.append(f'config_id:{config_id}')
        tags.append('db_type:postgres')
        return tags

    def _execute_single_query(self, conn: Any, query_spec: Query) -> dict[str, Any]:
        """Execute a query, catching DatabaseError per-query so the loop continues."""
        sql = query_spec.query.rstrip('; \t\n')
        monitor_id = query_spec.monitor_id
        # Wrap in a subquery to apply the row cap at the database level.
        limited_sql = f"SELECT * FROM ({sql}) _dd_row_limit LIMIT {MAX_RESULT_ROWS}"
        start = time.time()
        try:
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")
            with conn.cursor() as cursor:
                cursor.execute(limited_sql)
                columns = [desc[0] for desc in cursor.description]
                rows = [list(row) for row in cursor.fetchmany(MAX_RESULT_ROWS)]
            duration = time.time() - start
            return {
                'status': 'success',
                'columns': columns,
                'rows': rows,
                'row_count': len(rows),
                'duration_s': duration,
                'error': None,
            }
        except psycopg.errors.DatabaseError as e:
            # OperationalError is a subclass of DatabaseError. If the connection
            # is broken (server crash, network failure), re-raise so _job_loop
            # handles it with proper crash detection and health events.
            if conn.broken:
                raise
            duration = time.time() - start
            self._log.warning(
                "Query failed for monitor_id=%d (%.3fs): %s | SQL: %s",
                monitor_id,
                duration,
                e,
                sql,
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
        return {
            'timestamp': int(time.time() * 1000),
            'config_id': self._do_config.config_id or '',
            'db_type': 'postgres',
            'db_host': self._config.host,
            'db_port': self._config.port,
            'db_name': self._config.dbname,
            'monitor_id': query_spec.monitor_id,
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            **result,
        }

    def run_job(self):
        # Connection errors (InterfaceError, OperationalError with broken conn) propagate
        # to _job_loop, which handles expected_db_exceptions with retry semantics.
        due_queries = self._get_due_queries()
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()

        with self._check._get_main_db() as conn:
            now = time.time()
            for q in due_queries:
                tags = base_tags + [f'monitor_id:{q.monitor_id}']

                result = self._execute_single_query(conn, q)

                # Update scheduling timestamp immediately after execution, before
                # metric/event emission, so a serialization failure in the event
                # path cannot cause infinite re-execution of the same query.
                self._last_execution[q.monitor_id] = now

                try:
                    self._check.gauge(
                        'dd.postgres.data_observability.query_execution_time',
                        result['duration_s'],
                        tags=tags,
                        hostname=self._check.reported_hostname,
                        raw=True,
                    )
                    self._check.gauge(
                        'dd.postgres.data_observability.query_status',
                        1 if result['status'] == 'success' else 0,
                        tags=tags,
                        hostname=self._check.reported_hostname,
                        raw=True,
                    )

                    payload = self._build_event_payload(q, result)
                    raw_event = json.dumps(payload, default=default_json_event_encoding)
                    self._log.debug("Query result for monitor_id=%d: %s", q.monitor_id, raw_event)
                    self._check.event_platform_event(raw_event, EVENT_TRACK_TYPE)
                except Exception:
                    self._log.exception(
                        "Failed to emit metrics/event for monitor_id=%d",
                        q.monitor_id,
                    )
