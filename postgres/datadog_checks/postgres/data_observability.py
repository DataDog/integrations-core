# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import psycopg

from datadog_checks.base.utils.cron import CronScheduler
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

# Fallback per-query statement timeout.
DEFAULT_DO_QUERY_TIMEOUT_S = 60

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
        self._last_execution: dict[int, float] = {}
        collection_interval = config.data_observability.collection_interval or 10
        super(PostgresDataObservability, self).__init__(
            check,
            rate_limit=1 / float(collection_interval),
            run_sync=config.data_observability.run_sync,
            enabled=config.data_observability.enabled,
            dbms=check.dbms,
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(psycopg.errors.DatabaseError,),
            job_name="data-observability",
        )
        # Filter bad queries on check construction.
        self._queries, self._schedulers = self._filter_valid_queries(self._do_config.queries or ())

    def _shutdown(self):
        self._check = None

    @property
    def _do_config(self):
        return self._config.data_observability

    def _filter_valid_queries(self, queries: Iterable[Query]) -> tuple[tuple[Query, ...], dict[int, CronScheduler]]:
        valid: list[Query] = []
        schedulers: dict[int, CronScheduler] = {}
        for q in queries:
            if q.schedule:
                try:
                    schedulers[q.monitor_id] = CronScheduler(q.schedule, startup_lookback=CRON_STARTUP_LOOKBACK_SECONDS)
                except (ValueError, TypeError) as e:
                    self._log.warning(
                        "Skipping DO query monitor_id=%d: invalid cron schedule %r (%s). "
                        "Check the schedule of Data Observability monitor %d.",
                        q.monitor_id,
                        q.schedule,
                        e,
                        q.monitor_id,
                    )
                    continue
            elif not (q.interval_seconds and q.interval_seconds > 0):
                self._log.warning(
                    "Skipping DO query monitor_id=%d: neither schedule nor positive interval_seconds set",
                    q.monitor_id,
                )
                continue
            valid.append(q)
        return tuple(valid), schedulers

    def _get_due_queries(self) -> list[DueQuery]:
        now = time.time()
        due: list[DueQuery] = []
        for q in self._queries:
            if q.schedule:
                # +0.001 so a poll landing exactly on a tick boundary is treated
                # as due (CronScheduler.previous_tick uses strict less-than).
                ticks = self._schedulers[q.monitor_id].due_ticks(now + 0.001)
                if ticks:
                    # Take the latest elapsed tick; earlier ones are already in the past
                    # and do not need separate execution.
                    due.append(DueQuery(q, ticks[-1], "cron"))
            else:
                last = self._last_execution.get(q.monitor_id)
                if last is None or now - last >= q.interval_seconds:
                    # Seed: treat first sight as if the previous interval just completed,
                    # so the scheduled_time for DueQuery is now and lateness is 0.
                    scheduled = (last + q.interval_seconds) if last is not None else now
                    due.append(DueQuery(q, scheduled, "interval"))
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
            # query_timeout is in milliseconds, matching the instance-level query_timeout unit.
            timeout_ms = query_spec.query_timeout
            # Pool connections run with autocommit=True, so the timeout must be
            # applied inside an explicit transaction and reverts on commit,
            # avoiding timeout leakage onto the shared connection.
            # set_config() is used instead of "SET LOCAL statement_timeout = %s"
            # because psycopg3 uses server-side binding (extended query protocol)
            # for parameterized execute() calls, and PostgreSQL rejects bound
            # parameters in SET statements under the extended protocol. set_config()
            # is a regular function that accepts parameters normally; is_local=true
            # gives the same scope as SET LOCAL (current transaction only).
            with conn.transaction():
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('statement_timeout', %s, true)",
                        (str(int(timeout_ms)),),
                    )
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
            # For cron mode, due_ticks() already advanced the scheduler's internal state.
            now_at_fire_end = time.time()
            if due.mode == "interval":
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

                # Lateness measures scheduling delay only (time from tick to query start),
                # not end-to-end result latency — query execution time is reported separately.
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
                try:
                    self._check.count(
                        'dd.postgres.data_observability.emit_failures',
                        1,
                        tags=tags + [f'exc_class:{type(e).__name__}'],
                        hostname=self._check.reported_hostname,
                        raw=True,
                    )
                except Exception:
                    pass
