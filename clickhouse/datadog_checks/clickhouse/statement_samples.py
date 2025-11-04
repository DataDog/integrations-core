# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

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
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# Query to get recent queries from system.query_log
# We collect queries that have finished execution and have sufficient information
QUERY_LOG_QUERY = """
SELECT
    event_time,
    query_id,
    query,
    type,
    user,
    query_duration_ms,
    read_rows,
    read_bytes,
    written_rows,
    written_bytes,
    result_rows,
    result_bytes,
    memory_usage,
    exception
FROM system.query_log
WHERE
    type IN ('QueryFinish', 'ExceptionWhileProcessing')
    AND event_time >= toDateTime('{start_time}')
    AND event_time < toDateTime('{end_time}')
    AND query NOT LIKE '%system.query_log%'
    AND query NOT LIKE '%system.processes%'
ORDER BY event_time DESC
LIMIT {limit}
"""

# Query to get active queries from system.processes
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
    initial_query_id
FROM system.processes
WHERE query NOT LIKE '%%system.processes%%'
"""


def agent_check_getter(self):
    return self._check


class ClickhouseStatementSamples(DBMAsyncJob):
    """
    Collects statement samples from ClickHouse query logs.
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
        self._last_collection_timestamp = None

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

        # Cache for storing query execution plans
        self._explain_plan_cache = TTLCache(
            maxsize=1000,
            ttl=3600,  # 1 hour TTL
        )

        self._collection_interval = collection_interval

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

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_query_log_samples(self):
        """
        Fetch recent queries from system.query_log
        """
        start_time = time.time()

        # Calculate time window for query collection
        end_time_ts = time.time()
        if self._last_collection_timestamp is None:
            # First run: collect queries from the last collection interval
            start_time_ts = end_time_ts - self._collection_interval
        else:
            start_time_ts = self._last_collection_timestamp

        # Convert to datetime strings for ClickHouse
        from datetime import datetime

        start_time_dt = datetime.fromtimestamp(start_time_ts)
        end_time_dt = datetime.fromtimestamp(end_time_ts)

        params = {
            'start_time': start_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_time_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'limit': 100,
        }

        try:
            # Execute query using the check's client
            query = QUERY_LOG_QUERY.format(**params)
            self._log.debug("Executing query log query: %s", query)
            rows = self._check.execute_query_raw(query)

            self._last_collection_timestamp = end_time_ts

            self._report_check_hist_metrics(start_time, len(rows), "get_query_log_samples")
            self._log.info("Loaded %s rows from system.query_log", len(rows))

            return rows
        except Exception as e:
            self._log.exception("Failed to collect query log samples: %s", str(e))
            self._check.count(
                "dd.clickhouse.statement_samples.error",
                1,
                tags=self.tags + ["error:query-log-fetch"] + self._get_debug_tags(),
                raw=True,
            )
            return []

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _get_active_queries(self):
        """
        Fetch currently running queries from system.processes
        """
        start_time = time.time()

        try:
            rows = self._check.execute_query_raw(ACTIVE_QUERIES_QUERY)

            self._report_check_hist_metrics(start_time, len(rows), "get_active_queries")
            self._log.debug("Loaded %s rows from system.processes", len(rows))

            return rows
        except Exception as e:
            self._log.warning("Failed to collect active queries: %s", str(e))
            return []

    def _normalize_query_log_row(self, row):
        """
        Normalize a row from system.query_log into a standard format
        """
        try:
            (
                event_time,
                query_id,
                query,
                query_type,
                user,
                query_duration_ms,
                read_rows,
                read_bytes,
                written_rows,
                written_bytes,
                result_rows,
                result_bytes,
                memory_usage,
                exception,
            ) = row

            normalized_row = {
                'timestamp': event_time,
                'query_id': str(query_id),
                'query': str(query),
                'type': str(query_type),
                'user': str(user),
                'duration_ms': float(query_duration_ms) if query_duration_ms else 0,
                'read_rows': int(read_rows) if read_rows else 0,
                'read_bytes': int(read_bytes) if read_bytes else 0,
                'written_rows': int(written_rows) if written_rows else 0,
                'written_bytes': int(written_bytes) if written_bytes else 0,
                'result_rows': int(result_rows) if result_rows else 0,
                'result_bytes': int(result_bytes) if result_bytes else 0,
                'memory_usage': int(memory_usage) if memory_usage else 0,
                'exception': str(exception) if exception else None,
            }

            return self._obfuscate_and_normalize_query(normalized_row)
        except Exception as e:
            self._log.warning("Failed to normalize query log row: %s, row: %s", str(e), row)
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
            row['query_signature'] = compute_sql_signature(obfuscated_query)
            row['dd_tables'] = metadata.get('tables', None)
            row['dd_commands'] = metadata.get('commands', None)
            row['dd_comments'] = metadata.get('comments', None)
        except Exception as e:
            self._log.debug("Failed to obfuscate query: %s", e)
            self._check.count(
                "dd.clickhouse.statement_samples.error",
                1,
                tags=self.tags + ["error:sql-obfuscate"] + self._check._get_debug_tags(),
                raw=True,
            )
            # Use a default query signature if obfuscation fails
            row['query_signature'] = compute_sql_signature(row['query'][:100])

        row['statement'] = obfuscated_query
        return row

    def _get_debug_tags(self):
        return self._check._get_debug_tags() if hasattr(self._check, '_get_debug_tags') else []

    def _report_check_hist_metrics(self, start_time, row_len, method_name):
        """
        Report histogram metrics for check operations
        """
        elapsed_ms = (time.time() - start_time) * 1000
        self._check.histogram(
            f"dd.clickhouse.{method_name}.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._check.histogram(
            f"dd.clickhouse.{method_name}.rows",
            row_len,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _collect_statement_samples(self):
        """
        Main method to collect and submit statement samples
        """
        start_time = time.time()

        # Get query log samples
        rows = self._get_query_log_samples()

        self._log.info("Retrieved %s query log samples for processing", len(rows))

        submitted_count = 0
        skipped_count = 0
        error_count = 0

        for row in rows:
            try:
                normalized_row = self._normalize_query_log_row(row)

                # Check if we should submit this sample based on rate limiting
                query_signature = normalized_row.get('query_signature')
                if not query_signature:
                    self._log.debug("Skipping row without query signature")
                    skipped_count += 1
                    continue

                if not self._seen_samples_ratelimiter.acquire(query_signature):
                    skipped_count += 1
                    continue

                # Create the event payload
                event = self._create_sample_event(normalized_row)

                # Submit the event
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))
                submitted_count += 1
                self._log.debug("Submitted query sample for signature: %s", query_signature[:50])

            except Exception as e:
                error_count += 1
                self._log.exception("Error processing query log row: %s", e)
                self._check.count(
                    "dd.clickhouse.statement_samples.error",
                    1,
                    tags=self.tags + ["error:process-row"] + self._get_debug_tags(),
                    raw=True,
                )

        elapsed_ms = (time.time() - start_time) * 1000

        self._log.info(
            "Statement sample collection complete: submitted=%s, skipped=%s, errors=%s, elapsed_ms=%.2f",
            submitted_count, skipped_count, error_count, elapsed_ms
        )

        self._check.histogram(
            "dd.clickhouse.collect_statement_samples.time",
            elapsed_ms,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._check.count(
            "dd.clickhouse.collect_statement_samples.events_submitted.count",
            submitted_count,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._check.count(
            "dd.clickhouse.collect_statement_samples.events_skipped.count",
            skipped_count,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._check.count(
            "dd.clickhouse.collect_statement_samples.events_errors.count",
            error_count,
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )
        self._check.gauge(
            "dd.clickhouse.collect_statement_samples.seen_samples_cache.len",
            len(self._seen_samples_ratelimiter),
            tags=self.tags + self._get_debug_tags(),
            raw=True,
        )

    def _create_sample_event(self, row):
        """
        Create a database monitoring query sample event
        """
        db = self._check._db

        event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "clickhouse",
            "dbm_type": "sample",
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
            "clickhouse": {
                "query_id": row.get('query_id'),
                "type": row.get('type'),
                "duration_ms": row.get('duration_ms'),
                "read_rows": row.get('read_rows'),
                "read_bytes": row.get('read_bytes'),
                "written_rows": row.get('written_rows'),
                "written_bytes": row.get('written_bytes'),
                "result_rows": row.get('result_rows'),
                "result_bytes": row.get('result_bytes'),
                "memory_usage": row.get('memory_usage'),
            },
        }

        # Add exception information if present
        if row.get('exception'):
            event['clickhouse']['exception'] = row['exception']

        # Add duration if available
        if row.get('duration_ms'):
            event['duration'] = int(row['duration_ms'] * 1e6)  # Convert to nanoseconds

        return event

    def run_job(self):
        """
        Main job execution method called by DBMAsyncJob
        """
        # Filter out internal tags
        self.tags = [t for t in self._check._tags if not t.startswith('dd.internal')]
        self._tags_no_db = [t for t in self.tags if not t.startswith('db:')]

        self._collect_statement_samples()
