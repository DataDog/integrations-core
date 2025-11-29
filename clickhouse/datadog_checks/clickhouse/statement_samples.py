# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# Query to get currently running/active queries from system.processes
# This is the ClickHouse equivalent of Postgres pg_stat_activity
# Note: result_rows, result_bytes, query_start_time, query_start_time_microseconds
# don't exist in ClickHouse (as of 24.11), so they're excluded
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
FROM system.processes
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
FROM system.processes
WHERE query NOT LIKE '%system.processes%'
GROUP BY user, query_kind, current_database
"""

# Columns from system.processes which correspond to attributes common to all databases
# and are therefore stored under other standard keys
system_processes_sample_exclude_keys = {
    # we process & obfuscate this separately
    'query',
    # stored separately in standard db fields
    'user',
    'query_id',
    'current_database',  # stored as db.instance
}


def agent_check_getter(self):
    return self._check


class ClickhouseStatementSamples(DBMAsyncJob):
    """
    Collects statement samples from ClickHouse active queries (system.processes).
    Similar to Postgres integration using pg_stat_activity.
    """

    def __init__(self, check: ClickhouseCheck, config):
        # Default collection interval if not specified
        collection_interval = getattr(config, 'collection_interval', 10)

        super(ClickhouseStatementSamples, self).__init__(
            check,
            rate_limit=1 / collection_interval,
            run_sync=getattr(config, 'run_sync', False),
            enabled=getattr(config, 'enabled', True),
            dbms="clickhouse",
            min_collection_interval=check.check_interval if hasattr(check, 'check_interval') else 15,
            expected_db_exceptions=(Exception,),
            job_name="query-samples",
        )
        self._check = check
        self._config = config
        self._tags_no_db = None
        self.tags = None

        # Create a separate client for this DBM job to avoid concurrent query errors
        self._db_client = None

        # Get obfuscator options from config if available
        obfuscate_options = {
            'return_json_metadata': True,
            'collect_tables': True,
            'collect_commands': True,
            'collect_comments': True,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

        # Rate limiters for query samples
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=getattr(config, 'seen_samples_cache_maxsize', 10000),
            ttl=60 * 60 / getattr(config, 'samples_per_hour_per_query', 15),
        )

        self._collection_interval = collection_interval

        # Activity snapshot collection configuration
        self._activity_coll_enabled = getattr(config, 'activity_enabled', True)
        self._activity_coll_interval = getattr(config, 'activity_collection_interval', 10)
        self._activity_max_rows = getattr(config, 'activity_max_rows', 1000)
        self._time_since_last_activity_event = 0

        # Debug logging to verify config values
        self._check.log.info(
            "Activity config: enabled=%s, interval=%s, max_rows=%s",
            self._activity_coll_enabled,
            self._activity_coll_interval,
            self._activity_max_rows,
        )

    def _dbtags(self, db, *extra_tags):
        """
        Returns the default instance tags with the initial "db" tag replaced with the provided tag
        """
        t = ["db:" + db]
        if extra_tags:
            t.extend(extra_tags)
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    def _get_debug_tags(self):
        t = []
        if self._tags_no_db:
            t.extend(self._tags_no_db)
        return t

    def _report_check_hist_metrics(self, start_time, row_count, operation):
        """
        Report histogram metrics for check operations
        """
        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            "dd.clickhouse.statement_samples.{}.time".format(operation),
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._check.histogram(
            "dd.clickhouse.statement_samples.{}.rows".format(operation),
            row_count,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_active_queries(self):
        """
        Fetch currently running queries from system.processes
        This is analogous to Postgres querying pg_stat_activity
        """
        start_time = time.time()

        try:
            # Use the dedicated client for this job
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(ACTIVE_QUERIES_QUERY)
            rows = result.result_rows

            self._report_check_hist_metrics(start_time, len(rows), "get_active_queries")
            self._log.debug("Loaded %s rows from system.processes", len(rows))

            return rows
        except Exception as e:
            self._log.exception("Failed to collect active queries: %s", str(e))
            # Reset client on error to force reconnect
            self._db_client = None
            self._check.count(
                "dd.clickhouse.statement_samples.error",
                1,
                tags=self.tags + ["error:active-queries-fetch"] + self._get_debug_tags(),
                raw=True,
            )
            return []

    def _normalize_active_query_row(self, row):
        """
        Normalize a row from system.processes into a standard format
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
                # Original fields
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
                # New fields
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

            return self._obfuscate_and_normalize_query(normalized_row)
        except Exception as e:
            self._log.warning("Failed to normalize active query row: %s, row: %s", str(e), row)
            raise

    def _obfuscate_and_normalize_query(self, row):
        """
        Obfuscate the query and compute its signature
        """
        obfuscated_query = None
        try:
            statement = obfuscate_sql_with_metadata(row['query'], self._obfuscate_options)
            obfuscated_query = statement['query']
            metadata = statement['metadata']

            row['statement'] = obfuscated_query
            row['dd_tables'] = metadata.get('tables', None)
            row['dd_commands'] = metadata.get('commands', None)
            row['dd_comments'] = metadata.get('comments', None)

            # Compute query signature
            row['query_signature'] = compute_sql_signature(obfuscated_query)

        except Exception as e:
            self._log.warning("Failed to obfuscate query: %s, query: %s", str(e), row.get('query', '')[:100])
            # On obfuscation error, we still want to emit the row
            row['statement'] = None
            row['query_signature'] = compute_sql_signature(row['query'])
            row['dd_tables'] = None
            row['dd_commands'] = None
            row['dd_comments'] = None

        return row

    def _filter_and_normalize_statement_rows(self, rows):
        """
        Filter and normalize rows from system.processes
        """
        normalized_rows = []
        for row in rows:
            try:
                normalized_row = self._normalize_active_query_row(row)
                if normalized_row and normalized_row.get('statement'):
                    normalized_rows.append(normalized_row)
            except Exception as e:
                self._log.debug("Failed to normalize row: %s", e)

        return normalized_rows

    def _get_active_connections(self):
        """
        Get aggregated active connection counts from system.processes
        Similar to Postgres _get_active_connections from pg_stat_activity
        """
        try:
            start_time = time.time()

            # Use the dedicated client for this job
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(ACTIVE_CONNECTIONS_QUERY)
            rows = result.result_rows

            elapsed_ms = (time.time() - start_time) * 1000
            self._log.debug("Retrieved %s connection aggregation rows in %.2f ms", len(rows), elapsed_ms)

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

    def _to_active_session(self, row):
        """
        Convert a system.processes row to an active session
        Similar to Postgres _to_active_session
        """
        # Only include rows with successfully obfuscated statements
        if not row.get('statement'):
            return None

        # Remove null values and the raw query
        active_row = {key: val for key, val in row.items() if val is not None and key != 'query'}
        return active_row

    def _create_active_sessions(self, rows):
        """
        Create active sessions from system.processes rows
        Similar to Postgres _create_active_sessions
        """
        active_sessions_count = 0
        for row in rows:
            active_row = self._to_active_session(row)
            if active_row:
                active_sessions_count += 1
                yield active_row
            if active_sessions_count >= self._activity_max_rows:
                break

    def _create_activity_event(self, rows, active_connections):
        """
        Create a database monitoring activity event
        Similar to Postgres _create_activity_event
        """
        self._time_since_last_activity_event = time.time()
        active_sessions = []

        for row in self._create_active_sessions(rows):
            active_sessions.append(row)

        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "clickhouse",
            "dbm_type": "activity",
            "collection_interval": self._activity_coll_interval,
            "ddtags": self._tags_no_db,
            "timestamp": time.time() * 1000,
            "cloud_metadata": getattr(self._check, 'cloud_metadata', {}),
            'service': getattr(self._config, 'service', None),
            "clickhouse_activity": active_sessions,
            "clickhouse_connections": active_connections,
        }
        return event

    def _report_activity_event(self):
        """
        Check if we should report an activity event based on collection interval
        Similar to Postgres _report_activity_event
        """
        elapsed_s = time.time() - self._time_since_last_activity_event
        if elapsed_s < self._activity_coll_interval or not self._activity_coll_enabled:
            return False
        return True

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_statement_samples(self):
        """
        Main method to collect and submit statement samples from active queries
        Similar to Postgres _collect_statement_samples
        """
        start_time = time.time()

        # Get active queries from system.processes
        rows = self._get_active_queries()

        self._log.info("Retrieved %s active queries for processing", len(rows))

        # Normalize and filter rows
        rows = self._filter_and_normalize_statement_rows(rows)

        submitted_count = 0
        skipped_count = 0
        error_count = 0

        for row in rows:
            try:
                # Check if we should submit this sample based on rate limiting
                query_signature = row.get('query_signature')
                if not query_signature:
                    self._log.debug("Skipping row without query signature")
                    skipped_count += 1
                    continue

                if not self._seen_samples_ratelimiter.acquire(query_signature):
                    skipped_count += 1
                    continue

                # Create the event payload
                event = self._create_sample_event(row)

                # Log the event payload for debugging
                self._log.debug(
                    "Query sample event payload: ddsource=%s, query_signature=%s",
                    event.get('ddsource'),
                    query_signature[:50] if query_signature else 'N/A',
                )

                # Submit the event
                event_json = json.dumps(event, default=default_json_event_encoding)
                self._check.database_monitoring_query_sample(event_json)
                submitted_count += 1
                self._log.debug("Submitted query sample for signature: %s", query_signature[:50])

            except Exception as e:
                error_count += 1
                self._log.exception("Error processing active query row: %s", e)
                self._check.count(
                    "dd.clickhouse.statement_samples.error",
                    1,
                    tags=self.tags + ["error:process-row"] + self._get_debug_tags(),
                    raw=True,
                )

        elapsed_ms = (time.time() - start_time) * 1000

        self._log.info(
            "Statement sample collection complete: submitted=%s, skipped=%s, errors=%s, elapsed_ms=%.2f",
            submitted_count,
            skipped_count,
            error_count,
            elapsed_ms,
        )

        # Report cache size metrics
        self._check.gauge(
            "dd.clickhouse.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )

    def _create_sample_event(self, row):
        """
        Create a database monitoring query sample event (plan type)
        Format follows Postgres integration pattern
        This represents currently executing queries from system.processes
        """
        # Use current_database from the query if available, fallback to check's default db
        db = row.get('current_database') or self._check._db

        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "clickhouse",
            "dbm_type": "plan",  # Using "plan" type for query samples
            "ddtags": ",".join(self._dbtags(db)),
            "timestamp": int(time.time() * 1000),
            "db": {
                "instance": db,
                "query_signature": row.get('query_signature'),
                "statement": row.get('statement'),
                "user": row.get('user'),
                "metadata": {
                    "tables": row.get('dd_tables'),
                    "commands": row.get('dd_commands'),
                    "comments": row.get('dd_comments'),
                },
            },
            "clickhouse": {k: v for k, v in row.items() if k not in system_processes_sample_exclude_keys},
        }

        # Add duration if available (elapsed time in seconds, convert to nanoseconds)
        if row.get('elapsed'):
            event['duration'] = int(row['elapsed'] * 1e9)

        return event

    def run_job(self):
        """
        Main job execution method called by DBMAsyncJob
        """
        # Filter out internal tags
        self.tags = [t for t in self._check._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]

        # Check if we should collect activity snapshots
        collect_activity = self._report_activity_event()

        # Always collect statement samples
        self._collect_statement_samples()

        # Collect and submit activity event if it's time
        if collect_activity:
            try:
                start_time = time.time()

                # Get active queries for activity snapshot
                rows = self._get_active_queries()
                self._log.info("DEBUG: Retrieved %s raw rows from system.processes", len(rows))
                rows = self._filter_and_normalize_statement_rows(rows)
                self._log.info("DEBUG: After filtering/normalization: %s rows", len(rows))

                # Get active connections aggregation
                active_connections = self._get_active_connections()

                # Create and submit activity event
                activity_event = self._create_activity_event(rows, active_connections)
                self._log.info(
                    "DEBUG: Activity event has %s sessions", len(activity_event.get('clickhouse_activity', []))
                )
                self._check.database_monitoring_query_activity(
                    json.dumps(activity_event, default=default_json_event_encoding)
                )

                elapsed_ms = (time.time() - start_time) * 1000
                self._check.histogram(
                    "dd.clickhouse.collect_activity_snapshot.time",
                    elapsed_ms,
                    tags=self.tags + self._get_debug_tags(),
                    raw=True,
                )

                self._log.info(
                    "Activity snapshot collected and submitted: sessions=%s, connections=%s, elapsed_ms=%.2f",
                    len(activity_event.get('clickhouse_activity', [])),
                    len(activity_event.get('clickhouse_connections', [])),
                    elapsed_ms,
                )

            except Exception as e:
                self._log.exception("Failed to collect activity snapshot: %s", e)
                self._check.count(
                    "dd.clickhouse.statement_samples.error",
                    1,
                    tags=self.tags + ["error:collect-activity-snapshot"] + self._get_debug_tags(),
                    raw=True,
                )
