# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING

from cachetools import TTLCache
from clickhouse_connect.driver.exceptions import OperationalError

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# Persistent cache key for storing the last collection checkpoint
# This enables checkpoint-based collection that survives agent restarts
CHECKPOINT_CACHE_KEY = "query_metrics_last_checkpoint_microseconds"

# Query to fetch aggregated metrics from system.query_log using checkpoint-based collection
#
# Key design decisions:
# - Uses microsecond precision (event_time_microseconds) to avoid missing queries
# - Uses exclusive lower bound (>) and inclusive upper bound (<=) to prevent double-counting
# - Uses {query_log_table} placeholder for ClickHouse Cloud clusterAllReplicas() support
# - Uses event_date predicate for partition pruning optimization
# - Uses is_initial_query=1 to only count queries once (not sub-queries)
# - Uses type != 'QueryStart' to get one record per completed query
# - Uses normalizeQuery() to get query text with wildcards representing the entire set
# - Uses quantiles() to calculate p50, p90, p95, p99 simultaneously
# - Returns max(event_time_microseconds) to track the latest query timestamp in each batch
#
# Note: With checkpoint-based collection, we no longer need derivative calculation.
# Each collection window is exclusive, so metrics represent the actual values for that window.
#
# For ClickHouse Cloud, {query_log_table} becomes clusterAllReplicas('default', system.query_log)
# to query all nodes in the cluster. For self-hosted, it's just system.query_log.

# List of internal Cloud users to exclude from query metrics
# These are Datadog Cloud internal service accounts
INTERNAL_CLOUD_USERS = frozenset(
    {
        # Add internal Cloud user names here as needed
        # 'internal_service_user',
    }
)

STATEMENTS_QUERY = """
SELECT
    normalized_query_hash,
    normalizeQuery(any(query)) as query_text,
    any(user) as query_user,
    any(type) as query_type,
    any(exception_code) as exception_code,
    any(databases) as databases,
    any(tables) as tables,
    count() as execution_count,
    sum(query_duration_ms) as total_duration_ms,
    quantiles(0.5, 0.9, 0.95, 0.99)(query_duration_ms) as duration_quantiles,
    sum(read_rows) as total_read_rows,
    sum(read_bytes) as total_read_bytes,
    sum(written_rows) as total_written_rows,
    sum(written_bytes) as total_written_bytes,
    sum(result_rows) as total_result_rows,
    sum(result_bytes) as total_result_bytes,
    sum(memory_usage) as total_memory_usage,
    max(memory_usage) as peak_memory_usage,
    max(event_time_microseconds) as max_event_time_microseconds
FROM {query_log_table}
WHERE
    event_time_microseconds > fromUnixTimestamp64Micro({last_checkpoint_microseconds})
    AND event_time_microseconds <= fromUnixTimestamp64Micro({current_checkpoint_microseconds})
    AND event_date >= toDate(fromUnixTimestamp64Micro({last_checkpoint_microseconds}))
    AND type != 'QueryStart'
    AND is_initial_query = 1
    AND query != ''
    AND normalized_query_hash != 0
    {internal_user_filter}
GROUP BY normalized_query_hash
LIMIT 200
"""

# Query to get current timestamp from ClickHouse in microseconds
# Using the database's clock avoids drift between agent and database time
GET_CURRENT_TIME_QUERY = "SELECT toUnixTimestamp64Micro(now64(6))"


def agent_check_getter(self):
    return self._check


def _row_key(row):
    """
    :param row: a normalized row from system.query_log
    :return: a tuple uniquely identifying this row
    """
    return row['query_signature'], row.get('user', ''), row.get('databases', '')


class ClickhouseStatementMetrics(DBMAsyncJob):
    """
    Collects telemetry for SQL statements from system.query_log using checkpoint-based collection.

    Checkpoint-based collection ensures:
    - No queries are missed due to collection delays
    - No queries are double-counted
    - Microsecond precision for high-throughput environments
    - State survives agent restarts via persistent cache
    """

    def __init__(self, check: ClickhouseCheck, config):
        collection_interval = float(getattr(config, 'collection_interval', 10))
        super(ClickhouseStatementMetrics, self).__init__(
            check,
            run_sync=getattr(config, 'run_sync', False),
            enabled=getattr(config, 'enabled', True),
            expected_db_exceptions=(Exception,),
            min_collection_interval=check.check_interval if hasattr(check, 'check_interval') else 15,
            dbms="clickhouse",
            rate_limit=1 / float(collection_interval),
            job_name="query-metrics",
        )
        self._check = check
        self._metrics_collection_interval = collection_interval
        self._config = config
        self._tags_no_db = None
        self.tags = None
        self._state = StatementMetrics()

        # Dedicated client for this job (uses shared connection pool)
        self._db_client = None

        # Track the current checkpoint for this collection cycle
        # This is set during collection and saved only after successful submission
        self._pending_checkpoint_microseconds = None

        # Obfuscator options
        obfuscate_options = {
            'return_json_metadata': True,
            'collect_tables': True,
            'collect_commands': True,
            'collect_comments': True,
        }
        self._obfuscate_options = to_native_string(json.dumps(obfuscate_options))

        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=getattr(config, 'full_statement_text_cache_max_size', 10000),
            ttl=60 * 60 / getattr(config, 'full_statement_text_samples_per_hour_per_query', 1),
        )

    def cancel(self):
        """Cancel the job and clean up the dedicated client."""
        super(ClickhouseStatementMetrics, self).cancel()
        self._close_db_client()

    def _close_db_client(self):
        """Close the dedicated database client if it exists."""
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing DBM client: %s", e)
            self._db_client = None

    def _execute_query(self, query):
        """Execute a query using the dedicated client (with shared connection pool)."""
        if self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")
        try:
            if self._db_client is None:
                self._db_client = self._check.create_dbm_client()
            result = self._db_client.query(query)
            return result.result_rows
        except OperationalError as e:
            # Connection-related error - reset client to force reconnect
            self._log.warning("Connection error, will reconnect: %s", e)
            self._close_db_client()
            raise
        except Exception as e:
            # Query error (syntax, timeout, etc.) - don't reset connection
            self._log.warning("Query error: %s", e)
            raise

    def _get_current_checkpoint_from_db(self) -> int:
        """
        Get the current timestamp from ClickHouse in microseconds.
        Using the database's clock avoids drift between agent and database time.

        :return: Current timestamp in microseconds (Unix epoch)
        """
        rows = self._execute_query(GET_CURRENT_TIME_QUERY)
        if rows and len(rows) > 0:
            return int(rows[0][0])
        # Fallback to agent time if query fails (should not happen)
        return int(time.time() * 1_000_000)

    def _read_checkpoint(self) -> int | None:
        """
        Read the last checkpoint from persistent cache.

        :return: Last checkpoint in microseconds, or None if no checkpoint exists
        """
        checkpoint_str = self._check.read_persistent_cache(CHECKPOINT_CACHE_KEY)
        if checkpoint_str:
            try:
                return int(checkpoint_str)
            except (ValueError, TypeError):
                self._log.warning("Invalid checkpoint value in cache: %s", checkpoint_str)
        return None

    def _save_checkpoint(self, checkpoint_microseconds: int):
        """
        Save checkpoint to persistent cache.
        This should only be called after successful metrics submission.

        :param checkpoint_microseconds: Checkpoint timestamp in microseconds
        """
        self._check.write_persistent_cache(CHECKPOINT_CACHE_KEY, str(checkpoint_microseconds))
        self._log.debug("Saved checkpoint: %d", checkpoint_microseconds)

    def _get_collection_window(self) -> tuple[int, int]:
        """
        Calculate the collection time window using checkpoint-based logic.

        Returns:
            tuple: (last_checkpoint_microseconds, current_checkpoint_microseconds)

        Logic:
        - First run: Use (current_time - collection_interval) as starting point
        - Subsequent runs: Use last saved checkpoint as starting point
        - Always use current database time as end point
        """
        # Get current time from ClickHouse (avoids clock drift)
        current_checkpoint = self._get_current_checkpoint_from_db()

        # Try to read last checkpoint from persistent cache
        last_checkpoint = self._read_checkpoint()

        if last_checkpoint is None:
            # First run: Create initial lookback window
            # Go back by collection_interval seconds to establish baseline
            initial_lookback_microseconds = int(self._metrics_collection_interval * 1_000_000)
            last_checkpoint = current_checkpoint - initial_lookback_microseconds
            self._log.info(
                "First collection run. Creating initial window: last=%d, current=%d (lookback=%ds)",
                last_checkpoint,
                current_checkpoint,
                self._metrics_collection_interval,
            )
        else:
            # Calculate actual window size for logging
            window_seconds = (current_checkpoint - last_checkpoint) / 1_000_000
            self._log.debug(
                "Using checkpoint-based window: last=%d, current=%d (window=%.2fs)",
                last_checkpoint,
                current_checkpoint,
                window_seconds,
            )

        return last_checkpoint, current_checkpoint

    def run_job(self):
        # do not emit any dd.internal metrics for DBM specific check code
        self.tags = [t for t in self._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]
        self.collect_per_statement_metrics()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_per_statement_metrics(self):
        """
        Collect per-statement metrics from system.query_log and emit as:
        1. FQT events (dbm_type: fqt) - for query text catalog
        2. Query metrics payload - for time-series metrics

        Uses checkpoint-based collection to ensure no queries are missed or double-counted.
        Checkpoint is only saved after successful submission to handle errors gracefully.
        """
        try:
            # Reset pending checkpoint at the start of each collection
            self._pending_checkpoint_microseconds = None

            rows = self._collect_metrics_rows()
            if not rows:
                # Even if no rows, save the checkpoint to advance the window
                # This prevents re-querying the same empty window repeatedly
                if self._pending_checkpoint_microseconds:
                    self._save_checkpoint(self._pending_checkpoint_microseconds)
                return

            # Emit FQT (Full Query Text) events
            for event in self._rows_to_fqt_events(rows):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

            # Prepare metrics payload wrapper
            payload_wrapper = {
                'host': self._check.reported_hostname,
                'database_instance': self._check.database_identifier,
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._metrics_collection_interval,
                'tags': self._tags_no_db,
                'ddagentversion': datadog_agent.get_version(),
                'clickhouse_version': self._check.dbms_version,
            }

            # Get query metrics payloads (may be split into multiple if too large)
            payloads = self._get_query_metrics_payloads(payload_wrapper, rows)

            for payload in payloads:
                payload_data = json.loads(payload)
                num_rows = len(payload_data.get('clickhouse_rows', []))
                self._log.info(
                    "Submitting query metrics payload: %d bytes, %d rows, database_instance=%s",
                    len(payload),
                    num_rows,
                    payload_data.get('database_instance', 'MISSING'),
                )
                self._check.database_monitoring_query_metrics(payload)

            # Only save checkpoint after ALL payloads are successfully submitted
            # This ensures we don't lose data if submission fails partway through
            if self._pending_checkpoint_microseconds:
                self._save_checkpoint(self._pending_checkpoint_microseconds)
                self._log.info(
                    "Collection complete. Checkpoint saved: %d",
                    self._pending_checkpoint_microseconds,
                )

        except Exception:
            self._log.exception('Unable to collect statement metrics due to an error')
            # Do NOT save checkpoint on error - this ensures we retry the same window
            return []

    def _get_query_metrics_payloads(self, payload_wrapper, rows):
        """
        Split rows into multiple payloads if needed to avoid exceeding size limits
        """
        payloads = []
        max_size = 5 * 1024 * 1024  # 5MB limit

        queue = [rows]
        while queue:
            current = queue.pop()
            if len(current) == 0:
                continue

            payload = copy.deepcopy(payload_wrapper)
            payload["clickhouse_rows"] = current
            serialized_payload = json.dumps(payload, default=default_json_event_encoding)
            size = len(serialized_payload)

            if size < max_size:
                payloads.append(serialized_payload)
            else:
                if len(current) == 1:
                    self._log.warning(
                        "A single query is too large to send to Datadog. This query will be dropped. size=%d",
                        size,
                    )
                    continue
                mid = len(current) // 2
                queue.append(current[:mid])
                queue.append(current[mid:])

        return payloads

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

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_query_log_statements(self):
        """
        Load aggregated query metrics from system.query_log using checkpoint-based collection.

        This is analogous to Postgres loading from pg_stat_statements, but uses
        microsecond-precision timestamps to ensure no queries are missed.

        For ClickHouse Cloud: Uses clusterAllReplicas('default', system.query_log) to query
        all nodes in the cluster, since replicas are abstracted behind the managed service.

        For self-hosted: Queries only the local node's query_log - each ClickHouse node
        maintains its own query_log table with queries executed on that specific node.
        """
        try:
            # Get the collection time window
            last_checkpoint, current_checkpoint = self._get_collection_window()

            # Store the current checkpoint for saving after successful submission
            self._pending_checkpoint_microseconds = current_checkpoint

            # Calculate window size for logging
            window_seconds = (current_checkpoint - last_checkpoint) / 1_000_000

            # Get the appropriate table reference based on deployment type
            # For Cloud: clusterAllReplicas('default', system.query_log)
            # For self-hosted: system.query_log
            query_log_table = self._check.get_system_table('query_log')

            query = STATEMENTS_QUERY.format(
                query_log_table=query_log_table,
                last_checkpoint_microseconds=last_checkpoint,
                current_checkpoint_microseconds=current_checkpoint,
                internal_user_filter=self._get_internal_user_filter(),
            )
            rows = self._execute_query(query)

            # Log with deployment type indicator
            deployment_mode = (
                "cluster-wide (single endpoint)" if self._check.is_single_endpoint_mode else "local (direct)"
            )
            self._log.info(
                "Loaded %d rows from %s [%s] (window=%.2fs, last=%d, current=%d)",
                len(rows),
                query_log_table,
                deployment_mode,
                window_seconds,
                last_checkpoint,
                current_checkpoint,
            )

            # Convert to list of dicts
            result_rows = []
            for row in rows:
                (
                    normalized_query_hash,
                    query_text,
                    query_user,
                    query_type,
                    exception_code,
                    databases,
                    tables,
                    execution_count,
                    total_duration_ms,
                    duration_quantiles,  # Array of [p50, p90, p95, p99]
                    total_read_rows,
                    total_read_bytes,
                    total_written_rows,
                    total_written_bytes,
                    total_result_rows,
                    total_result_bytes,
                    total_memory_usage,
                    peak_memory_usage,
                    max_event_time_microseconds,  # New field for checkpoint tracking
                ) = row

                # Parse quantiles array: [p50, p90, p95, p99]
                p50_time = float(duration_quantiles[0]) if duration_quantiles and len(duration_quantiles) > 0 else 0.0
                p90_time = float(duration_quantiles[1]) if duration_quantiles and len(duration_quantiles) > 1 else 0.0
                p95_time = float(duration_quantiles[2]) if duration_quantiles and len(duration_quantiles) > 2 else 0.0
                p99_time = float(duration_quantiles[3]) if duration_quantiles and len(duration_quantiles) > 3 else 0.0

                # Calculate mean_time directly since we're not using derivatives
                # With checkpoint-based collection, count is the actual count for this window
                mean_time = float(total_duration_ms) / execution_count if execution_count > 0 else 0.0

                result_rows.append(
                    {
                        'normalized_query_hash': str(normalized_query_hash),
                        'query': str(query_text) if query_text else '',
                        'user': str(query_user) if query_user else '',
                        'query_type': str(query_type) if query_type else '',
                        'exception_code': str(exception_code) if exception_code else '',
                        'databases': str(databases[0]) if databases and len(databases) > 0 else '',
                        'dd_tables': tables if tables else [],  # Use ClickHouse native tables column
                        'count': int(execution_count) if execution_count else 0,
                        'total_time': float(total_duration_ms) if total_duration_ms else 0.0,
                        # Mean time calculated directly (no derivative needed with checkpointing)
                        'mean_time': mean_time,
                        # Quantile metrics (p50, p90, p95, p99) - point-in-time aggregates for this window
                        'p50_time': p50_time,
                        'p90_time': p90_time,
                        'p95_time': p95_time,
                        'p99_time': p99_time,
                        'result_rows': int(total_result_rows) if total_result_rows else 0,
                        'read_rows': int(total_read_rows) if total_read_rows else 0,
                        'read_bytes': int(total_read_bytes) if total_read_bytes else 0,
                        'written_rows': int(total_written_rows) if total_written_rows else 0,
                        'written_bytes': int(total_written_bytes) if total_written_bytes else 0,
                        'result_bytes': int(total_result_bytes) if total_result_bytes else 0,
                        'memory_usage': int(total_memory_usage) if total_memory_usage else 0,
                        'peak_memory_usage': int(peak_memory_usage) if peak_memory_usage else 0,
                    }
                )

            return result_rows

        except Exception as e:
            self._log.exception("Failed to load statements from system.query_log: %s", e)
            self._check.count(
                "dd.clickhouse.statement_metrics.error",
                1,
                tags=self.tags + ["error:query_log_load_failed"],
                raw=True,
            )
            # Re-raise to let outer handler skip checkpoint advancement
            # This ensures the failed time window will be retried
            raise

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_metrics_rows(self):
        """
        Collect and normalize query metrics rows.

        With checkpoint-based collection, we no longer need derivative calculation.
        Each collection window is exclusive (> last_checkpoint AND <= current_checkpoint),
        so the metrics represent the actual values for that specific time window.
        """
        rows = self._load_query_log_statements()
        if not rows:
            return []

        # Normalize queries (obfuscate SQL text)
        rows = self._normalize_queries(rows)

        if not rows:
            return []

        # Note: With checkpoint-based collection, we skip derivative calculation.
        # The exclusive time windows ensure each query is counted exactly once.
        # Metrics are the actual totals for the collection window.

        self._log.info(
            "Query metrics: collected %d rows for current window",
            len(rows),
        )

        self._check.gauge(
            'dd.clickhouse.queries.query_rows_raw',
            len(rows),
            tags=self.tags + self._check._get_debug_tags(),
            raw=True,
        )

        return rows

    def _normalize_queries(self, rows):
        """
        Normalize and obfuscate queries
        """
        normalized_rows = []
        for row in rows:
            normalized_row = dict(copy.copy(row))
            try:
                query_text = row['query']
                statement = obfuscate_sql_with_metadata(query_text, self._obfuscate_options)
            except Exception as e:
                self._log.debug("Failed to obfuscate query | err=[%s]", e)
                continue

            obfuscated_query = statement['query']
            normalized_row['query'] = obfuscated_query
            normalized_row['query_signature'] = compute_sql_signature(obfuscated_query)

            metadata = statement['metadata']
            # Keep ClickHouse native dd_tables if present (more accurate than obfuscator)
            # Only use obfuscator tables as fallback
            if not normalized_row.get('dd_tables'):
                normalized_row['dd_tables'] = metadata.get('tables', None)
            # Add commands and comments from obfuscator (ClickHouse doesn't have native columns for these)
            normalized_row['dd_commands'] = metadata.get('commands', None)
            normalized_row['dd_comments'] = metadata.get('comments', None)
            normalized_rows.append(normalized_row)

        return normalized_rows

    def _rows_to_fqt_events(self, rows):
        """
        Generate FQT (Full Query Text) events for each unique query signature
        These events provide the mapping from query_signature to actual SQL text
        dbm_type: fqt
        """
        for row in rows:
            query_cache_key = _row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue
            self._full_statement_text_cache[query_cache_key] = True

            db = row.get('databases', 'default')
            user = row.get('user', 'default')

            row_tags = self._tags_no_db + [
                "db:{}".format(db),
                "user:{}".format(user),
            ]

            yield {
                "timestamp": time.time() * 1000,
                "host": self._check.reported_hostname,
                "database_instance": self._check.database_identifier,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "clickhouse",
                "ddtags": ",".join(row_tags),
                "dbm_type": "fqt",
                "db": {
                    "instance": db,
                    "query_signature": row['query_signature'],
                    "statement": row['query'],
                    "metadata": {
                        "tables": row['dd_tables'],
                        "commands": row['dd_commands'],
                        "comments": row['dd_comments'],
                    },
                },
                "clickhouse": {
                    "user": user,
                    "normalized_query_hash": row.get('normalized_query_hash'),
                },
            }
