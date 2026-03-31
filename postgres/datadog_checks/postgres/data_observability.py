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
    from datadog_checks.postgres.config_models.instance import InstanceConfig

EVENT_TRACK_TYPE = 'do-query-results'


class PostgresDataObservability(DBMAsyncJob):
    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self._check = check
        self._config = config.data_observability
        self._last_execution: dict[int, float] = {}
        super(PostgresDataObservability, self).__init__(
            check,
            rate_limit=1 / float(self._config.collection_interval),
            run_sync=self._config.run_sync,
            enabled=self._config.enabled,
            dbms="postgres",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="data-observability",
        )

    def _get_due_queries(self) -> list[Any]:
        queries = self._config.queries or ()
        now = time.time()
        due = []
        for q in queries:
            last_run = self._last_execution.get(q.monitor_id, 0.0)
            if now - last_run >= q.interval_seconds:
                due.append(q)
        return due

    def _build_base_tags(self) -> list[str]:
        tags = list(self._tags) if self._tags else []
        config_id = self._config.config_id
        if config_id:
            tags.append(f'config_id:{config_id}')
        tags.append('db_type:postgres')
        return tags

    def _execute_single_query(self, conn: Any, query_spec: Any) -> dict[str, Any]:
        """Execute a single query and return a structured result dict.

        Per-query statement_timeout is not set; the check's global query_timeout applies.
        """
        sql = query_spec.query
        monitor_id = query_spec.monitor_id
        start = time.time()
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [list(row) for row in cursor.fetchall()] if cursor.description else []
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
            duration = time.time() - start
            self._log.warning(
                "Query failed for monitor_id=%d (%.3fs): %s",
                monitor_id,
                duration,
                e,
            )
            return {
                'status': 'error',
                'columns': [],
                'rows': [],
                'row_count': 0,
                'duration_s': duration,
                'error': str(e),
            }

    def _build_event_payload(self, query_spec: Any, result: dict[str, Any]) -> dict[str, Any]:
        entity = query_spec.entity.model_dump(exclude_none=True, by_alias=True) if query_spec.entity else {}
        custom_fields = (
            query_spec.custom_sql_select_fields.model_dump(exclude_none=True)
            if query_spec.custom_sql_select_fields
            else None
        )
        pg_config = self._check._config
        return {
            'timestamp': int(time.time() * 1000),
            'config_id': self._config.config_id or '',
            'db_type': 'postgres',
            'db_host': pg_config.host,
            'db_port': pg_config.port,
            'db_name': pg_config.dbname,
            'monitor_id': query_spec.monitor_id,
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            'status': result['status'],
            'columns': result['columns'],
            'rows': result['rows'],
            'row_count': result['row_count'],
            'duration_s': result['duration_s'],
            'error': result['error'],
        }

    def run_job(self):
        due_queries = self._get_due_queries()
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()
        pg_config = self._check._config

        try:
            with self._check.db_pool.get_connection(pg_config.dbname) as conn:
                now = time.time()
                for q in due_queries:
                    tags = base_tags + [f'monitor_id:{q.monitor_id}']

                    result = self._execute_single_query(conn, q)

                    self._check.gauge(
                        'data_observability.query_execution_time',
                        result['duration_s'],
                        tags=tags,
                        hostname=self._check.reported_hostname,
                    )
                    self._check.gauge(
                        'data_observability.query_status',
                        1 if result['status'] == 'success' else 0,
                        tags=tags,
                        hostname=self._check.reported_hostname,
                    )

                    payload = self._build_event_payload(q, result)
                    raw_event = json.dumps(payload, default=default_json_event_encoding)
                    self._log.debug("Query result for monitor_id=%d: %s", q.monitor_id, raw_event)
                    self._check.event_platform_event(raw_event, EVENT_TRACK_TYPE)

                    self._last_execution[q.monitor_id] = now

        except Exception:
            self._log.exception("Data observability job execution failed")
            for q in due_queries:
                tags = base_tags + [f'monitor_id:{q.monitor_id}']
                self._check.gauge(
                    'data_observability.query_execution_time',
                    0,
                    tags=tags,
                    hostname=self._check.reported_hostname,
                )
                self._check.gauge(
                    'data_observability.query_status',
                    0,
                    tags=tags,
                    hostname=self._check.reported_hostname,
                )
