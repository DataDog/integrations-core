# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING

from cachetools import TTLCache

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, RateLimitingTTLCache, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# Query to fetch individual completed queries from system.query_log
# Unlike statements.py which aggregates, this query returns individual query executions
# Note: peak_memory_usage may not exist in all ClickHouse versions (e.g., ClickHouse Cloud)
# We use a subquery with hasColumnInTable() to conditionally include it
#
# Uses {query_log_table} placeholder for ClickHouse Cloud clusterAllReplicas() support:
# - For ClickHouse Cloud: clusterAllReplicas('default', system.query_log)
# - For self-hosted: system.query_log
COMPLETED_QUERIES_QUERY = """
SELECT
    normalized_query_hash,
    query,
    user,
    type as query_type,
    databases,
    tables,
    query_duration_ms,
    read_rows,
    read_bytes,
    written_rows,
    written_bytes,
    result_rows,
    result_bytes,
    memory_usage,
    memory_usage as peak_memory_usage,
    query_start_time_microseconds,
    event_time_microseconds,
    query_id,
    initial_query_id,
    query_kind,
    is_initial_query
FROM {query_log_table}
WHERE
  event_time_microseconds > fromUnixTimestamp64Micro({last_checkpoint_microseconds})
  AND event_time_microseconds <= fromUnixTimestamp64Micro({current_checkpoint_microseconds})
  AND event_date >= toDate(fromUnixTimestamp64Micro({last_checkpoint_microseconds}))
  AND type = 'QueryFinish'
  AND is_initial_query = 1
  AND query != ''
  AND normalized_query_hash != 0
  {internal_user_filter}
ORDER BY event_time_microseconds ASC
LIMIT {max_samples}
"""

# List of internal Cloud users to exclude from query samples
# These are Datadog Cloud internal service accounts
INTERNAL_CLOUD_USERS = frozenset(
    {
        # Add internal Cloud user names here as needed
        # 'internal_service_user',
    }
)


def agent_check_getter(self):
    return self._check


class ClickhouseCompletedQuerySamples(DBMAsyncJob):
    """Collects individual completed query samples from system.query_log"""

    # Persistent cache key for storing the last collection timestamp
    CHECKPOINT_CACHE_KEY = "completed_query_samples_last_checkpoint_microseconds"

    def __init__(self, check: ClickhouseCheck, config):
        collection_interval = float(getattr(config, 'collection_interval', 10))
        super(ClickhouseCompletedQuerySamples, self).__init__(
            check,
            run_sync=getattr(config, 'run_sync', False),
            enabled=getattr(config, 'enabled', True),
            expected_db_exceptions=(Exception,),
            min_collection_interval=check.check_interval if hasattr(check, 'check_interval') else 15,
            dbms="clickhouse",
            rate_limit=1 / float(collection_interval),
            job_name="query-completions",
        )
        self._check = check
        self._collection_interval = collection_interval
        self._config = config
        self._tags_no_db = None
        self.tags = None

        # Create a separate client for this DBM job to avoid concurrent query errors
        self._db_client = None

        # Obfuscator options
        obfuscate_options = {
            'return_json_metadata': True,
            'collect_tables': True,
            'collect_commands': True,
            'collect_comments': True,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

        # Rate limiting: limit samples per query signature
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=getattr(config, 'seen_samples_cache_maxsize', 10000),
            ttl=60 * 60 / getattr(config, 'samples_per_hour_per_query', 15),
        )

        # Maximum number of samples to collect per run
        self._max_samples_per_collection = getattr(config, 'max_samples_per_collection', 1000)

        # Checkpoint state for exactly-once collection semantics
        # Will be loaded from persistent cache on first collection
        self._last_checkpoint_microseconds = None
        self._current_checkpoint_microseconds = None

    def _execute_query(self, query):
        """Execute a query and return the results using the dedicated client"""
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")
        try:
            # Use the dedicated client for this job
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(query)
            return result.result_rows
        except Exception as e:
            self._log.warning("Failed to run query: %s", e)
            # Reset client on error to force reconnect
            self._db_client = None
            raise e

    def run_job(self):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        self.collect_completed_query_samples()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_completed_query_samples(self):
        """
        Collect and submit completed query samples, saving checkpoint on success.

        Critical: Checkpoint is ONLY saved after successful submission to ensure
        exactly-once semantics and automatic retry on failure.
        """
        try:
            # Step 1: Collect rows (loads checkpoint internally)
            rows = self._collect_completed_queries()

            if not rows:
                # No new queries, but still advance checkpoint
                if self._current_checkpoint_microseconds:
                    self._save_checkpoint(self._current_checkpoint_microseconds)
                    self._last_checkpoint_microseconds = self._current_checkpoint_microseconds
                    self._log.debug("Advanced checkpoint (no new completed queries)")
                return

            # Step 2: Apply rate limiting and create payload
            payload = self._create_batched_payload(rows)

            if not payload or not payload.get('clickhouse_query_completions'):
                self._log.debug("No query completions after rate limiting")
                # Still advance checkpoint even if all were rate-limited
                if self._current_checkpoint_microseconds:
                    self._save_checkpoint(self._current_checkpoint_microseconds)
                    self._last_checkpoint_microseconds = self._current_checkpoint_microseconds
                return

            # Step 3: Submit payload
            payload_data = json.dumps(payload, default=default_json_event_encoding)
            num_completions = len(payload.get('clickhouse_query_completions', []))
            self._log.info(
                "Submitting query completions payload: %d bytes, %d completions",
                len(payload_data),
                num_completions,
            )
            self._check.database_monitoring_query_activity(payload_data)

            # Step 4: CRITICAL - Only save checkpoint AFTER successful submission
            if self._current_checkpoint_microseconds:
                self._save_checkpoint(self._current_checkpoint_microseconds)
                self._last_checkpoint_microseconds = self._current_checkpoint_microseconds
                self._log.info(
                    "Successfully advanced checkpoint to %d microseconds",
                    self._current_checkpoint_microseconds
                )

        except Exception:
            self._log.exception('Unable to collect completed query samples due to an error')
            # Don't save checkpoint on error - will retry same window next time
            return

    def _get_internal_user_filter(self) -> str:
        """
        Build the SQL filter to exclude internal Cloud users.
        Returns empty string if no users are configured for exclusion.
        """
        filters = ["user NOT LIKE '%-internal'"]
        if INTERNAL_CLOUD_USERS:
            users_list = ", ".join(f"'{user}'" for user in INTERNAL_CLOUD_USERS)
            filters.append(f"user NOT IN ({users_list})")
        return "AND " + " AND ".join(filters)

    def _load_checkpoint(self) -> int:
        """
        Load the last successful collection timestamp from persistent cache.

        Returns:
            int: Timestamp in microseconds since Unix epoch

        Behavior:
            - On first run: Returns (current_time - collection_interval)
            - On subsequent runs: Returns last saved checkpoint
            - On cache error: Falls back to default lookback
            - Uses ClickHouse server time to avoid clock drift
        """
        try:
            # Attempt to read from persistent cache
            cached_value = self._check.read_persistent_cache(self.CHECKPOINT_CACHE_KEY)
            if cached_value:
                checkpoint = int(cached_value)
                self._log.debug(
                    "Loaded checkpoint from persistent cache: %d microseconds",
                    checkpoint
                )
                return checkpoint
        except Exception as e:
            self._log.warning(
                "Could not load checkpoint from persistent cache: %s. "
                "Will use default lookback window.",
                str(e)
            )

        # First run or cache error - calculate default checkpoint
        # IMPORTANT: Use ClickHouse's time, not agent's time, to avoid clock drift
        try:
            result = self._execute_query("SELECT toUnixTimestamp64Micro(now64(6))")
            if result and len(result) > 0:
                current_time_micros = int(result[0][0])

                # Lookback by collection_interval seconds
                default_checkpoint = current_time_micros - int(
                    self._collection_interval * 1_000_000
                )

                self._log.info(
                    "Using default checkpoint (lookback %d seconds): %d microseconds",
                    int(self._collection_interval),
                    default_checkpoint
                )
                return default_checkpoint
        except Exception as e:
            self._log.error("Failed to get current time from ClickHouse: %s", e)
            raise

        # Should rarely reach here
        raise Exception("Unable to determine checkpoint timestamp")

    def _save_checkpoint(self, timestamp_microseconds: int):
        """
        Save the current collection timestamp to persistent cache.

        Args:
            timestamp_microseconds: The checkpoint timestamp to save

        Note:
            - Only called AFTER successful sample submission
            - Failures are logged but don't raise exceptions
            - Next collection will retry with previous checkpoint
        """
        try:
            self._check.write_persistent_cache(
                self.CHECKPOINT_CACHE_KEY,
                str(timestamp_microseconds)
            )
            self._log.debug(
                "Saved checkpoint to persistent cache: %d microseconds",
                timestamp_microseconds
            )
        except Exception as e:
            self._log.error(
                "Failed to save checkpoint to persistent cache: %s. "
                "Next collection will retry the same time window.",
                str(e)
            )

    def _get_current_checkpoint_microseconds(self) -> int:
        """
        Get the current checkpoint timestamp from ClickHouse server.

        Returns:
            int: Current timestamp in microseconds

        Note:
            - Always uses ClickHouse's clock, not agent's clock
            - This prevents issues with clock drift between agent and database
            - Captured BEFORE executing the collection query
        """
        try:
            result = self._execute_query("SELECT toUnixTimestamp64Micro(now64(6))")
            if result and len(result) > 0:
                return int(result[0][0])
        except Exception as e:
            self._log.error(
                "Failed to get current timestamp from ClickHouse: %s",
                str(e)
            )
            raise

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_completed_queries(self):
        """
        Load completed query samples using checkpoint-based collection.

        Flow:
            1. Load or initialize last checkpoint
            2. Capture current checkpoint (before query execution)
            3. Query window: (last_checkpoint, current_checkpoint]
            4. Return results (checkpoint saved later on success)

        For ClickHouse Cloud: Uses clusterAllReplicas('default', system.query_log) to query
        all nodes in the cluster.
        For self-hosted: Queries only the local node's query_log.
        """
        try:
            # Step 1: Load checkpoint if first run
            if self._last_checkpoint_microseconds is None:
                self._last_checkpoint_microseconds = self._load_checkpoint()

            # Step 2: Capture current checkpoint BEFORE executing query
            # This ensures we don't miss any queries that arrive during execution
            self._current_checkpoint_microseconds = self._get_current_checkpoint_microseconds()

            # Get the appropriate table reference based on deployment type
            query_log_table = self._check.get_system_table('query_log')

            # Step 3: Build query with checkpoint window
            query = COMPLETED_QUERIES_QUERY.format(
                query_log_table=query_log_table,
                last_checkpoint_microseconds=self._last_checkpoint_microseconds,
                current_checkpoint_microseconds=self._current_checkpoint_microseconds,
                internal_user_filter=self._get_internal_user_filter(),
                max_samples=self._max_samples_per_collection,
            )

            # Step 4: Execute query
            rows = self._execute_query(query)

            # Calculate actual time window
            window_seconds = (
                self._current_checkpoint_microseconds -
                self._last_checkpoint_microseconds
            ) / 1_000_000.0

            # Log with deployment type indicator
            deployment_mode = "Cloud (cluster-wide)" if self._check.is_clickhouse_cloud else "self-hosted (local)"
            self._log.info(
                "Loaded %d completed queries from %s [%s]. "
                "Window: [%d, %d] microseconds (%.2f seconds elapsed)",
                len(rows),
                query_log_table,
                deployment_mode,
                self._last_checkpoint_microseconds,
                self._current_checkpoint_microseconds,
                window_seconds
            )

            # Step 5: Convert to list of dicts and obfuscate
            result_rows = []
            for row in rows:
                (
                    normalized_query_hash,
                    query_text,
                    user,
                    query_type,
                    databases,
                    tables,
                    query_duration_ms,
                    read_rows,
                    read_bytes,
                    written_rows,
                    written_bytes,
                    result_rows_count,
                    result_bytes,
                    memory_usage,
                    peak_memory_usage,
                    query_start_time_microseconds,
                    event_time_microseconds,
                    query_id,
                    initial_query_id,
                    query_kind,
                    is_initial_query,
                ) = row

                # Helper to convert datetime to microseconds (ClickHouse Cloud returns datetime objects)
                def to_microseconds(val):
                    if val is None:
                        return 0
                    if hasattr(val, 'timestamp'):  # datetime object
                        return int(val.timestamp() * 1_000_000)
                    return int(val)

                row_dict = {
                    'normalized_query_hash': str(normalized_query_hash),
                    'query': str(query_text) if query_text else '',
                    'user': str(user) if user else '',
                    'query_type': str(query_type) if query_type else '',
                    'databases': str(databases[0]) if databases and len(databases) > 0 else '',
                    'tables': tables if tables else [],
                    'query_duration_ms': float(query_duration_ms) if query_duration_ms else 0.0,
                    'read_rows': int(read_rows) if read_rows else 0,
                    'read_bytes': int(read_bytes) if read_bytes else 0,
                    'written_rows': int(written_rows) if written_rows else 0,
                    'written_bytes': int(written_bytes) if written_bytes else 0,
                    'result_rows': int(result_rows_count) if result_rows_count else 0,
                    'result_bytes': int(result_bytes) if result_bytes else 0,
                    'memory_usage': int(memory_usage) if memory_usage else 0,
                    'peak_memory_usage': int(peak_memory_usage) if peak_memory_usage else 0,
                    'query_start_time_microseconds': to_microseconds(query_start_time_microseconds),
                    'event_time_microseconds': to_microseconds(event_time_microseconds) or self._current_checkpoint_microseconds,
                    'query_id': str(query_id) if query_id else '',
                    'initial_query_id': str(initial_query_id) if initial_query_id else '',
                    'query_kind': str(query_kind) if query_kind else '',
                    'is_initial_query': bool(is_initial_query) if is_initial_query is not None else True,
                }

                # Obfuscate the query
                obfuscated_row = self._normalize_query(row_dict)
                if obfuscated_row:
                    result_rows.append(obfuscated_row)

            return result_rows

        except Exception as e:
            self._log.exception("Failed to load completed queries from system.query_log: %s", e)

            # IMPORTANT: Don't update checkpoint on error
            # Next collection will retry the same window

            self._check.count(
                "dd.clickhouse.completed_query_samples.error",
                1,
                tags=self.tags + ["error:query_log_load_failed"],
                raw=True,
            )
            return []

    def _normalize_query(self, row):
        """
        Normalize and obfuscate a single query row
        """
        try:
            query_text = row['query']
            statement = obfuscate_sql_with_metadata(query_text, self._obfuscate_options)
        except Exception as e:
            self._log.debug("Failed to obfuscate query | err=[%s]", e)
            self._check.count(
                "dd.clickhouse.completed_query_samples.error",
                1,
                tags=self.tags + ["error:obfuscate-query"],
                raw=True,
            )
            return None

        obfuscated_query = statement['query']
        row['statement'] = obfuscated_query
        row['query_signature'] = compute_sql_signature(obfuscated_query)

        metadata = statement['metadata']
        row['dd_tables'] = metadata.get('tables', None)
        row['dd_commands'] = metadata.get('commands', None)
        row['dd_comments'] = metadata.get('comments', None)

        return row

    def _create_batched_payload(self, rows):
        """
        Create a batched payload following SQL Server query_completion pattern.
        Apply rate limiting and filter out rate-limited queries.

        Returns:
            dict: Batched payload with array of query completion details
        """
        query_completions = []

        for row in rows:
            query_signature = row.get('query_signature')
            if not query_signature:
                continue

            # Apply rate limiting
            if not self._seen_samples_ratelimiter.acquire(query_signature):
                continue

            # Create query_details structure (similar to SQL Server)
            query_details = {
                'statement': row.get('statement'),
                'query_signature': query_signature,
                'duration_ms': row.get('query_duration_ms', 0),
                'database_name': row.get('databases', ''),
                'username': row.get('user', ''),
                'query_id': row.get('query_id', ''),
                'query_type': row.get('query_type', ''),
                'query_kind': row.get('query_kind', ''),
                'normalized_query_hash': row.get('normalized_query_hash', ''),
                'read_rows': row.get('read_rows', 0),
                'read_bytes': row.get('read_bytes', 0),
                'written_rows': row.get('written_rows', 0),
                'written_bytes': row.get('written_bytes', 0),
                'result_rows': row.get('result_rows', 0),
                'result_bytes': row.get('result_bytes', 0),
                'memory_usage': row.get('memory_usage', 0),
                'peak_memory_usage': row.get('peak_memory_usage', 0),
                'query_start_time_microseconds': row.get('query_start_time_microseconds', 0),
                'event_time_microseconds': row.get('event_time_microseconds', 0),
                'initial_query_id': row.get('initial_query_id', ''),
                'is_initial_query': row.get('is_initial_query', True),
                'metadata': {
                    'tables': row.get('dd_tables'),
                    'commands': row.get('dd_commands'),
                    'comments': row.get('dd_comments'),
                },
            }

            query_completions.append({'query_details': query_details})

        if not query_completions:
            return None

        # Create payload following SQL Server pattern
        payload = {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': datadog_agent.get_version(),
            'ddsource': 'clickhouse',
            'dbm_type': 'query_completion',
            'collection_interval': self._collection_interval,
            'ddtags': self._tags_no_db,
            'timestamp': time.time() * 1000,
            'clickhouse_version': self._get_clickhouse_version(),
            'service': getattr(self._check, 'service', None),
            'clickhouse_query_completions': query_completions,
        }

        return payload

    def _get_clickhouse_version(self):
        """Get ClickHouse version string"""
        try:
            version_rows = self._check.execute_query_raw('SELECT version()')
            if version_rows:
                return str(version_rows[0][0])
        except Exception:
            pass
        return 'unknown'


