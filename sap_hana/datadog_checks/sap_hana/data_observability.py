# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable
from contextlib import closing
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from datadog_checks.base.utils.cron import CronScheduler
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding

if TYPE_CHECKING:
    from .config_models.instance import DataObservability, Query
    from .sap_hana import SapHanaCheck

try:
    from hdbcli.dbapi import Error as HanaError
except ImportError:
    HanaError = Exception  # type: ignore[misc,assignment]

EVENT_TRACK_TYPE = 'do-query-results'

MAX_RESULT_ROWS = 10_000

CRON_STARTUP_LOOKBACK_SECONDS = 300

DEFAULT_DO_QUERY_TIMEOUT_MS = 60_000

Mode = Literal["cron", "interval"]


def _query_key(q: Query) -> str:
    """Stable per-query scheduling key.

    Prefer the monitor id when the RC payload carries a real one — this is the
    forward-looking contract shared with Postgres. Today the payload delivers no
    per-query monitor id (it decodes to 0/None), so fall back to a hash of the query
    text. That is sufficient because the SQL embeds the monitor id(s) it serves (in a
    trailing "-- Datadog {\"monitor_ids\":[...]}" comment, or the column alias for
    custom SQL), so distinct monitors always produce distinct query text.
    """
    if q.monitor_id:  # real, non-zero monitor id
        return f"monitor:{q.monitor_id}"
    return hashlib.sha256(q.query.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class DueQuery:
    query: Query
    query_key: str
    scheduled_time: float
    mode: Mode


class SapHanaDataObservability(DBMAsyncJob):
    def __init__(self, check: SapHanaCheck, do_config: DataObservability) -> None:
        self._check = check
        self._do_config = do_config
        self._last_execution: dict[str, float] = {}
        self._do_conn: Any = None
        self._do_conn_timeout_ms: int | None = None

        collection_interval = do_config.collection_interval or 10
        super().__init__(
            check,
            config_host=check._server,
            rate_limit=1 / float(collection_interval),
            run_sync=do_config.run_sync,
            enabled=do_config.enabled,
            dbms="saphana",
            min_collection_interval=check.instance.get('min_collection_interval', 15),
            expected_db_exceptions=(HanaError,),
            shutdown_callback=self._shutdown,
            job_name="data-observability",
        )
        self._queries, self._schedulers = self._filter_valid_queries(do_config.queries or ())
        self._log.debug(
            "Data Observability job initialized: %d valid queries, config_id=%s",
            len(self._queries),
            do_config.config_id,
        )

    def _shutdown(self) -> None:
        self._close_connection()

    def _close_connection(self) -> None:
        """Close the persistent DO connection and clear its cached state."""
        if self._do_conn is not None:
            try:
                self._do_conn.close()
            except Exception:
                pass
        self._do_conn = None
        self._do_conn_timeout_ms = None

    def _filter_valid_queries(self, queries: Iterable[Query]) -> tuple[tuple[Query, ...], dict[str, CronScheduler]]:
        valid: list[Query] = []
        schedulers: dict[str, CronScheduler] = {}
        n_skipped = 0
        for q in queries:
            key = _query_key(q)
            if q.schedule:
                try:
                    schedulers[key] = CronScheduler(q.schedule, startup_lookback=CRON_STARTUP_LOOKBACK_SECONDS)
                except (ValueError, TypeError) as e:
                    self._log.warning(
                        "Skipping DO query key=%s: invalid cron schedule %r (%s).",
                        key,
                        q.schedule,
                        e,
                    )
                    n_skipped += 1
                    continue
            elif not (q.interval_seconds and q.interval_seconds > 0):
                self._log.warning(
                    "Skipping DO query key=%s: neither schedule nor positive interval_seconds set",
                    key,
                )
                n_skipped += 1
                continue
            valid.append(q)
        if n_skipped:
            self._log.warning(
                "Data Observability: %d of %d queries were skipped due to invalid scheduling configuration.",
                n_skipped,
                n_skipped + len(valid),
            )
        return tuple(valid), schedulers

    def _get_due_queries(self) -> list[DueQuery]:
        now = time.time()
        due: list[DueQuery] = []
        for q in self._queries:
            key = _query_key(q)
            if q.schedule:
                ticks = self._schedulers[key].due_ticks(now + 0.001)
                if ticks:
                    due.append(DueQuery(q, key, ticks[-1], "cron"))
            else:
                last = self._last_execution.get(key)
                if last is None or now - last >= q.interval_seconds:
                    scheduled = (last + q.interval_seconds) if last is not None else now
                    due.append(DueQuery(q, key, scheduled, "interval"))
        return due

    def _build_base_tags(self) -> list[str]:
        tags = [t for t in self._tags if not t.startswith('dd.internal')] if self._tags else []
        if self._do_config.config_id:
            tags.append(f'config_id:{self._do_config.config_id}')
        tags.append('db_type:saphana')
        return tags

    def _get_connection(self, timeout_ms: int) -> Any:
        """Return the persistent DO connection, (re)creating it when the timeout changes."""
        if self._do_conn is not None and self._do_conn_timeout_ms == timeout_ms:
            return self._do_conn
        if self._do_conn is not None:
            self._log.debug(
                "Data Observability: reopening DO connection (timeout changed from %dms to %dms).",
                self._do_conn_timeout_ms,
                timeout_ms,
            )
            self._close_connection()
        from hdbcli.dbapi import connect as hana_connect  # noqa: PLC0415

        # Use the check's connection-property builder so that TLS settings from
        # use_tls/tls_* instance options are applied here too.  The DO job opens
        # its own connection (instead of reusing self._check._conn) because it
        # needs a per-query statementTimeout that must not affect main-check queries.
        conn_props = self._check._get_connection_properties()
        conn_props['statementTimeout'] = timeout_ms
        try:
            self._do_conn = hana_connect(**conn_props)
        except HanaError as e:
            self._log.error(
                "Data Observability: failed to open DO connection to %s:%s — %s",
                self._check._server,
                self._check._port,
                e,
            )
            raise
        self._log.debug(
            "Data Observability: DO connection opened (statementTimeout=%dms).",
            timeout_ms,
        )
        self._do_conn_timeout_ms = timeout_ms
        return self._do_conn

    def _execute_single_query(self, query_spec: Query) -> dict[str, Any]:
        timeout_ms = query_spec.query_timeout or DEFAULT_DO_QUERY_TIMEOUT_MS
        start = time.time()
        try:
            # Acquire the connection inside the try so a failure to (re)open it is
            # reported as a per-query error instead of aborting the whole run_job cycle.
            conn = self._get_connection(timeout_ms)
            if self._cancel_event.is_set():
                raise Exception("Job loop cancelled. Aborting query.")
            with closing(conn.cursor()) as cursor:
                cursor.execute(query_spec.query)
                if cursor.description is None:
                    raise HanaError("Query returned no result set — only SELECT statements are supported")
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
        except HanaError as e:
            duration = time.time() - start
            self._log.warning(
                "Query failed (%.3fs): %s | SQL: %s",
                duration,
                e,
                query_spec.query,
            )
            self._log.warning("Data Observability: resetting DO connection after query failure.")
            self._close_connection()
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
            'db_type': 'saphana',
            'db_host': self._check._server,
            'db_port': self._check._port,
            'db_name': query_spec.dbname or '',
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            **result,
        }
        if query_spec.monitor_id is not None:
            payload['monitor_id'] = query_spec.monitor_id
        return payload

    def run_job(self) -> None:
        if not self._queries:
            self._log.debug(
                "Data Observability job is enabled but no queries are configured. "
                "Waiting for Remote Configuration to deliver DO_QUERY_ACTIONS."
            )
            return
        due_queries = self._get_due_queries()
        if not due_queries:
            self._log.debug("No data observability queries due for execution.")
            return

        base_tags = self._build_base_tags()

        for due in due_queries:
            q = due.query
            tags = base_tags

            now_at_fire_start = time.time()
            result = self._execute_single_query(q)
            now_at_fire_end = time.time()

            if due.mode == "interval":
                self._last_execution[due.query_key] = now_at_fire_end

            try:
                self._check.gauge(
                    'dd.sap_hana.data_observability.query_execution_time',
                    result['duration_s'],
                    tags=tags,
                    hostname=self._check.reported_hostname,
                    raw=True,
                )
                self._check.count(
                    'dd.sap_hana.data_observability.query_executions',
                    1,
                    tags=tags + [f'status:{result["status"]}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )

                lateness = max(0.0, now_at_fire_start - due.scheduled_time)
                self._check.gauge(
                    'dd.sap_hana.data_observability.query_fire_lateness_seconds',
                    lateness,
                    tags=tags + [f'mode:{due.mode}'],
                    hostname=self._check.reported_hostname,
                    raw=True,
                )

                payload = self._build_event_payload(q, result)
                raw_event = json.dumps(payload, default=default_json_event_encoding)
                self._log.debug(
                    "Query result key=%s: status=%s row_count=%d",
                    due.query_key,
                    result['status'],
                    result['row_count'],
                )
                self._check.event_platform_event(raw_event, EVENT_TRACK_TYPE)
            except Exception as e:
                self._log.exception("Failed to emit metrics/event for query key=%s", due.query_key)
                try:
                    self._check.count(
                        'dd.sap_hana.data_observability.emit_failures',
                        1,
                        tags=tags + [f'exc_class:{type(e).__name__}'],
                        hostname=self._check.reported_hostname,
                        raw=True,
                    )
                except Exception:
                    pass
