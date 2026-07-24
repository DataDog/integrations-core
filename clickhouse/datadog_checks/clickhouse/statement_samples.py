# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Collects database samples snapshots from ClickHouse system.processes.

This module provides real-time visibility into currently executing queries,
"""

from __future__ import annotations

import math
import time
from typing import TYPE_CHECKING

from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import AsynchronousInsertBufferSnapshot, QuerySamples

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# Query to get currently running/active queries from system.processes
# This is the ClickHouse equivalent of Postgres pg_stat_activity
#
# Uses {processes_table} placeholder for ClickHouse Cloud clusterAllReplicas() support:
# - For ClickHouse Cloud: clusterAllReplicas('default', system.processes)
# - For self-hosted: system.processes
ACTIVE_QUERIES_QUERY = """
SELECT
    elapsed,
    query_id,
    query,
    user,
    read_rows,
    read_bytes,
    written_rows,
    written_bytes,
    memory_usage,
    initial_query_id,
    initial_user,
    query_kind,
    is_initial_query,
    peak_memory_usage,
    total_rows_approx,
    client_name,
    client_version_major,
    client_version_minor,
    client_version_patch,
    current_database,
    thread_ids,
    address,
    port,
    client_hostname,
    is_cancelled,
    http_user_agent
FROM {processes_table}
WHERE query NOT LIKE '%system.processes%'
  AND query NOT LIKE '%system.query_log%'
  AND query != ''
"""

# Query to get active connections aggregated by user, database, etc
# Similar to Postgres PG_ACTIVE_CONNECTIONS_QUERY
ACTIVE_CONNECTIONS_QUERY = """
SELECT
    user,
    query_kind,
    current_database,
    count(*) as connections
FROM {processes_table}
WHERE query NOT LIKE '%system.processes%'
GROUP BY user, query_kind, current_database
"""

DBM_TYPE = "async_inserts_buffer"

# Query to get pending async insert buffers from system.asynchronous_inserts
BUFFER_SNAPSHOT_QUERY = """
SELECT
    database,
    table,
    hostName() AS server_node,
    format,
    query,
    total_bytes,
    length(entries.query_id) AS entry_count,
    -- first_update is the scheduled flush deadline (queued as now + busy_timeout in ClickHouse's
    -- async insert queue), not the first insert time as the docs claim.
    toUnixTimestamp64Micro(first_update) AS flush_deadline_us
FROM {asynchronous_inserts_table}
ORDER BY total_bytes DESC
LIMIT {payload_row_limit}
"""


def agent_check_getter(self):
    return self._check


class ClickhouseStatementSamples(DBMAsyncJob):
    """
    Collects database samples snapshots from ClickHouse system.processes.

    This job queries system.processes to capture currently executing queries
    and emits samples events for the DBM Samples page.
    """

    def __init__(
        self,
        check: ClickhouseCheck,
        config: QuerySamples,
        buffer_config: AsynchronousInsertBufferSnapshot,
    ):
        samples_collection_interval = config.collection_interval

        enabled_intervals = []
        if config.enabled:
            enabled_intervals.append(samples_collection_interval)
        if buffer_config.enabled:
            enabled_intervals.append(buffer_config.collection_interval)
        collection_interval = (
            math.gcd(*(int(i) for i in enabled_intervals)) if enabled_intervals else samples_collection_interval
        )
        # int() truncates intervals below 1s to 0, which would zero out the gcd and make rate_limit divide by zero.
        if enabled_intervals and collection_interval < 1:
            collection_interval = min(enabled_intervals)

        super(ClickhouseStatementSamples, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=config.run_sync,
            enabled=config.enabled or buffer_config.enabled,
            dbms="clickhouse",
            min_collection_interval=check.check_interval if hasattr(check, 'check_interval') else 15,
            expected_db_exceptions=(Exception,),
            job_name="query-samples",
        )
        self._check = check
        self._config = config
        self._tags_no_db = None
        self.tags = None

        # Dedicated client for this job (uses shared connection pool)
        self._db_client = None

        # Obfuscator options for SQL statements
        obfuscate_options = {
            'return_json_metadata': True,
            'collect_tables': True,
            'collect_commands': True,
            'collect_comments': True,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

        self._collection_interval = samples_collection_interval
        self._last_samples_time = 0.0
        self._payload_row_limit = config.payload_row_limit

        # Async insert buffer snapshot collapses into this job
        self._buffer_enabled = buffer_config.enabled
        self._buffer_collection_interval = buffer_config.collection_interval
        self._buffer_payload_row_limit = buffer_config.payload_row_limit
        self._last_buffer_snapshot_time = 0.0

    def cancel(self):
        """Cancel the job and clean up the dedicated client."""
        super(ClickhouseStatementSamples, self).cancel()
        self._close_db_client()

    def _close_db_client(self):
        """Close the dedicated database client if it exists."""
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing DBM client: %s", e)
            self._db_client = None

    def _get_debug_tags(self):
        """Get debug tags for metrics."""
        t = []
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_active_queries(self):
        """
        Fetch currently running queries from system.processes.

        For ClickHouse Cloud: Uses clusterAllReplicas('default', system.processes) to query
        all nodes in the cluster.
        For self-hosted: Queries only the local node's system.processes.
        """
        start_time = time.time()

        try:
            # Get the appropriate table reference based on deployment type
            processes_table = self._check.get_system_table('processes')
            query = ACTIVE_QUERIES_QUERY.format(processes_table=processes_table)

            # Use the dedicated client for this job
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(query)
            rows = result.result_rows

            elapsed_ms = (time.time() - start_time) * 1000
            self._check.histogram(
                "dd.clickhouse.samples.get_active_queries.time",
                elapsed_ms,
                tags=self.tags + self._get_debug_tags(),
                raw=True,
            )
            self._log.debug("Loaded %s rows from %s in %.2f ms", len(rows), processes_table, elapsed_ms)

            return rows
        except OperationalError as e:
            # Connection-related error - reset client to force reconnect
            self._log.warning("Connection error in active queries, will reconnect: %s", e)
            self._close_db_client()
            self._check.count(
                "dd.clickhouse.samples.error",
                1,
                tags=self.tags + ["error:get-active-queries", "error_type:connection"] + self._get_debug_tags(),
                raw=True,
            )
            return []
        except Exception as e:
            # Query error - don't reset connection
            self._log.exception("Failed to collect active queries: %s", str(e))
            self._check.count(
                "dd.clickhouse.samples.error",
                1,
                tags=self.tags + ["error:get-active-queries"] + self._get_debug_tags(),
                raw=True,
            )
            return []

    def _normalize_row(self, row):
        """
        Normalize a row from system.processes into a standard format.
        """
        try:
            (
                elapsed,
                query_id,
                query,
                user,
                read_rows,
                read_bytes,
                written_rows,
                written_bytes,
                memory_usage,
                initial_query_id,
                initial_user,
                query_kind,
                is_initial_query,
                peak_memory_usage,
                total_rows_approx,
                client_name,
                client_version_major,
                client_version_minor,
                client_version_patch,
                current_database,
                thread_ids,
                address,
                port,
                client_hostname,
                is_cancelled,
                http_user_agent,
            ) = row

            normalized_row = {
                'elapsed': float(elapsed) if elapsed else 0,
                'query_id': str(query_id),
                'query': str(query),
                'user': str(user),
                'read_rows': int(read_rows) if read_rows else 0,
                'read_bytes': int(read_bytes) if read_bytes else 0,
                'written_rows': int(written_rows) if written_rows else 0,
                'written_bytes': int(written_bytes) if written_bytes else 0,
                'memory_usage': int(memory_usage) if memory_usage else 0,
                'initial_query_id': str(initial_query_id) if initial_query_id else None,
                'initial_user': str(initial_user) if initial_user else None,
                'query_kind': str(query_kind) if query_kind else None,
                'is_initial_query': bool(is_initial_query) if is_initial_query is not None else True,
                'peak_memory_usage': int(peak_memory_usage) if peak_memory_usage else 0,
                'total_rows_approx': int(total_rows_approx) if total_rows_approx else 0,
                'client_name': str(client_name) if client_name else None,
                'client_version_major': int(client_version_major) if client_version_major else None,
                'client_version_minor': int(client_version_minor) if client_version_minor else None,
                'client_version_patch': int(client_version_patch) if client_version_patch else None,
                'current_database': str(current_database) if current_database else None,
                'thread_ids': list(thread_ids) if thread_ids else [],
                'address': str(address) if address else None,
                'port': int(port) if port else None,
                'client_hostname': str(client_hostname) if client_hostname else None,
                'is_cancelled': bool(is_cancelled) if is_cancelled is not None else False,
                'http_user_agent': str(http_user_agent) if http_user_agent else None,
            }

            return self._obfuscate_query(normalized_row)
        except Exception as e:
            self._log.warning("Failed to normalize row: %s, row: %s", str(e), row)
            return None

    def _obfuscate_query(self, row):
        """
        Obfuscate the query and compute its signature.
        """
        try:
            statement = obfuscate_sql_with_metadata(row['query'], self._obfuscate_options)
            obfuscated_query = statement['query']
            metadata = statement['metadata']

            row['statement'] = obfuscated_query
            row['query_signature'] = compute_sql_signature(obfuscated_query)
            row['dd_tables'] = metadata.get('tables', None)
            row['dd_commands'] = metadata.get('commands', None)
            row['dd_comments'] = metadata.get('comments', None)

        except Exception as e:
            self._log.warning("Failed to obfuscate query: %s, query: %s", str(e), row.get('query', '')[:100])
            # On obfuscation error, still include the row but without statement
            row['statement'] = None
            row['query_signature'] = compute_sql_signature(row['query'])
            row['dd_tables'] = None
            row['dd_commands'] = None
            row['dd_comments'] = None

        return row

    def _normalize_rows(self, rows):
        """
        Normalize and filter rows from system.processes.
        """
        normalized_rows = []
        for row in rows:
            normalized_row = self._normalize_row(row)
            if normalized_row and normalized_row.get('statement'):
                normalized_rows.append(normalized_row)

        return normalized_rows

    def _get_active_connections(self):
        """
        Get aggregated active connection counts from system.processes.

        For ClickHouse Cloud: Uses clusterAllReplicas to aggregate across all nodes.
        For self-hosted: Aggregates only the local node's connections.
        """
        try:
            start_time = time.time()

            # Get the appropriate table reference based on deployment type
            processes_table = self._check.get_system_table('processes')
            query = ACTIVE_CONNECTIONS_QUERY.format(processes_table=processes_table)

            # Use the dedicated client for this job
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(query)
            rows = result.result_rows

            elapsed_ms = (time.time() - start_time) * 1000
            self._log.debug(
                "Retrieved %s connection aggregation rows from %s in %.2f ms", len(rows), processes_table, elapsed_ms
            )

            # Convert to list of dicts
            connections = []
            for row in rows:
                connections.append(
                    {
                        'user': row[0],
                        'query_kind': row[1],
                        'current_database': row[2],
                        'connections': row[3],
                    }
                )

            return connections

        except OperationalError as e:
            # Connection-related error - reset client to force reconnect
            self._log.warning("Connection error in active connections, will reconnect: %s", e)
            self._close_db_client()
            return []
        except Exception as e:
            # Query error - don't reset connection
            self._log.warning("Failed to get active connections: %s", e)
            return []

    def _create_active_sessions(self, rows):
        """
        Create active sessions from normalized rows.
        Yields sessions up to the payload_row_limit.
        """
        session_count = 0
        for row in rows:
            # Only include rows with successfully obfuscated statements
            if not row.get('statement'):
                continue

            # Remove null values and the raw query (we have the obfuscated statement)
            active_row = {key: val for key, val in row.items() if val is not None and key != 'query'}
            session_count += 1
            yield active_row

            if session_count >= self._payload_row_limit:
                break

    def _create_samples_event(self, rows, active_connections):
        """
        Create a database monitoring samples event payload.
        """
        active_sessions = list(self._create_active_sessions(rows))

        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "clickhouse",
            "dbm_type": "activity",
            "collection_interval": self._collection_interval,
            "ddtags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "service": getattr(self._check._config, 'service', None),
            "clickhouse_activity": active_sessions,
            "clickhouse_connections": active_connections,
        }
        return event

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_samples(self):
        """
        Main method to collect and submit samples snapshots.
        """
        start_time = time.time()

        # Get active queries from system.processes
        rows = self._get_active_queries()
        self._log.debug("Retrieved %s raw rows from system.processes", len(rows))

        # Normalize and filter rows
        rows = self._normalize_rows(rows)
        self._log.debug("After normalization: %s rows", len(rows))

        # Get active connections aggregation
        active_connections = self._get_active_connections()

        # Create and submit samples event
        samples_event = self._create_samples_event(rows, active_connections)

        self._check.database_monitoring_query_activity(json.dumps(samples_event, default=default_json_event_encoding))

        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            "dd.clickhouse.collect_samples_snapshot.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )

        self._log.debug(
            "Samples snapshot collected: sessions=%s, connections=%s, elapsed_ms=%.2f",
            len(samples_event.get('clickhouse_activity', [])),
            len(samples_event.get('clickhouse_connections', [])),
            elapsed_ms,
        )

    def _collect_buffer_snapshot(self) -> None:
        """
        Run the async insert buffer snapshot on its own collection interval
        """
        now = time.time()
        if self._buffer_enabled and now - self._last_buffer_snapshot_time >= self._buffer_collection_interval:
            self._last_buffer_snapshot_time = now
            buffer_snapshot = self._query_buffer_snapshot()
            self._emit_buffer_events(buffer_snapshot)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _query_buffer_snapshot(self) -> list[dict]:
        """Query system.asynchronous_inserts for pending buffers."""
        query = BUFFER_SNAPSHOT_QUERY.format(
            asynchronous_inserts_table=self._check.get_system_table('asynchronous_inserts'),
            payload_row_limit=self._buffer_payload_row_limit,
        )
        try:
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            rows = self._db_client.query(query).result_rows
        except OperationalError as e:
            self._log.warning("Database connection error in buffer snapshot, will reconnect: %s", e)
            self._close_db_client()
            self._check.count(
                "dd.clickhouse.async_inserts_buffer.error",
                1,
                tags=self.tags + ["error:collect-buffer-snapshot", "error_type:connection"] + self._get_debug_tags(),
                raw=True,
            )
            return []
        except Exception as e:
            self._log.exception("Failed to collect buffer snapshot: %s", e)
            self._check.count(
                "dd.clickhouse.async_inserts_buffer.error",
                1,
                tags=self.tags + ["error:collect-buffer-snapshot"] + self._get_debug_tags(),
                raw=True,
            )
            return []

        result = []
        for row in rows:
            database, table, server_node, format_, query_text, total_bytes, entry_count, flush_deadline_us = row
            result.append(
                {
                    'database': database,
                    'table': table,
                    'server_node': server_node,
                    'format': format_,
                    'query': query_text,
                    'total_bytes': total_bytes,
                    'entry_count': entry_count,
                    'flush_deadline_us': flush_deadline_us,
                }
            )
        return result

    def _obfuscate_buffer_query(self, query_text: str) -> dict | None:
        try:
            statement = obfuscate_sql_with_metadata(query_text, self._obfuscate_options)
            obfuscated_query = statement['query']
            metadata = statement['metadata']
            return {
                'query': obfuscated_query,
                'query_signature': compute_sql_signature(obfuscated_query),
                'dd_tables': metadata.get('tables'),
                'dd_commands': metadata.get('commands'),
                'dd_comments': metadata.get('comments'),
            }
        except Exception as e:
            self._log.debug("Failed to obfuscate buffer query: %s", e)
            self._check.count(
                "dd.clickhouse.async_inserts_buffer.error",
                1,
                tags=self.tags + ["error:obfuscate-query"] + self._get_debug_tags(),
                raw=True,
            )
            return None

    def _create_buffer_event(self, buffer_snapshot: list[dict]) -> dict:
        """
        Create a database monitoring buffer snapshot event payload.
        """
        buffers = []
        for row in buffer_snapshot:
            obfuscated = self._obfuscate_buffer_query(row['query'])
            if obfuscated:
                buffers.append(
                    {
                        'database': row['database'],
                        'table': row['table'],
                        'format': row['format'],
                        'query': obfuscated['query'],
                        'query_signature': obfuscated['query_signature'],
                        'dd_tables': obfuscated['dd_tables'],
                        'dd_commands': obfuscated['dd_commands'],
                        'dd_comments': obfuscated['dd_comments'],
                        'server_node': row.get('server_node', ''),
                        'total_bytes': row['total_bytes'],
                        'entry_count': row['entry_count'],
                        'flush_deadline_us': row['flush_deadline_us'],
                    }
                )

        return {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "clickhouse",
            "dbm_type": DBM_TYPE,
            "collection_interval": self._buffer_collection_interval,
            "ddtags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "clickhouse_version": self._check.dbms_version,
            "clickhouse_async_insert_buffers": buffers,
        }

    def _emit_buffer_events(self, buffer_snapshot: list[dict]) -> None:
        if not buffer_snapshot:
            return

        buffer_event = self._create_buffer_event(buffer_snapshot)
        self._check.database_monitoring_query_activity(json.dumps(buffer_event, default=default_json_event_encoding))

    def run_job(self):
        """
        Main job execution method called by DBMAsyncJob.
        """
        # Filter out internal tags
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]

        try:
            now = time.time()
            if self._config.enabled and now - self._last_samples_time >= self._collection_interval:
                self._last_samples_time = now
                self._collect_samples()
        except Exception as e:
            self._log.exception("Failed to collect samples snapshot: %s", e)
            self._check.count(
                "dd.clickhouse.samples.error",
                1,
                tags=self.tags + ["error:collect-samples"] + self._get_debug_tags(),
                raw=True,
            )

        try:
            self._collect_buffer_snapshot()
        except Exception as e:
            self._log.exception("Failed to collect buffer snapshot: %s", e)
            self._check.count(
                "dd.clickhouse.async_inserts_buffer.error",
                1,
                tags=self.tags + ["error:collect-buffer-snapshot"] + self._get_debug_tags(),
                raw=True,
            )
