# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import pymysql
from croniter import croniter

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.mysql.util import ManagedAuthConnectionMixin, connect_with_session_variables

if TYPE_CHECKING:
    from datadog_checks.mysql import MySql
    from datadog_checks.mysql.config import MySQLConfig
    from datadog_checks.mysql.config_models.instance import Query

EVENT_TRACK_TYPE = 'do-query-results'

MAX_RESULT_ROWS = 10_000
CRON_STARTUP_LOOKBACK_SECONDS = 300
DATABASE_NAME_PATTERN = re.compile(r'^[A-Za-z0-9_$]+$')

Mode = Literal["cron", "interval"]


@dataclass(frozen=True)
class DueQuery:
    query: Query
    scheduled_time: float
    mode: Mode


class MySQLDataObservability(ManagedAuthConnectionMixin, DBMAsyncJob):
    def __init__(self, check: MySql, config: MySQLConfig, connection_args_provider, uses_managed_auth=False):
        self._check = check
        self._config = config
        self._connection_args_provider = connection_args_provider
        self._uses_managed_auth = uses_managed_auth
        self._db_created_at = 0
        self._db = None
        self._last_execution: dict[int, float] = {}
        self._next_run: dict[int, float] = {}
        collection_interval = config.data_observability.collection_interval or 10
        super(MySQLDataObservability, self).__init__(
            check,
            rate_limit=1 / float(collection_interval),
            run_sync=config.data_observability.run_sync,
            enabled=config.data_observability.enabled,
            dbms="mysql",
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            job_name="data-observability",
            shutdown_callback=self._close_db_conn,
        )
        self._queries = self._filter_valid_queries(self._do_config.queries or ())

    @property
    def _do_config(self):
        return self._config.data_observability

    def _close_db_conn(self):
        if self._db:
            try:
                self._db.close()
            except Exception:
                self._log.debug("Failed to close data observability db connection", exc_info=1)
            finally:
                self._db = None

    def _get_do_connection(self):
        if self._should_reconnect_for_managed_auth():
            self._close_db_conn()

        if self._db:
            try:
                if not self._db.open:
                    self._close_db_conn()
                else:
                    self._db.ping(reconnect=False)
            except pymysql.err.Error:
                self._close_db_conn()

        if not self._db:
            conn_args = self._connection_args_provider()
            self._db = connect_with_session_variables(**conn_args)
            if self._uses_managed_auth:
                self._db_created_at = time.time()

        return self._db

    def _filter_valid_queries(self, queries) -> tuple[Query, ...]:
        valid = []
        for q in queries:
            if q.schedule:
                if not croniter.is_valid(q.schedule):
                    self._log.warning(
                        "Skipping DO query monitor_id=%d: invalid cron schedule %r",
                        q.monitor_id,
                        q.schedule,
                    )
                    continue
            elif not (q.interval_seconds and q.interval_seconds > 0):
                self._log.warning(
                    "Skipping DO query monitor_id=%d: neither schedule nor positive interval_seconds set",
                    q.monitor_id,
                )
                continue
            valid.append(q)
        return tuple(valid)

    def _get_due_queries(self) -> list[DueQuery]:
        now = time.time()
        due: list[DueQuery] = []
        for q in self._queries:
            if q.schedule:
                cached = self._next_run.get(q.monitor_id)
                if cached is None:
                    it = croniter(q.schedule, now)
                    prev_tick = it.get_prev(float)
                    self._next_run[q.monitor_id] = it.get_next(float)
                    if 0 < CRON_STARTUP_LOOKBACK_SECONDS and (now - prev_tick) < CRON_STARTUP_LOOKBACK_SECONDS:
                        due.append(DueQuery(q, prev_tick, "cron"))
                    continue
                if now >= cached:
                    due.append(DueQuery(q, cached, "cron"))
            else:
                last = self._last_execution.setdefault(q.monitor_id, now - q.interval_seconds)
                if now - last >= q.interval_seconds:
                    due.append(DueQuery(q, last + q.interval_seconds, "interval"))
        return due

    def _build_base_tags(self) -> list[str]:
        tags = [t for t in self._tags if not t.startswith('dd.internal')] if self._tags else []
        config_id = self._do_config.config_id
        if config_id:
            tags.append(f'config_id:{config_id}')
        tags.append('db_type:mysql')
        return tags

    def _use_database(self, cursor, dbname: str):
        if not DATABASE_NAME_PATTERN.match(dbname):
            raise pymysql.err.ProgrammingError(f"Invalid database name {dbname!r}")
        cursor.execute(f'USE `{dbname}`')

    def _is_connection_broken(self, conn: Any) -> bool:
        if not getattr(conn, 'open', True):
            return True
        try:
            conn.ping(reconnect=False)
        except pymysql.err.Error:
            return True
        return False

    def _execute_single_query(self, conn: Any, query_spec: Query) -> dict[str, Any]:
        """Execute a query, catching database errors per query."""
        monitor_id = query_spec.monitor_id
        start = time.time()
        try:
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")
            with conn.cursor() as cursor:
                self._use_database(cursor, query_spec.dbname)
                cursor.execute(query_spec.query)
                if cursor.description is None:
                    raise pymysql.err.ProgrammingError(
                        "Query returned no result set - only SELECT statements are supported"
                    )
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
        except pymysql.err.DatabaseError as e:
            if self._is_connection_broken(conn):
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
        return {
            'timestamp': int(time.time() * 1000),
            'config_id': self._do_config.config_id or '',
            'db_type': 'mysql',
            'db_host': self._check.reported_hostname,
            'db_port': self._config.port,
            'db_name': query_spec.dbname,
            'monitor_id': query_spec.monitor_id,
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            **result,
        }

    def run_job(self):
        due_queries = self._get_due_queries()
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()
        conn = self._get_do_connection()

        for due in due_queries:
            q = due.query
            tags = base_tags + [f'monitor_id:{q.monitor_id}']

            now_at_fire_start = time.time()
            result = self._execute_single_query(conn, q)

            now_at_fire_end = time.time()
            if due.mode == "cron":
                self._next_run[q.monitor_id] = croniter(q.schedule, now_at_fire_end).get_next(float)
            else:
                self._last_execution[q.monitor_id] = now_at_fire_end

            try:
                self._check.gauge(
                    'dd.mysql.data_observability.query_execution_time',
                    result['duration_s'],
                    tags=tags,
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                self._check.count(
                    'dd.mysql.data_observability.query_executions',
                    1,
                    tags=tags + [f'status:{result["status"]}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                self._check.gauge(
                    'dd.mysql.data_observability.query_fire_lateness_seconds',
                    max(0.0, now_at_fire_start - due.scheduled_time),
                    tags=tags + [f'mode:{due.mode}'],
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
            except Exception as e:
                self._log.exception(
                    "Failed to emit metrics/event for monitor_id=%d",
                    q.monitor_id,
                )
                self._check.count(
                    'dd.mysql.data_observability.emit_failures',
                    1,
                    tags=tags + [f'exc_class:{type(e).__name__}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
