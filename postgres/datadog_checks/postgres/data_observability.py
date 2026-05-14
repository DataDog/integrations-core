# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import psycopg
from croniter import croniter

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql
    from datadog_checks.postgres.config_models.instance import InstanceConfig, Query

EVENT_TRACK_TYPE = 'do-query-results'

MAX_RESULT_ROWS = 10_000

# After an agent start, run cron-scheduled queries whose scheduled time of execution
# fell within this many seconds in the past. Recovers missed runs across short check
# restarts (deploys, crashes, Remote Configuration redeliveries). Set to 0 to skip
# catch-up.
CRON_STARTUP_LOOKBACK_SECONDS = 300

Mode = Literal["cron", "interval"]


@dataclass(frozen=True)
class DueQuery:
    query: Query
    scheduled_time: float
    mode: Mode


class PostgresDataObservability(DBMAsyncJob):
    def __init__(self, check: PostgreSql, config: InstanceConfig):
        self._check = check
        self._config = config
        self._last_execution: dict[int, float] = {}  # interval mode: last fire timestamp
        self._next_run: dict[int, float] = {}  # cron mode: next fire time
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
        # Filter bad queries on check construction.
        self._queries = self._filter_valid_queries(self._do_config.queries or ())

    def _shutdown(self):
        self._check = None

    @property
    def _do_config(self):
        return self._config.data_observability

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
                    # Startup recovery: catch up if the previous tick fell within the lookback window.
                    if 0 < CRON_STARTUP_LOOKBACK_SECONDS and (now - prev_tick) < CRON_STARTUP_LOOKBACK_SECONDS:
                        due.append(DueQuery(q, prev_tick, "cron"))
                    continue
                if now >= cached:
                    due.append(DueQuery(q, cached, "cron"))
            else:
                # On first sight, backdate one interval so the first fire reports lateness = 0.
                last = self._last_execution.setdefault(q.monitor_id, now - q.interval_seconds)
                if now - last >= q.interval_seconds:
                    due.append(DueQuery(q, last + q.interval_seconds, "interval"))
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
        monitor_id = query_spec.monitor_id
        start = time.time()
        try:
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")
            with conn.cursor() as cursor:
                cursor.execute(query_spec.query)
                # cursor.description is None when the query produced no result set
                # (e.g. INSERT, UPDATE, DELETE, or a syntax error that executed without
                # raising). RC-delivered queries must be SELECTs; treat this as a
                # per-query error so subsequent queries in the list still run.
                if cursor.description is None:
                    raise psycopg.errors.ProgrammingError(
                        "Query returned no result set — only SELECT statements are supported"
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
            'db_type': 'postgres',
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
        # Connection errors (InterfaceError, OperationalError with broken conn) propagate
        # to _job_loop, which handles expected_db_exceptions with retry semantics.
        due_queries = self._get_due_queries()
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()

        for due in due_queries:
            q = due.query
            tags = base_tags + [f'monitor_id:{q.monitor_id}']

            now_at_fire_start = time.time()
            with self._check.db_pool.get_connection(q.dbname) as conn:
                result = self._execute_single_query(conn, q)

            # Advance scheduling state before emission so an emit-side error cannot
            # leave the query stuck re-firing the same tick.
            now_at_fire_end = time.time()
            if due.mode == "cron":
                self._next_run[q.monitor_id] = croniter(q.schedule, now_at_fire_end).get_next(float)
            else:
                self._last_execution[q.monitor_id] = now_at_fire_end

            try:
                self._check.gauge(
                    'dd.postgres.data_observability.query_execution_time',
                    result['duration_s'],
                    tags=tags,
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                self._check.count(
                    'dd.postgres.data_observability.query_executions',
                    1,
                    tags=tags + [f'status:{result["status"]}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )

                lateness = max(0.0, now_at_fire_start - due.scheduled_time)
                self._check.gauge(
                    'dd.postgres.data_observability.query_fire_lateness_seconds',
                    lateness,
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
                    'dd.postgres.data_observability.emit_failures',
                    1,
                    tags=tags + [f'exc_class:{type(e).__name__}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
