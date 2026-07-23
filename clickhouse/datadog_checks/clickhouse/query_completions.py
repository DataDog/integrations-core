# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck
    from datadog_checks.clickhouse.config_models.instance import AsyncInsertFlushes

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.utils import RateLimitingTTLCache, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.clickhouse.explain_plans import ClickhouseExplainPlans
from datadog_checks.clickhouse.query_log_job import (
    ClickhouseQueryLogJob,
    NodeCheckpoint,
    agent_check_getter,
    collection_interval_gcd,
)

# Query to fetch individual completed queries from system.query_log.
# Unlike statements.py which aggregates, this returns individual query executions.
#
# Always includes hostName() as server_node for per-node checkpoint tracking.
# For single-node deployments this is a single constant value; for multi-node
# Cloud clusters it enables each node's checkpoint to advance independently.
COMPLETED_QUERIES_QUERY = """
SELECT
    normalized_query_hash,
    hostName() as server_node,
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
    ProfileEvents['OSCPUVirtualTimeMicroseconds'] as cpu_us,
    ProfileEvents['OSCPUWaitMicroseconds'] as cpu_wait_us,
    query_start_time_microseconds,
    event_time_microseconds,
    query_id,
    initial_query_id,
    query_kind,
    is_initial_query
FROM {query_log_table}
WHERE
  {checkpoint_filter}
  AND event_time_microseconds <= now64(6)
  AND event_date >= toDate(fromUnixTimestamp64Micro({min_checkpoint_us:UInt64}))
  AND type = 'QueryFinish'
  AND is_initial_query = 1
  AND query != ''
  AND normalized_query_hash != 0
  {internal_user_filter}
ORDER BY event_time_microseconds ASC
LIMIT {max_samples:UInt64}
"""

# Query to fetch flush records from system.asynchronous_insert_log.
FLUSH_LOG_QUERY = """
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
    AND event_date >= toDate(fromUnixTimestamp64Micro({min_checkpoint_us:UInt64}))
ORDER BY event_time_microseconds ASC
LIMIT {max_flush_rows:UInt64}
"""

DBM_TYPE_FLUSH = "async_inserts_flush"
FLUSH_CHECKPOINT_CACHE_KEY = "async_insert_flush_log_last_checkpoint_microseconds"


class ClickhouseQueryCompletions(ClickhouseQueryLogJob):
    """Collects individual completed query samples from system.query_log"""

    # Persistent cache key for storing the last collection timestamp
    CHECKPOINT_CACHE_KEY = "query_completions_last_checkpoint_microseconds"

    def __init__(self, check: ClickhouseCheck, config, flush_config: AsyncInsertFlushes):
        # The shared job loop ticks at the GCD of the enabled sub-schedules' intervals, so each one
        # fires on time instead of being floored by (or stalled behind) the other's interval.
        enabled_intervals = []
        if config.enabled:
            enabled_intervals.append(config.collection_interval)
        if flush_config.enabled:
            enabled_intervals.append(flush_config.collection_interval)
        loop_collection_interval = (
            collection_interval_gcd(*enabled_intervals) if enabled_intervals else config.collection_interval
        )
        super().__init__(
            check=check,
            config=config,
            job_name="query-completions",
            # Run the shared job when either collection is enabled, so flush logs are still
            # collected when query completions is disabled.
            enabled=config.enabled or flush_config.enabled,
            collection_interval=loop_collection_interval,
        )

        # Rate limiting: limit samples per query signature
        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.seen_samples_cache_maxsize),
            ttl=60 * 60 / float(config.samples_per_hour_per_query),
        )

        # Maximum number of samples to collect per run
        self._max_samples_per_collection = int(config.max_samples_per_collection)

        self._explain_plans = ClickhouseExplainPlans(check, config, self._execute_query)

        # Last collection time for completions
        self._last_completions_collection_time = 0.0

        # Async insert flush log collection collapses into this job. It keeps its own independent
        # checkpoint (separate from the query_log completions checkpoint) and runs on its own interval.
        self._flush_enabled = flush_config.enabled
        self._flush_collection_interval = flush_config.collection_interval
        self._flush_max_rows = int(flush_config.max_samples_per_collection)
        self._flush_checkpoint = NodeCheckpoint(self, FLUSH_CHECKPOINT_CACHE_KEY, self._flush_collection_interval)
        self._last_flush_collection_time = 0.0

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_submit(self):
        """
        Collect and submit completed query samples.

        Checkpoint is always advanced after collection to prefer dropped data over duplicates.
        """
        # The shared job may be running only for the async insert flush log, so skip
        # completed-query collection when query completions is disabled.
        if not self._config.enabled:
            return
        now = time.time()
        if now - self._last_completions_collection_time < self._collection_interval:
            return
        self._last_completions_collection_time = now
        try:
            # Reset pending checkpoints at the start of each collection
            self._current_checkpoint_microseconds = None
            self._pending_node_checkpoints = {}

            # Step 1: Collect rows (loads checkpoint internally)
            rows = self._collect_completed_queries()

            if not rows:
                # No new queries
                self._log.debug("No new completed queries")
                return

            # Step 2: Collect and submit explain plans (independent of completion rate limiting)
            try:
                for plan_event in self._explain_plans._collect_plans(rows, self._tags_no_db or []):
                    plan_data = json.dumps(plan_event, default=default_json_event_encoding)
                    self._check.database_monitoring_query_sample(plan_data)
            except Exception:
                self._log.exception("Failed to collect explain plans")

            # Step 3: Apply rate limiting and create payload
            payload = self._create_batched_payload(rows)

            if not payload or not payload.get('clickhouse_query_completions'):
                self._log.debug("No query completions after rate limiting")
                return

            # Step 4: Submit payload
            payload_data = json.dumps(payload, default=default_json_event_encoding)
            num_completions = len(payload.get('clickhouse_query_completions', []))
            self._log.debug(
                "Submitting query completions payload: %d bytes, %d completions",
                len(payload_data),
                num_completions,
            )
            self._check.database_monitoring_query_activity(payload_data)

            if self._current_checkpoint_microseconds is not None:
                self._log.debug(
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
            1. Build per-node checkpoint filter (falls back to global on first run)
            2. Execute query with now64(6) as upper bound
            3. Derive checkpoint from max(event_time_microseconds) in results
            4. Return results (checkpoint saved later on success)

        Optimization: Uses now64(6) directly in the query and derives the checkpoint from
        the results, reducing DB roundtrips from 2 to 1 for normal operation.
        """
        try:
            query_log_table = self._check.get_system_table('query_log')
            checkpoint_filter, min_checkpoint, params = self._build_per_node_checkpoint_filter()

            query = (
                COMPLETED_QUERIES_QUERY.replace("{query_log_table}", query_log_table)
                .replace("{checkpoint_filter}", checkpoint_filter)
                .replace("{internal_user_filter}", self._get_internal_user_filter())
            )
            params["min_checkpoint_us"] = min_checkpoint
            params["max_samples"] = self._max_samples_per_collection

            rows = self._execute_query(query, parameters=params)

            self._log.debug(
                "Loaded %d completed queries from %s [%s]",
                len(rows),
                query_log_table,
                self.deployment_mode,
            )

            max_event_time = 0

            result_rows = []
            for row in rows:
                (
                    normalized_query_hash,
                    server_node,
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
                    cpu_us,
                    cpu_wait_us,
                    query_start_time_microseconds,
                    event_time_microseconds,
                    query_id,
                    initial_query_id,
                    query_kind,
                    is_initial_query,
                ) = row

                event_time_int = self.to_microseconds(event_time_microseconds)
                if event_time_int > max_event_time:
                    max_event_time = event_time_int

                if server_node:
                    self._track_node_checkpoint(str(server_node), event_time_int)

                row_dict = {
                    'normalized_query_hash': str(normalized_query_hash),
                    'hostname': str(server_node) if server_node else '',
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
                    'cpu_us': int(cpu_us) if cpu_us else 0,
                    'cpu_wait_us': int(cpu_wait_us) if cpu_wait_us else 0,
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
            self._log.warning("Failed to load completed queries from system.query_log: %s", e)

            self._check.count(
                "dd.clickhouse.query_completions.error",
                1,
                tags=self.tags + ["error:query_log_load_failed"],
                raw=True,
            )

            # Re-raise to let outer handler log the error.
            # Checkpoint will still advance to avoid duplicates on retry.
            raise

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
                'cpu_us': row.get('cpu_us', 0),
                'cpu_wait_us': row.get('cpu_wait_us', 0),
                'query_start_time_microseconds': row.get('query_start_time_microseconds', 0),
                'event_time_microseconds': row.get('event_time_microseconds', 0),
                'initial_query_id': row.get('initial_query_id', ''),
                'is_initial_query': row.get('is_initial_query', True),
                'hostname': row.get('hostname', ''),
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

    def run_job(self):
        """
        Run completed-query collection (base behavior), then the async insert flush log collection.
        """
        super().run_job()
        try:
            self._collect_flush()
        except Exception:
            self._log.exception("Failed to collect async insert flush log")
            self._flush_error_count("collect-flush-log")

    def _collect_flush(self):
        """
        Run the async insert flush log collection on its own collection interval
        """
        now = time.time()
        if self._flush_enabled and now - self._last_flush_collection_time >= self._flush_collection_interval:
            self._last_flush_collection_time = now
            self._collect_and_submit_flush()

    def _collect_and_submit_flush(self):
        """
        Collect flush records since the flush checkpoint and submit them as DBM events.

        Unlike query completions (which always advances to prefer dropped data over duplicates),
        the flush checkpoint is advanced only on success, so a failed query or submission retries
        the same window rather than losing flush data.
        """
        self._flush_checkpoint.reset_pending()

        try:
            records = self._collect_flush_rows()
        except Exception:
            self._log.exception("Failed to load async insert flush log")
            self._flush_error_count("load-flush-log")
            return  # do not advance checkpoint; retry this window next time

        if not records:
            # Idle window: advance so we don't rescan the same empty range indefinitely.
            self._flush_checkpoint.advance_checkpoint()
            return

        event = self._create_flush_event(records)
        try:
            self._check.database_monitoring_query_activity(json.dumps(event, default=default_json_event_encoding))
        except Exception:
            self._log.exception("Failed to submit async insert flush payload")
            self._flush_error_count("submit-flush-log")
            return  # do not advance checkpoint; retry this window next time

        self._flush_checkpoint.advance_checkpoint()
        self._log.debug("Submitted %d async insert flush records", len(records))

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_flush_rows(self):
        """Load new flush records from system.asynchronous_insert_log using the flush checkpoint."""
        async_insert_log_table = self._check.get_system_table('asynchronous_insert_log')
        checkpoint_filter, min_checkpoint, params = self._flush_checkpoint.build_per_node_checkpoint_filter()

        query = FLUSH_LOG_QUERY.replace("{async_insert_log_table}", async_insert_log_table).replace(
            "{checkpoint_filter}", checkpoint_filter
        )
        params["min_checkpoint_us"] = min_checkpoint
        params["max_flush_rows"] = self._flush_max_rows

        rows = self._execute_query(query, parameters=params)
        self._log.debug("Loaded %d async insert flush rows [%s]", len(rows), self.deployment_mode)

        max_event_time = 0
        records = []
        for row in rows:
            (
                database,
                table,
                format_,
                status,
                exception,
                server_node,
                bytes_,
                rows_,
                query_id,
                query_text,
                event_time_microseconds,
                flush_time_microseconds,
            ) = row

            event_time_int = self.to_microseconds(event_time_microseconds)
            flush_time_int = self.to_microseconds(flush_time_microseconds)
            flush_latency_us = max(0, flush_time_int - event_time_int) if event_time_int and flush_time_int else 0

            if event_time_int > max_event_time:
                max_event_time = event_time_int
            if server_node:
                self._flush_checkpoint.track_node_checkpoint(str(server_node), event_time_int)

            obfuscated = self._obfuscate_query(str(query_text)) if query_text else None
            records.append(
                {
                    'database': str(database) if database else '',
                    'table': str(table) if table else '',
                    'format': str(format_) if format_ else '',
                    'status': str(status) if status else '',
                    'exception': str(exception) if exception else '',
                    'server_node': str(server_node) if server_node else '',
                    'bytes': int(bytes_) if bytes_ else 0,
                    'rows': int(rows_) if rows_ else 0,
                    'query_id': str(query_id) if query_id else '',
                    'query': obfuscated['query'] if obfuscated else None,
                    'query_signature': obfuscated['query_signature'] if obfuscated else None,
                    'event_time_microseconds': event_time_int,
                    'flush_time_microseconds': flush_time_int,
                    'flush_latency_us': flush_latency_us,
                }
            )

        # Advance-eligible checkpoint from the max event time seen (or DB time if no rows).
        self._flush_checkpoint.set_checkpoint_from_event_time(max_event_time)
        return records

    def _create_flush_event(self, records):
        """Create a database monitoring flush record event payload."""
        return {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': datadog_agent.get_version(),
            'ddsource': 'clickhouse',
            'dbm_type': DBM_TYPE_FLUSH,
            'collection_interval': self._flush_collection_interval,
            'ddtags': self._tags_no_db,
            'timestamp': time.time() * 1000,
            'clickhouse_version': self._check.dbms_version,
            'service': getattr(self._check._config, 'service', None),
            'clickhouse_async_insert_flushes': records,
        }

    def _flush_error_count(self, error_label):
        self._check.count(
            "dd.clickhouse.async_inserts_flush.error",
            1,
            tags=(self.tags or []) + [f"error:{error_label}"],
            raw=True,
        )
