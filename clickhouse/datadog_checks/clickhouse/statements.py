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
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding, obfuscate_sql_with_metadata
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method

# Query to fetch aggregated metrics from system.query_log
# This is the ClickHouse equivalent of Postgres pg_stat_statements
#
# Key design decisions:
# - Queries the LOCAL system.query_log table on this node only
# - Uses event_date predicate for partition pruning optimization
# - Uses is_initial_query=1 to only count queries once (not sub-queries)
# - Uses type != 'QueryStart' to get one record per completed query
# - Uses normalizeQuery() to get query text with wildcards representing the entire set
# - Uses quantiles() to calculate p50, p90, p95, p99 simultaneously
# - Removed ORDER BY and LIMIT to avoid losing data at high QPS
#
# Note: We collect count() and sum() metrics which are treated as cumulative counters
# and then compute derivatives. Quantile metrics (p50, p90, p95, p99) are point-in-time
# aggregates and are NOT included in derivative calculation.
# mean_time is computed from total_time/count after derivatives.

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
    any(user) as user,
    any(type) as query_type,
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
    max(memory_usage) as peak_memory_usage
FROM system.query_log
WHERE event_date >= toDate(now() - INTERVAL {collection_interval} SECOND)
  AND event_time >= now() - INTERVAL {collection_interval} SECOND
  AND type != 'QueryStart'
  AND is_initial_query = 1
  AND query NOT LIKE '%system.query_log%'
  AND query NOT LIKE '%system.processes%'
  AND query NOT LIKE '/* DDIGNORE */%'
  AND query != ''
  AND normalized_query_hash != 0
  {internal_user_filter}
GROUP BY normalized_query_hash
"""


def agent_check_getter(self):
    return self._check


def _row_key(row):
    """
    :param row: a normalized row from system.query_log
    :return: a tuple uniquely identifying this row
    """
    return row['query_signature'], row.get('user', ''), row.get('databases', '')


class ClickhouseStatementMetrics(DBMAsyncJob):
    """Collects telemetry for SQL statements from system.query_log"""

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

        # full_statement_text_cache: limit the ingestion rate of full statement text events per query_signature
        self._full_statement_text_cache = TTLCache(
            maxsize=getattr(config, 'full_statement_text_cache_max_size', 10000),
            ttl=60 * 60 / getattr(config, 'full_statement_text_samples_per_hour_per_query', 1),
        )

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
        self.collect_per_statement_metrics()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_per_statement_metrics(self):
        """
        Collect per-statement metrics from system.query_log and emit as:
        1. FQT events (dbm_type: fqt) - for query text catalog
        2. Query metrics payload - for time-series metrics
        """
        try:
            rows = self._collect_metrics_rows()
            if not rows:
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
                'clickhouse_version': self._get_clickhouse_version(),
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

        except Exception:
            self._log.exception('Unable to collect statement metrics due to an error')
            return []

    def _get_clickhouse_version(self):
        """Get ClickHouse version string"""
        try:
            version_rows = self._check.execute_query_raw('SELECT version()')
            if version_rows:
                return str(version_rows[0][0])
        except Exception:
            pass
        return 'unknown'

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
        if not INTERNAL_CLOUD_USERS:
            return ""
        # Build a NOT IN clause for the internal users
        users_list = ", ".join(f"'{user}'" for user in INTERNAL_CLOUD_USERS)
        return f"AND user NOT IN ({users_list})"

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _load_query_log_statements(self):
        """
        Load aggregated query metrics from the local system.query_log table.
        This is analogous to Postgres loading from pg_stat_statements.

        Queries only the local node's query_log - each ClickHouse node maintains
        its own query_log table with queries executed on that specific node.
        """
        try:
            query = STATEMENTS_QUERY.format(
                collection_interval=int(self._metrics_collection_interval),
                internal_user_filter=self._get_internal_user_filter(),
            )
            rows = self._execute_query(query)

            self._log.debug("Loaded %s rows from local system.query_log", len(rows))

            # Convert to list of dicts
            result_rows = []
            for row in rows:
                (
                    normalized_query_hash,
                    query_text,
                    user,
                    query_type,
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
                ) = row

                # Parse quantiles array: [p50, p90, p95, p99]
                p50_time = float(duration_quantiles[0]) if duration_quantiles and len(duration_quantiles) > 0 else 0.0
                p90_time = float(duration_quantiles[1]) if duration_quantiles and len(duration_quantiles) > 1 else 0.0
                p95_time = float(duration_quantiles[2]) if duration_quantiles and len(duration_quantiles) > 2 else 0.0
                p99_time = float(duration_quantiles[3]) if duration_quantiles and len(duration_quantiles) > 3 else 0.0

                result_rows.append(
                    {
                        'normalized_query_hash': str(normalized_query_hash),
                        'query': str(query_text) if query_text else '',
                        'user': str(user) if user else '',
                        'query_type': str(query_type) if query_type else '',
                        'databases': str(databases[0]) if databases and len(databases) > 0 else '',
                        'tables': tables if tables else [],
                        'count': int(execution_count) if execution_count else 0,
                        'total_time': float(total_duration_ms) if total_duration_ms else 0.0,
                        # Quantile metrics (p50, p90, p95, p99) - these are point-in-time aggregates
                        # and are NOT included in derivative calculation
                        'p50_time': p50_time,
                        'p90_time': p90_time,
                        'p95_time': p95_time,
                        'p99_time': p99_time,
                        # Note: mean_time will be calculated after derivative calculation as total_time / count
                        'rows': int(total_result_rows) if total_result_rows else 0,
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
            return []

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_metrics_rows(self):
        """
        Collect and normalize query metrics rows
        """
        rows = self._load_query_log_statements()
        if not rows:
            return []

        # Normalize queries (obfuscate SQL text)
        rows = self._normalize_queries(rows)

        if not rows:
            return []

        # Get available metric columns
        # Note: We only include counter metrics (count, totals) in derivative calculation.
        # Aggregated metrics like mean_time, min_time, max_time, p95_time are excluded
        # because taking derivatives of averages/percentiles is mathematically incorrect.
        available_columns = set(rows[0].keys())
        metric_columns = available_columns & {
            'count',
            'total_time',
            'rows',
            'read_rows',
            'read_bytes',
            'written_rows',
            'written_bytes',
            'result_bytes',
            'memory_usage',
            'peak_memory_usage',
        }

        # Compute derivative rows (calculate deltas since last collection)
        rows_before = len(rows)
        rows = self._state.compute_derivative_rows(rows, metric_columns, key=_row_key, execution_indicators=['count'])
        rows_after = len(rows)

        # Calculate mean_time from derivative values (total_time / count)
        # This follows the same pattern as Postgres, MySQL, and SQL Server
        for row in rows:
            if row.get('count', 0) > 0:
                row['mean_time'] = row.get('total_time', 0.0) / row['count']
            else:
                row['mean_time'] = 0.0

        self._log.info(
            "Query metrics: loaded=%d rows, after_derivative=%d rows (filtered=%d)",
            rows_before,
            rows_after,
            rows_before - rows_after,
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
            normalized_row['dd_tables'] = metadata.get('tables', None)
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
