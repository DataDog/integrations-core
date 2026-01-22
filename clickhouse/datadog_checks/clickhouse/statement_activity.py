# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Collects database activity snapshots from ClickHouse system.processes.

This module provides real-time visibility into currently executing queries,
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import QueryActivity

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


def agent_check_getter(self):
    return self._check


class ClickhouseStatementActivity(DBMAsyncJob):
    """
    Collects database activity snapshots from ClickHouse system.processes.

    This job queries system.processes to capture currently executing queries
    and emits activity events for the DBM Activity page.
    """

    def __init__(self, check: ClickhouseCheck, config: QueryActivity):
        collection_interval = config.collection_interval

        super(ClickhouseStatementActivity, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=config.run_sync,
            enabled=config.enabled,
            dbms="clickhouse",
            min_collection_interval=check.check_interval if hasattr(check, 'check_interval') else 15,
            expected_db_exceptions=(Exception,),
            job_name="query-activity",
        )
        self._check = check
        self._config = config
        self._tags_no_db = None
        self.tags = None

        # Create a separate client for this DBM job to avoid concurrent query errors
        self._db_client = None

        # Obfuscator options for SQL statements
        obfuscate_options = {
            'return_json_metadata': True,
            'collect_tables': True,
            'collect_commands': True,
            'collect_comments': True,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

        self._collection_interval = collection_interval
        self._payload_row_limit = config.payload_row_limit

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
                "dd.clickhouse.activity.get_active_queries.time",
                elapsed_ms,
                tags=self.tags + self._get_debug_tags(),
                raw=True,
            )
            self._log.debug("Loaded %s rows from %s in %.2f ms", len(rows), processes_table, elapsed_ms)

            return rows
        except Exception as e:
            self._log.exception("Failed to collect active queries: %s", str(e))
            # Reset client on error to force reconnect
            self._db_client = None
            self._check.count(
                "dd.clickhouse.activity.error",
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

        except Exception as e:
            self._log.warning("Failed to get active connections: %s", e)
            # Reset client on error to force reconnect
            self._db_client = None
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

    def _create_activity_event(self, rows, active_connections):
        """
        Create a database monitoring activity event payload.
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
    def _collect_activity(self):
        """
        Main method to collect and submit activity snapshots.
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

        # Create and submit activity event
        activity_event = self._create_activity_event(rows, active_connections)

        self._check.database_monitoring_query_activity(json.dumps(activity_event, default=default_json_event_encoding))

        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            "dd.clickhouse.collect_activity_snapshot.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )

        self._log.debug(
            "Activity snapshot collected: sessions=%s, connections=%s, elapsed_ms=%.2f",
            len(activity_event.get('clickhouse_activity', [])),
            len(activity_event.get('clickhouse_connections', [])),
            elapsed_ms,
        )

    def run_job(self):
        """
        Main job execution method called by DBMAsyncJob.
        """
        # Filter out internal tags
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]

        try:
            self._collect_activity()
        except Exception as e:
            self._log.exception("Failed to collect activity snapshot: %s", e)
            self._check.count(
                "dd.clickhouse.activity.error",
                1,
                tags=self.tags + ["error:collect-activity"] + self._get_debug_tags(),
                raw=True,
            )
