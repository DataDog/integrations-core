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

# Query to fetch failed queries from system.query_log.
# Collects ExceptionBeforeStart (type=3) and ExceptionWhileProcessing (type=4) events.
# Includes exception, exception_code, and stack_trace fields in addition to the standard query fields.
QUERY_ERRORS_QUERY = """
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
    query_start_time_microseconds,
    event_time_microseconds,
    query_id,
    initial_query_id,
    query_kind,
    is_initial_query,
    exception,
    exception_code,
    stack_trace,
    current_database,
    address
FROM {query_log_table}
WHERE
  {checkpoint_filter}
  AND event_time_microseconds <= now64(6)
  AND event_date >= toDate(fromUnixTimestamp64Micro({min_checkpoint_us:UInt64}))
  AND type IN ('ExceptionBeforeStart', 'ExceptionWhileProcessing')
  AND is_initial_query = 1
  AND query != ''
  AND normalized_query_hash != 0
  {internal_user_filter}
ORDER BY event_time_microseconds ASC
LIMIT {max_samples:UInt64}
"""


class ClickhouseQueryErrors(ClickhouseQueryLogJob):
    """Collects failed query samples from system.query_log"""

    CHECKPOINT_CACHE_KEY = "query_errors_last_checkpoint_microseconds"

    def __init__(self, check: ClickhouseCheck, config):
        super().__init__(
            check=check,
            config=config,
            job_name="query-errors",
        )

        self._seen_samples_ratelimiter = RateLimitingTTLCache(
            maxsize=int(config.seen_samples_cache_maxsize),
            ttl=60 * 60 / float(config.samples_per_hour_per_query),
        )

        self._max_samples_per_collection = int(config.max_samples_per_collection)

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_and_submit(self):
        """
        Collect and submit failed query samples.

        Checkpoint is always advanced after collection to prefer dropped data over duplicates.
        """
        try:
            self._current_checkpoint_microseconds = None
            self._pending_node_checkpoints = {}

            rows = self._collect_query_errors()

            if not rows:
                self._log.debug("No new query errors")
                return

            payload = self._create_batched_payload(rows)

            if not payload or not payload.get('clickhouse_query_errors'):
                self._log.debug("No query errors after rate limiting")
                return

            payload_data = json.dumps(payload, default=default_json_event_encoding)
            num_errors = len(payload.get('clickhouse_query_errors', []))
            self._log.debug(
                "Submitting query errors payload: %d bytes, %d errors",
                len(payload_data),
                num_errors,
            )
            self._check.database_monitoring_query_activity(payload_data)

            if self._current_checkpoint_microseconds is not None:
                self._log.debug(
                    "Successfully submitted. Checkpoint: %d microseconds", self._current_checkpoint_microseconds
                )

        except Exception:
            self._log.exception('Unable to collect query error samples due to an error')
        finally:
            self._advance_checkpoint()

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_query_errors(self):
        """Load failed query samples using checkpoint-based collection."""
        try:
            query_log_table = self._check.get_system_table('query_log')
            checkpoint_filter, min_checkpoint, params = self._build_per_node_checkpoint_filter()

            query = (
                QUERY_ERRORS_QUERY.replace("{query_log_table}", query_log_table)
                .replace("{checkpoint_filter}", checkpoint_filter)
                .replace("{internal_user_filter}", self._get_internal_user_filter())
            )
            params["min_checkpoint_us"] = min_checkpoint
            params["max_samples"] = self._max_samples_per_collection

            rows = self._execute_query(query, parameters=params)

            self._log.debug(
                "Loaded %d query errors from %s [%s]",
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
                    query_start_time_microseconds,
                    event_time_microseconds,
                    query_id,
                    initial_query_id,
                    query_kind,
                    is_initial_query,
                    exception,
                    exception_code,
                    stack_trace,
                    current_database,
                    address,
                ) = row

                event_time_int = self.to_microseconds(event_time_microseconds)
                if event_time_int > max_event_time:
                    max_event_time = event_time_int

                if server_node:
                    self._track_node_checkpoint(str(server_node), event_time_int)

                row_dict = {
                    'normalized_query_hash': str(normalized_query_hash),
                    'query': str(query_text) if query_text else '',
                    'user': str(user) if user else '',
                    'query_type': str(query_type) if query_type else '',
                    # For ExceptionBeforeStart errors, `databases` is empty because the query
                    # failed before table resolution. Fall back to `current_database` (the
                    # connection's default database) so the field is always populated.
                    'databases': (
                        str(databases[0]) if databases else (str(current_database) if current_database else '')
                    ),
                    'tables': [str(t) for t in tables] if tables else [],
                    'query_duration_ms': float(query_duration_ms) if query_duration_ms else 0.0,
                    'read_rows': int(read_rows) if read_rows else 0,
                    'read_bytes': int(read_bytes) if read_bytes else 0,
                    'written_rows': int(written_rows) if written_rows else 0,
                    'written_bytes': int(written_bytes) if written_bytes else 0,
                    'result_rows': int(result_rows_count) if result_rows_count else 0,
                    'result_bytes': int(result_bytes) if result_bytes else 0,
                    'memory_usage': int(memory_usage) if memory_usage else 0,
                    'query_start_time_microseconds': self.to_microseconds(query_start_time_microseconds),
                    'event_time_microseconds': event_time_int,
                    'query_id': str(query_id) if query_id else '',
                    'initial_query_id': str(initial_query_id) if initial_query_id else '',
                    'query_kind': str(query_kind) if query_kind else '',
                    'is_initial_query': bool(is_initial_query) if is_initial_query is not None else True,
                    'exception': str(exception) if exception else '',
                    'exception_code': int(exception_code) if exception_code else 0,
                    'stack_trace': str(stack_trace) if stack_trace else '',
                    'client_ip': str(address) if address else '',
                }

                obfuscated_row = self._normalize_query(row_dict)
                if obfuscated_row:
                    result_rows.append(obfuscated_row)

            self._set_checkpoint_from_event_time(max_event_time)

            return result_rows

        except Exception as e:
            self._log.exception("Failed to load query errors from %s: %s", query_log_table, e)

            self._check.count(
                "dd.clickhouse.query_errors.error",
                1,
                tags=self.tags + ["error:query_log_load_failed"],
                raw=True,
            )

            raise

    def _normalize_query(self, row: dict) -> dict | None:
        """Normalize and obfuscate a single query error row."""
        obfuscation_result = self._obfuscate_query(row['query'])
        if obfuscation_result is None:
            return None

        row['statement'] = obfuscation_result['query']
        row['query_signature'] = obfuscation_result['query_signature']
        row['dd_tables'] = obfuscation_result['dd_tables']
        row['dd_commands'] = obfuscation_result['dd_commands']
        row['dd_comments'] = obfuscation_result['dd_comments']

        return row

    def _create_batched_payload(self, rows: list) -> dict | None:
        """Create a batched payload with rate limiting applied."""
        query_errors = []

        for row in rows:
            query_signature = row.get('query_signature')
            if not query_signature:
                continue

            if not self._seen_samples_ratelimiter.acquire(query_signature):
                continue

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
                'query_start_time_microseconds': row.get('query_start_time_microseconds', 0),
                'event_time_microseconds': row.get('event_time_microseconds', 0),
                'initial_query_id': row.get('initial_query_id', ''),
                'is_initial_query': row.get('is_initial_query', True),
                'exception': row.get('exception', ''),
                'exception_code': row.get('exception_code', 0),
                'stack_trace': row.get('stack_trace', ''),
                'client_ip': row.get('client_ip', ''),
                'metadata': {
                    'tables': row.get('dd_tables'),
                    'commands': row.get('dd_commands'),
                    'comments': row.get('dd_comments'),
                },
            }

            query_errors.append({'query_details': query_details})

        if not query_errors:
            return None

        payload = {
            'host': self._check.reported_hostname,
            'database_instance': self._check.database_identifier,
            'ddagentversion': datadog_agent.get_version(),
            'ddsource': 'clickhouse',
            'dbm_type': 'query_error',
            'collection_interval': self._collection_interval,
            'ddtags': self._tags_no_db,
            'timestamp': time.time() * 1000,
            'clickhouse_version': self._check.dbms_version,
            'service': getattr(self._check, 'service', None),
            'clickhouse_query_errors': query_errors,
        }

        return payload
