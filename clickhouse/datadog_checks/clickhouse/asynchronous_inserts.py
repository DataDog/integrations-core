from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import OperationalError

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import AsynchronousInsertBufferSnapshot

DBM_TYPE_BUFFER = "asynchronous_inserts_buffer"  # buffer snapshot, from system.asynchronous_inserts
DBM_TYPE_FLUSH = "asynchronous_inserts_flush"  # flush health, from system.asynchronous_insert_log

BUFFER_SNAPSHOT_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    format,
    query,
    total_bytes,
    length(entries.query_id) AS entry_count,
    toUnixTimestamp64Micro(first_update) AS first_update_us
FROM {asynchronous_inserts_table}
ORDER BY total_bytes DESC
"""

FLUSH_HEALTH_QUERY = """\
SELECT
    database,
    table,
    format,
    status,
    exception,
    hostName() AS server_node,
    bytes,
    rows,
    query_id,
    query,
    event_time_microseconds,
    flush_time_microseconds
FROM {asynchronous_insert_log_table}
WHERE
    {checkpoint_filter}
    AND event_time_microseconds <= now64(6)
ORDER BY event_time_microseconds ASC
"""


def agent_check_getter(self):
    return self._check


class ClickhouseAsynchronousInserts(DBMAsyncJob):
    """
    Monitors asynchronous insert health by polling:
     - system.asynchronous_inserts          - buffer state
     - system.asynchronous_insert_log       - flush health

    Produces:
     - gauge metrics (buffer state) via self._check.gauge()
     - TODO (later phase): buffer snapshot events (dbm_type="asynchronous_inserts_buffer")
     - TODO (later phase): flush health events (dbm_type="asynchronous_inserts_flush")
    """

    def __init__(self, check: ClickhouseCheck, config: AsynchronousInsertBufferSnapshot):
        collection_interval = config.collection_interval

        super().__init__(
            check,
            run_sync=config.run_sync,
            enabled=config.enabled,
            expected_db_exceptions=(Exception,),
            min_collection_interval=check._config.min_collection_interval,
            dbms="clickhouse",
            job_name="asynchronous-inserts",
            rate_limit=1 / collection_interval,
        )

        self._check = check
        self._config = config
        self._collection_interval = collection_interval

        self._tags_no_db: list[str] | None = None
        self.tags: list[str] | None = None

        self._db_client = None

    def cancel(self):
        super().cancel()
        self._close_db_client()

    def _close_db_client(self):
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing asynchronous inserts client: %s", e)
            self._db_client = None

    def _get_debug_tags(self) -> list[str]:
        return list(self._tags_no_db) if self._tags_no_db else []

    def _execute_query(self, query: str) -> list:
        if self._db_client is None:
            self._db_client = self._check.create_dbm_client()
        try:
            return self._db_client.query(query).result_rows
        except OperationalError as e:
            self._log.warning("Database connection error, will reconnect on next query: %s", e)
            self._close_db_client()
            raise

    def _collect_buffer_snapshot(self) -> list[dict]:
        query = BUFFER_SNAPSHOT_QUERY.format(
            asynchronous_inserts_table=self._check.get_system_table('asynchronous_inserts'),
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect buffer snapshot")
            self._emit_error_count("collect-buffer-snapshot")
            return []

        result = []
        for row in rows:
            database, table, server_node, format_, query_text, total_bytes, entry_count, first_update_us = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'format': format_,
                    'query': query_text,
                    'total_bytes': total_bytes,
                    'entry_count': entry_count,
                    'first_update_us': first_update_us,
                }
            )
        return result

    # TODO (later phase): flush log collection from system.asynchronous_insert_log
    def _collect_flush_health(self):
        pass

    def _emit_gauges(self, buffer_snapshot: list[dict]) -> None:
        """
        Aggregate per-buffer rows by (database, table, server_node) and emit one
        set of gauges per key.

        Steps to implement:
          1. Build an aggregation dict keyed by (database, table, server_node).
             For each row: sum total_bytes, sum entry_count, count buffers
             (active_count), and track min(oldest_entr).
          2. For each key, build tags:
             self.tags + [f'database:{db}', f'table:{tbl}', f'server_node:{node}']
          3. Emit four gauges via self._check.gauge():
               asynchronous_inserts.buffer.bytes                -> summed total_bytes
               asynchronous_inserts.buffer.pending_entry_count  -> summed entry_count
               asynchronous_inserts.buffer.active_count         -> buffer count
               asynchronous_inserts.buffer.oldest_age_seconds   -> see note
             oldest_age_seconds = max(time.time() - oldest_entr / 1_000_000, 0)
             (use the Agent clock, not server now(), to avoid ClickHouse Cloud skew)
        """
        now = time.time()

        buffer_state_agg: dict[tuple, dict] = defaultdict(
            lambda: {
                'total_bytes_pending': 0,
                'active_buffers': 0,
                'total_entries_pending': 0,
                'oldest_entry': None,  # raw min first_update timestamp (microseconds); converted to age at emit time
            }
        )

        for row in buffer_snapshot:
            server_node = row.get('server_node', '')
            key = (row['database'], row['table'], server_node)
            agg = buffer_state_agg[key]
            agg['total_bytes_pending'] += row['total_bytes']
            agg['active_buffers'] += 1
            agg['total_entries_pending'] += row['entry_count']
            # Track the smallest first_update timestamp for this key (the oldest pending entry).
            first_update_us = row.get('first_update_us')
            if first_update_us is not None and (agg['oldest_entry'] is None or first_update_us < agg['oldest_entry']):
                agg['oldest_entry'] = first_update_us

        for (database, table, server_node), agg in buffer_state_agg.items():
            tags = self.tags + [
                f'database:{database}',
                f'table:{table}',
                f'server_node:{server_node}',
            ]

            # Convert the oldest pending entry's timestamp into an age in seconds
            oldest_entry = agg['oldest_entry']
            oldest_entry_age_seconds = now - oldest_entry / 1_000_000 if oldest_entry is not None else 0

            self._check.gauge('asynchronous_inserts.buffer.pending_bytes', agg['total_bytes_pending'], tags=tags)
            self._check.gauge(
                'asynchronous_inserts.buffer.pending_entry_count', agg['total_entries_pending'], tags=tags
            )
            self._check.gauge('asynchronous_inserts.buffer.active_count', agg['active_buffers'], tags=tags)
            self._check.gauge(
                'asynchronous_inserts.buffer.oldest_entry_age_seconds', oldest_entry_age_seconds, tags=tags
            )

    # TODO (later phase): emit buffer rows as DBM events (dbm_type="asynchronous_inserts_buffer")
    # and emit flush health as DBM events (dbm_type="asynchronous_inserts_flush")
    def _emit_events(self, buffer_snapshot: list[dict]) -> None:
        pass

    def _emit_error_count(self, error_label: str) -> None:
        base_tags = self.tags if self.tags else []
        self._check.count(
            "dd.clickhouse.asynchronous_inserts.error",
            1,
            tags=base_tags + [f"error:{error_label}"] + self._get_debug_tags(),
            raw=True,
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_emit(self):
        """
        Main collection and emission logic.
        """
        buffer_snapshot = self._collect_buffer_snapshot()

        # Milestone 1: gauges only
        self._emit_gauges(buffer_snapshot)

        # Milestone 2 (later): DBM events for the per-query drilldown
        # self._emit_events(buffer_snapshot)

        # Milestone 3 (later): flush health events
        # self._collect_flush_health()

    def run_job(self):
        """
        Main job entry point.
        """
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]

        try:
            self._collect_and_emit()
        except Exception as e:
            self._log.exception("asynchronous_inserts run_job failed: %s", e)
            self._emit_error_count("run-job")
