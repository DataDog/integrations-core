from typing import TYPE_CHECKING
from clickhouse_connect.driver.client import Client
from clickhouse_connect.driver.exceptions import OperationalError
from collections import defaultdict
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

DBM_TYPE = "async_inserts"

BUFFER_SNAPSHOT_QUERY = """\
SELECT
    database,
    table,
    hostName() AS server_node,
    format,
    query,
    total_bytes,
    length(entries.query_id) AS entry_count,
    toUnixTimestamp64Micro(first_update) AS oldest_entry_us
FROM {async_inserts_table}
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
FROM {async_insert_log_table}
WHERE
    {checkpoint_filter}
    AND event_time_microseconds <= now64(6)
ORDER BY event_time_microseconds ASC
"""

def agent_check_getter(self):
    return self._check

class ClickhouseAsyncInserts(DBMAsyncJob):
    """
    Monitors async insert health by polling:
     - system.asynchronous_inserts          - buffer state
     - system.asynchronous_insert_log       - flush health

    Produces gauges (buffer state) and row-level events
    """

    # TODO: implement this
    def __init__(self, check: ClickhouseCheck, config):
        pass

    def cancel(self):
        super().cancel()
        self._close_db_client()

    def _close_db_client(self):
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing async inserts client: %s", e)
            self._db_client = None

    def _execute_query(self, query: str) -> list:
        if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
        try:
        
        except OperationalError as e:


    def _collect_buffer_snapshot(self) -> list[dict]:
        query = BUFFER_SNAPSHOT_QUERY.format(
            async_inserts_table=self._check.get_system_table('asynchronous_inserts'),
        )
        try:
            rows = self._execute_query(query)
        except Exception:
            self._log.exception("Failed to collect buffer snapshot")
            self._emit_error_count("collect-buffer-snapshot")
            return []

        # TODO: parse rows into a list of dicts
        result = []
        for row in rows:
            database, table, server_node,  format, query, total_bytes, entry_count, oldest_entry_us = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'format': format,
                    'query': query,
                    'total_bytes': total_bytes,
                    'entry_count': entry_count,
                    'oldest_entry_us': oldest_entry_us,
                }
            )
        return result

    # TODO: implement this
    def _collect_flush_health(self):
        pass

    # TODO: implement this
    def _emit_gauges(self, buffer_snapshot: list[dict]) -> None:
        pass

    # TODO: implement this
    def _emit_events(self):
        pass

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_emit(self):
        pass

    def run_job(self):
        # TODO: set tags here

        try:
            self._collect_and_emit()
        except Exception as e:
            self._log.exception("async_inserts run_job failed: %s", e)
            self._emit_error_count("run-job")
