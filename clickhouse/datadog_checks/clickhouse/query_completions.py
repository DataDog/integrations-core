# (C) Datadog, Inc. 2026-present
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

from datadog_checks.base.utils.db.utils import RateLimitingTTLCache, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.clickhouse.query_log_job import ClickhouseQueryLogJob, agent_check_getter

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
  AND event_time_microseconds <= now64(6)
  AND event_date >= toDate(fromUnixTimestamp64Micro({last_checkpoint_microseconds}))
  AND type = 'QueryFinish'
  AND is_initial_query = 1
  AND query != ''
  AND normalized_query_hash != 0
  {internal_user_filter}
ORDER BY event_time_microseconds ASC
LIMIT {max_samples}
"""


class ClickhouseQueryCompletions(ClickhouseQueryLogJob):
    """Collects individual completed query samples from system.query_log"""

    # Persistent cache key for storing the last collection timestamp
    CHECKPOINT_CACHE_KEY = "query_completions_last_checkpoint_microseconds"

    def __init__(self, check: ClickhouseCheck, config):
        super().__init__(
            check=check,
            config=config,
            job_name="query-completions",
        )

        # Rate limiting: limit samples per query signature
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.seen_samples_cache_maxsize),
            ttl=60 * 60 / float(config.samples_per_hour_per_query),
        )

        # Maximum number of samples to collect per run
        self._max_samples_per_collection = int(config.max_samples_per_collection)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_submit(self):
        """
        Collect and submit completed query samples.

        Checkpoint is always advanced after collection to prefer dropped data over duplicates.
        """
        try:
            # Step 1: Collect rows (loads checkpoint internally)
            rows = self._collect_completed_queries()

            if not rows:
                # No new queries
                self._log.debug("No new completed queries")
                return

            # Step 2: Apply rate limiting and create payload
            payload = self._create_batched_payload(rows)

            if not payload or not payload.get('clickhouse_query_completions'):
                self._log.debug("No query completions after rate limiting")
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

            if self._current_checkpoint_microseconds:
                self._log.info(
                    "Successfully submitted. Checkpoint: %d microseconds", self._current_checkpoint_microseconds
                )

        except Exception:
            self._log.exception('Unable to collect completed query samples due to an error')
        finally:
            # Always advance checkpoint to avoid duplicates on retry.
            # Dropped payloads are preferable to duplicate samples which can skew analysis.
            self._advance_checkpoint()

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_completed_queries(self):
        """
        Load completed query samples using checkpoint-based collection.

        Flow:
            1. Load or initialize last checkpoint (only fetches from DB on first run)
            2. Execute query with now64(6) as upper bound
            3. Derive checkpoint from max(event_time_microseconds) in results
            4. Return results (checkpoint saved later on success)

        Optimization: Uses now64(6) directly in the query and derives the checkpoint from
        the results, reducing DB roundtrips from 2 to 1 for normal operation.

        For ClickHouse Cloud: Uses clusterAllReplicas('default', system.query_log) to query
        all nodes in the cluster.
        For self-hosted: Queries only the local node's query_log.
        """
        try:
            # Step 1: Get last checkpoint (only fetches from DB on first run)
            if self._last_checkpoint_microseconds is None:
                self._last_checkpoint_microseconds = self._get_last_checkpoint()

            # Get the appropriate table reference based on deployment type
            query_log_table = self._check.get_system_table('query_log')

            # Step 2: Build and execute query (uses now64(6) directly for upper bound)
            query = COMPLETED_QUERIES_QUERY.format(
                query_log_table=query_log_table,
                last_checkpoint_microseconds=self._last_checkpoint_microseconds,
                internal_user_filter=self._get_internal_user_filter(),
                max_samples=self._max_samples_per_collection,
            )
            rows = self._execute_query(query)

            self._log.info(
                "Loaded %d completed queries from %s [%s] (last_checkpoint=%d)",
                len(rows),
                query_log_table,
                self.deployment_mode,
                self._last_checkpoint_microseconds,
            )

            # Track the max event time across all rows for checkpoint
            # Since results are ordered ASC by event_time, the last row has the max
            max_event_time = 0

            # Step 3: Convert to list of dicts and obfuscate
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

                # Track max event time for checkpoint
                event_time_int = self.to_microseconds(event_time_microseconds)
                if event_time_int > max_event_time:
                    max_event_time = event_time_int

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
                    'query_start_time_microseconds': self.to_microseconds(query_start_time_microseconds),
                    'event_time_microseconds': event_time_int,
                    'query_id': str(query_id) if query_id else '',
                    'initial_query_id': str(initial_query_id) if initial_query_id else '',
                    'query_kind': str(query_kind) if query_kind else '',
                    'is_initial_query': bool(is_initial_query) if is_initial_query is not None else True,
                }

                # Obfuscate the query
                obfuscated_row = self._normalize_query(row_dict)
                if obfuscated_row:
                    result_rows.append(obfuscated_row)

            # Step 4: Set checkpoint from results, or fetch current time if no rows (idle period)
            self._set_checkpoint_from_event_time(max_event_time)

            return result_rows

        except Exception as e:
            self._log.exception("Failed to load completed queries from system.query_log: %s", e)

            self._check.count(
                "dd.clickhouse.query_completions.error",
                1,
                tags=self.tags + ["error:query_log_load_failed"],
                raw=True,
            )

            # Re-raise to let outer handler log the error.
            # Checkpoint will still advance to avoid duplicates on retry.
            raise

    def _normalize_query(self, row):
        """
        Normalize and obfuscate a single query row
        """
        obfuscation_result = self._obfuscate_query(row['query'])
        if obfuscation_result is None:
            return None

        row['statement'] = obfuscation_result['query']
        row['query_signature'] = obfuscation_result['query_signature']
        row['dd_tables'] = obfuscation_result['dd_tables']
        row['dd_commands'] = obfuscation_result['dd_commands']
        row['dd_comments'] = obfuscation_result['dd_comments']

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
            'clickhouse_version': self._check.dbms_version,
            'service': getattr(self._check, 'service', None),
            'clickhouse_query_completions': query_completions,
        }

        return payload
