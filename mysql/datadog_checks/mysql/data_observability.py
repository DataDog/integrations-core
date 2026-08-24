# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import pymysql

from datadog_checks.base.utils.cron import CronScheduler
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json

from .util import ManagedAuthConnectionMixin

if TYPE_CHECKING:
    from .config import MySQLConfig
    from .config_models.instance import DataObservability, Query
    from .mysql import MySql

EVENT_TRACK_TYPE = 'do-query-results'

MAX_RESULT_ROWS = 10_000

# Recover cron executions missed during short check restarts.
CRON_STARTUP_LOOKBACK_SECONDS = 300

DEFAULT_COLLECTION_INTERVAL_SECONDS = 10

DBNAME_PATTERN = re.compile(r'^[A-Za-z0-9_$]+$')

Mode = Literal["cron", "interval"]


@dataclass(frozen=True)
class DueQuery:
    query: Query
    scheduled_time: float
    mode: Mode


class MySQLDataObservability(ManagedAuthConnectionMixin, DBMAsyncJob):
    def __init__(
        self,
        check: MySql,
        do_config: DataObservability,
        config: MySQLConfig,
        connection_args_provider: Callable[[], Mapping[str, Any]],
        uses_managed_auth: bool = False,
    ) -> None:
        self._check = check
        self._do_config = do_config
        self._last_execution: dict[int, float] = {}
        # CronScheduler consumes a tick when it reports it. Keep due work here if
        # the connection fails so the next poll can retry the same execution.
        self._pending_retries: dict[int, DueQuery] = {}
        self._connection_args_provider = connection_args_provider
        self._uses_managed_auth = uses_managed_auth
        self._db_created_at = 0.0
        self._db: Any = None
        self._current_dbname: str | None = None
        self._current_query_timeout_ms: int | None = None

        collection_interval = do_config.collection_interval
        if not collection_interval or collection_interval <= 0:
            collection_interval = DEFAULT_COLLECTION_INTERVAL_SECONDS
        super().__init__(
            check,
            config_host=config.host,
            rate_limit=1 / float(collection_interval),
            run_sync=do_config.run_sync,
            enabled=do_config.enabled,
            dbms=check.dbms,
            min_collection_interval=config.min_collection_interval,
            expected_db_exceptions=(pymysql.err.DatabaseError,),
            shutdown_callback=self._close_db_conn,
            job_name="data-observability",
        )
        self._queries, self._schedulers = self._filter_valid_queries(do_config.queries or ())

    def _close_db_conn(self) -> None:
        db = self._db
        self._db = None
        self._current_dbname = None
        self._current_query_timeout_ms = None
        if db:
            try:
                db.close()
            except Exception:
                self._log.debug("Failed to close Data Observability database connection", exc_info=True)

    def _filter_valid_queries(self, queries: Iterable[Query]) -> tuple[tuple[Query, ...], dict[int, CronScheduler]]:
        valid: list[Query] = []
        schedulers: dict[int, CronScheduler] = {}
        for query in queries:
            try:
                self._validate_dbname(query.dbname)
            except ValueError as e:
                self._log.warning("Skipping DO query monitor_id=%d: %s", query.monitor_id, e)
                continue
            if query.schedule:
                try:
                    schedulers[query.monitor_id] = CronScheduler(
                        query.schedule, startup_lookback=CRON_STARTUP_LOOKBACK_SECONDS
                    )
                except (ValueError, TypeError) as e:
                    self._log.warning(
                        "Skipping DO query monitor_id=%d: invalid cron schedule %r (%s). "
                        "Check the schedule of Data Observability monitor %d.",
                        query.monitor_id,
                        query.schedule,
                        e,
                        query.monitor_id,
                    )
                    continue
            elif not (query.interval_seconds and query.interval_seconds > 0):
                self._log.warning(
                    "Skipping DO query monitor_id=%d: neither schedule nor positive interval_seconds set",
                    query.monitor_id,
                )
                continue
            valid.append(query)
        return tuple(valid), schedulers

    def _get_due_queries(self) -> list[DueQuery]:
        now = time.time()
        due: list[DueQuery] = []
        for query in self._queries:
            if query.schedule:
                ticks = self._schedulers[query.monitor_id].due_ticks(now + 0.001)
                if ticks:
                    due.append(DueQuery(query, ticks[-1], "cron"))
            else:
                last = self._last_execution.get(query.monitor_id)
                if last is None or now - last >= query.interval_seconds:
                    scheduled = last + query.interval_seconds if last is not None else now
                    due.append(DueQuery(query, scheduled, "interval"))
        return due

    def _build_base_tags(self) -> list[str]:
        tags = [tag for tag in self._tags if not tag.startswith('dd.internal')] if self._tags else []
        if self._do_config.config_id:
            tags.append(f'config_id:{self._do_config.config_id}')
        tags.append('db_type:mysql')
        return tags

    @staticmethod
    def _validate_dbname(dbname: str) -> str:
        if not DBNAME_PATTERN.fullmatch(dbname):
            raise ValueError(
                f"Invalid database name {dbname!r}: only letters, numbers, underscores, dollar signs are allowed"
            )
        return dbname

    def _set_query_timeout(self, conn: Any, query_timeout_ms: int) -> None:
        if not self._check.is_mariadb and not self._check.version.version_compatible((5, 7, 4)):
            # MySQL added max_execution_time in 5.7.4. Older supported servers
            # must still execute the monitor query without attempting to use it.
            return
        if query_timeout_ms == self._current_query_timeout_ms:
            return

        # This connection belongs only to Data Observability, so its timeout can
        # remain in place until a later query needs a different value.
        timeout_variable = "max_statement_time" if self._check.is_mariadb else "max_execution_time"
        timeout_value = query_timeout_ms / 1000 if self._check.is_mariadb else query_timeout_ms
        with closing(conn.cursor()) as cursor:
            cursor.execute(f"SET SESSION {timeout_variable} = %s", (timeout_value,))
        self._current_query_timeout_ms = query_timeout_ms

    def _execute_single_query(self, conn: Any, query_spec: Query) -> dict[str, Any]:
        dbname = self._validate_dbname(query_spec.dbname)
        monitor_id = query_spec.monitor_id
        start = time.time()
        try:
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")
            self._set_query_timeout(conn, query_spec.query_timeout)
            # SSCursor reads rows as fetchmany() requests them instead of buffering the
            # full result in execute(). Closing it drains unread rows before the shared
            # connection is reused for another query.
            with closing(conn.cursor(pymysql.cursors.SSCursor)) as cursor:
                if dbname != self._current_dbname:
                    cursor.execute(f"USE `{dbname}`")
                    self._current_dbname = dbname
                cursor.execute(query_spec.query)
                if cursor.description is None:
                    raise pymysql.err.ProgrammingError(
                        "Query returned no result set — only SELECT statements are supported"
                    )
                columns = [description[0] for description in cursor.description]
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
            if not conn.open:
                self._close_db_conn()
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
            'db_port': self._check._config.port,
            'db_name': query_spec.dbname,
            'monitor_id': query_spec.monitor_id,
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            **result,
        }

    def run_job(self) -> None:
        # A newly due execution replaces an older pending execution for the same
        # monitor so an extended outage does not build an unbounded backlog.
        due_by_monitor_id = dict(self._pending_retries)
        self._pending_retries = {}
        due_by_monitor_id.update({due.query.monitor_id: due for due in self._get_due_queries()})
        # Group shared session state so each database and timeout is selected as
        # few times as possible during this collection.
        due_queries = sorted(
            due_by_monitor_id.values(),
            key=lambda due: (due.query.dbname, due.query.query_timeout),
        )
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()
        try:
            conn = self._get_db_connection()
        except (pymysql.err.DatabaseError, pymysql.err.InterfaceError):
            self._close_db_conn()
            self._pending_retries.update(due_by_monitor_id)
            raise

        for index, due in enumerate(due_queries):
            query = due.query
            tags = base_tags + [f'monitor_id:{query.monitor_id}']

            now_at_fire_start = time.time()
            try:
                result = self._execute_single_query(conn, query)
            except (pymysql.err.DatabaseError, pymysql.err.InterfaceError):
                self._close_db_conn()
                self._pending_retries.update({pending.query.monitor_id: pending for pending in due_queries[index:]})
                raise
            now_at_fire_end = time.time()
            if due.mode == "interval":
                self._last_execution[query.monitor_id] = now_at_fire_end

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

                lateness = max(0.0, now_at_fire_start - due.scheduled_time)
                self._check.gauge(
                    'dd.mysql.data_observability.query_fire_lateness_seconds',
                    lateness,
                    tags=tags + [f'mode:{due.mode}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )

                payload = self._build_event_payload(query, result)
                raw_event = json.dumps(payload, default=default_json_event_encoding)
                self._log.debug(
                    "Query result for monitor_id=%d: status=%s row_count=%d",
                    query.monitor_id,
                    result['status'],
                    result['row_count'],
                )
                self._check.event_platform_event(raw_event, EVENT_TRACK_TYPE)
            except Exception as e:
                self._log.exception("Failed to emit metrics/event for monitor_id=%d", query.monitor_id)
                try:
                    self._check.count(
                        'dd.mysql.data_observability.emit_failures',
                        1,
                        tags=tags + [f'exc_class:{type(e).__name__}'],
                        hostname=self._check.reported_hostname,
                        raw=True,
                    )
                except Exception:
                    pass
