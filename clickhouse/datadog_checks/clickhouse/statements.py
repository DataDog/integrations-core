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

from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.clickhouse.query_log_job import ClickhouseQueryLogJob, agent_check_getter

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
    AND event_time_microseconds <= now64(6)
    -- Partition pruning: event_date filter allows ClickHouse to skip entire daily partitions
    AND event_date >= toDate(fromUnixTimestamp64Micro({last_checkpoint_microseconds}))
    AND type != 'QueryStart'
    AND is_initial_query = 1
    AND query != ''
    AND normalized_query_hash != 0
    {internal_user_filter}
GROUP BY normalized_query_hash
ORDER BY total_duration_ms DESC  -- Prioritize queries with highest system impact
"""


def _row_key(row):
    """
    :param row: a normalized row from system.query_log
    :return: a tuple uniquely identifying this row
    """
    return row['query_signature'], row.get('user', ''), row.get('databases', '')


class ClickhouseStatementMetrics(ClickhouseQueryLogJob):
    """
    Collects telemetry for SQL statements from system.query_log using checkpoint-based collection.

    Checkpoint-based collection ensures:
    - No queries are missed due to collection delays
    - No queries are double-counted
    - Microsecond precision for high-throughput environments
    - State survives agent restarts via persistent cache
    """

    # Persistent cache key for storing the last collection checkpoint
    CHECKPOINT_CACHE_KEY = "query_metrics_last_checkpoint_microseconds"

    def __init__(self, check: ClickhouseCheck, config):
        super().__init__(
            check=check,
            config=config,
            job_name="query-metrics",
        )

        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=int(config.full_statement_text_cache_max_size),
            ttl=60 * 60 / float(config.full_statement_text_samples_per_hour_per_query),
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_submit(self):
        """
        Collect per-statement metrics from system.query_log and emit as:
        1. FQT events (dbm_type: fqt) - for query text catalog
        2. Query metrics payload - for time-series metrics

        Uses checkpoint-based collection to ensure no queries are double-counted.
        Checkpoint is always advanced after collection to prefer dropped data over duplicates.
        """
        try:
            # Reset pending checkpoint at the start of each collection
            self._current_checkpoint_microseconds = None

            rows = self._collect_metrics_rows()
            if not rows:
                # Even if no rows, save the checkpoint to advance the window
                # This prevents re-querying the same empty window repeatedly
                self._advance_checkpoint()
                return

            # Emit FQT (Full Query Text) events
            for event in self._rows_to_fqt_events(rows):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

            # Prepare metrics payload wrapper
            payload_wrapper = {
                'host': self._check.reported_hostname,
                'database_instance': self._check.database_identifier,
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._collection_interval,
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

            if self._current_checkpoint_microseconds:
                self._log.info("Collection complete. Checkpoint saved: %d", self._current_checkpoint_microseconds)

        except Exception:
            self._log.exception('Unable to collect statement metrics due to an error')
        finally:
            # Always advance checkpoint to avoid duplicates on retry.
            # Dropped payloads are preferable to duplicate metrics which can skew aggregations.
            self._advance_checkpoint()

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

        Optimization: Uses now64(6) directly in the query and derives the checkpoint from
        max(event_time_microseconds) in the results, reducing DB roundtrips from 2 to 1.
        """
        try:
            # Get the last checkpoint (only fetches from DB on first run)
            if self._last_checkpoint_microseconds is None:
                self._last_checkpoint_microseconds = self._get_last_checkpoint()

            # Get the appropriate table reference based on deployment type
            # For Cloud: clusterAllReplicas('default', system.query_log)
            # For self-hosted: system.query_log
            query_log_table = self._check.get_system_table('query_log')

            query = STATEMENTS_QUERY.format(
                query_log_table=query_log_table,
                last_checkpoint_microseconds=self._last_checkpoint_microseconds,
                internal_user_filter=self._get_internal_user_filter(),
            )
            rows = self._execute_query(query)

            self._log.info(
                "Loaded %d rows from %s [%s] (last_checkpoint=%d)",
                len(rows),
                query_log_table,
                self.deployment_mode,
                self._last_checkpoint_microseconds,
            )

            # Track the global max event time across all rows for checkpoint
            global_max_event_time = 0

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
                    max_event_time_microseconds,  # Per-group max, used to derive global checkpoint
                ) = row

                # Track global max for checkpoint
                event_time_int = self.to_microseconds(max_event_time_microseconds)
                if event_time_int > global_max_event_time:
                    global_max_event_time = event_time_int

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

            # Set checkpoint from results, or fetch current time if no rows (idle period)
            self._set_checkpoint_from_event_time(global_max_event_time)

            return result_rows

        except Exception as e:
            self._log.exception("Failed to load statements from system.query_log: %s", e)
            self._check.count(
                "dd.clickhouse.statement_metrics.error",
                1,
                tags=self.tags + ["error:query_log_load_failed"],
                raw=True,
            )
            # Re-raise to let outer handler log the error.
            # Checkpoint will still advance to avoid duplicates on retry.
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
            obfuscation_result = self._obfuscate_query(row['query'])
            if obfuscation_result is None:
                continue

            normalized_row['query'] = obfuscation_result['query']
            normalized_row['query_signature'] = obfuscation_result['query_signature']

            # Keep ClickHouse native dd_tables if present (more accurate than obfuscator)
            # Only use obfuscator tables as fallback
            if not normalized_row.get('dd_tables'):
                normalized_row['dd_tables'] = obfuscation_result['dd_tables']
            # Add commands and comments from obfuscator (ClickHouse doesn't have native columns for these)
            normalized_row['dd_commands'] = obfuscation_result['dd_commands']
            normalized_row['dd_comments'] = obfuscation_result['dd_comments']
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
