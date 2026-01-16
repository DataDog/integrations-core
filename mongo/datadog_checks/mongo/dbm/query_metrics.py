# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import time
from typing import Iterator

from cachetools import TTLCache
from packaging.version import Version
from pymongo.errors import OperationFailure

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.statement_metrics import StatementMetrics
from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mongo.common import ReplicaSetDeployment

from .types import QueryMetricsRow
from .utils import (
    get_query_stats_row_key,
    obfuscate_command,
    reconstruct_command_from_query_shape,
)

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


# Minimum MongoDB version required for $queryStats
MINIMUM_MONGODB_VERSION = Version("8.0")

# Metrics columns for derivative calculation
QUERY_METRICS_COLUMNS = frozenset(
    {
        'exec_count',
        'total_exec_micros_sum',
        'first_response_exec_micros_sum',
        'keys_examined_sum',
        'docs_examined_sum',
        'docs_returned_sum',
        # P1 metrics
        'bytes_read_sum',
        'cpu_nanos_sum',
        'used_disk_count',
        'has_sort_stage_count',
        # P2 metrics
        'read_time_micros_sum',
        'working_time_millis_sum',
    }
)


def agent_check_getter(self):
    return self._check


class MongoQueryMetrics(DBMAsyncJob):
    """
    Collects query metrics from MongoDB using $queryStats aggregation pipeline.

    This is only available in MongoDB 8.0+.

    The implementation follows the pattern established by PostgresStatementMetrics:
    1. Collect raw statistics from $queryStats
    2. Normalize and reconstruct queries for unified obfuscation
    3. Compute derivative metrics using StatementMetrics
    4. Batch and submit payloads
    """

    def __init__(self, check):
        self._query_metrics_config = check._config.query_metrics
        self._collection_interval = self._query_metrics_config['collection_interval']

        super(MongoQueryMetrics, self).__init__(
            check,
            rate_limit=1 / self._collection_interval,
            run_sync=self._query_metrics_config.get('run_sync', False),
            enabled=self._query_metrics_config['enabled'],
            dbms='mongo',
            min_collection_interval=check._config.min_collection_interval,
            job_name='query-metrics',
        )

        # StatementMetrics handles derivative calculation
        self._statement_metrics = StatementMetrics()

        # Cache for full query text to avoid sending duplicates
        self._full_statement_text_cache = TTLCache(
            maxsize=self._query_metrics_config['full_statement_text_cache_max_size'],
            ttl=60 * 60 / self._query_metrics_config['full_statement_text_samples_per_hour_per_query'],
        )

        # Track if we've logged the version warning
        self._version_warning_logged = False

    def run_job(self):
        self.collect_query_metrics()

    def _should_collect_query_metrics(self) -> bool:
        """Check if query metrics collection should run."""
        # Skip on arbiter nodes
        deployment = self._check.deployment_type
        if isinstance(deployment, ReplicaSetDeployment):
            if deployment.is_arbiter:
                self._check.log.debug("Skipping query metrics collection on arbiter node")
                return False
            if deployment.replset_state == 3:  # RECOVERING
                self._check.log.debug("Skipping query metrics collection on node in recovering state")
                return False

        # Check MongoDB version (8.0+ required)
        if not self._check._mongo_version:
            self._check.log.debug("MongoDB version not available yet, skipping query metrics collection")
            return False

        try:
            mongo_version = Version(self._check._mongo_version.split('-')[0])
            if mongo_version < MINIMUM_MONGODB_VERSION:
                if not self._version_warning_logged:
                    self._check.log.warning(
                        "Query metrics collection requires MongoDB 8.0+. Current version: %s. Skipping collection.",
                        self._check._mongo_version,
                    )
                    self._version_warning_logged = True
                return False
        except Exception as e:
            self._check.log.debug("Could not parse MongoDB version: %s", e)
            return False

        return True

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_query_metrics(self):
        """Main collection method."""
        if not self._should_collect_query_metrics():
            return

        try:
            rows = self._collect_metrics_rows()
            if not rows:
                return

            # Emit full query text events for new queries
            for event in self._rows_to_fqt_events(rows):
                self._check.database_monitoring_query_sample(json.dumps(event, default=default_json_event_encoding))

            # Build and submit query metrics payloads
            tags = self._check._get_tags(include_internal_resource_tags=True)
            # Remove db tag as it will be per-query
            tags_no_db = [t for t in tags if not t.startswith('db:')]

            payload_wrapper = {
                'host': self._check._resolved_hostname,
                'timestamp': time.time() * 1000,
                'min_collection_interval': self._collection_interval,
                'tags': tags_no_db,
                'cloud_metadata': self._check._config.cloud_metadata,
                'mongo_version': self._check._mongo_version,
                'ddagentversion': datadog_agent.get_version(),
                'service': self._check._config.service,
            }

            payloads = self._get_query_metrics_payloads(payload_wrapper, rows)
            for payload in payloads:
                self._check.database_monitoring_query_metrics(payload)

        except OperationFailure as e:
            # $queryStats might not be available or user lacks permissions
            self._check.log.warning(
                "Failed to collect query metrics: %s. "
                "Ensure the user has the clusterMonitor role and MongoDB 8.0+ is running.",
                e,
            )
        except Exception as e:
            self._check.log.exception("Unexpected error while collecting query metrics: %s", e)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _collect_metrics_rows(self) -> list[QueryMetricsRow]:
        """
        Collect and process query statistics rows.

        1. Query $queryStats
        2. Normalize rows (reconstruct commands, obfuscate, compute signatures)
        3. Compute derivative metrics
        """
        raw_rows = list(self._load_query_stats())
        if not raw_rows:
            return []

        # Normalize rows
        normalized_rows = self._normalize_rows(raw_rows)
        if not normalized_rows:
            return []

        # Compute derivative metrics
        rows = self._statement_metrics.compute_derivative_rows(
            normalized_rows, QUERY_METRICS_COLUMNS, key=get_query_stats_row_key, execution_indicators=['exec_count']
        )

        self._check.gauge(
            'dd.mongodb.queries.query_rows_raw',
            len(rows),
            tags=self._check._get_tags(include_internal_resource_tags=True),
            hostname=self._check._resolved_hostname,
            raw=True,
        )

        return rows

    def _load_query_stats(self) -> Iterator[dict]:
        """Load raw query statistics from MongoDB."""
        try:
            for doc in self._check.api_client.query_stats():
                yield doc
        except OperationFailure as e:
            self._check.log.warning("Failed to query $queryStats: %s", e)
            raise

    def _normalize_rows(self, raw_rows: list[dict]) -> list[QueryMetricsRow]:
        """
        Normalize raw $queryStats rows into a consistent format for processing.

        This includes:
        1. Reconstructing the command from query shape
        2. Obfuscating the command for sensitive data removal
        3. Computing query signature for deduplication
        4. Extracting and flattening metrics
        """
        normalized = []
        databases_monitored = set(self._check.databases_monitored)

        for doc in raw_rows:
            try:
                key = doc.get('key', {})
                query_shape = key.get('queryShape', {})
                metrics = doc.get('metrics', {})

                # Extract namespace info
                cmd_ns = query_shape.get('cmdNs', {})
                db_name = cmd_ns.get('db', '')
                coll_name = cmd_ns.get('coll', '')

                # Skip if database not in monitored list
                if db_name not in databases_monitored:
                    continue

                # Skip admin database
                if db_name == 'admin':
                    continue

                # Reconstruct command and obfuscate
                reconstructed_cmd = reconstruct_command_from_query_shape(query_shape)
                obfuscated_command = obfuscate_command(reconstructed_cmd)
                query_signature = compute_exec_plan_signature(obfuscated_command)

                # Extract and flatten metrics
                exec_count = metrics.get('execCount', 0)
                total_exec_micros = metrics.get('totalExecMicros', {})
                first_response_exec_micros = metrics.get('firstResponseExecMicros', {})
                keys_examined = metrics.get('keysExamined', {})
                docs_examined = metrics.get('docsExamined', {})
                docs_returned = metrics.get('docsReturned', {})
                # P1 metrics
                bytes_read = metrics.get('bytesRead', {})
                cpu_nanos = metrics.get('cpuNanos', {})
                used_disk = metrics.get('usedDisk', {})
                has_sort_stage = metrics.get('hasSortStage', {})
                # P2 metrics
                read_time_micros = metrics.get('readTimeMicros', {})
                working_time_millis = metrics.get('workingTimeMillis', {})

                row: QueryMetricsRow = {
                    'query_signature': query_signature,
                    'db_name': db_name,
                    'collection': coll_name,
                    'obfuscated_command': obfuscated_command,
                    'command_type': query_shape.get('command', 'unknown'),
                    'key_hash': doc.get('keyHash', ''),
                    'query_shape_hash': doc.get('queryShapeHash', ''),
                    # Metrics for derivative calculation
                    'exec_count': exec_count,
                    'total_exec_micros_sum': total_exec_micros.get('sum', 0),
                    'first_response_exec_micros_sum': first_response_exec_micros.get('sum', 0),
                    'keys_examined_sum': keys_examined.get('sum', 0),
                    'docs_examined_sum': docs_examined.get('sum', 0),
                    'docs_returned_sum': docs_returned.get('sum', 0),
                    # P1 metrics
                    'bytes_read_sum': bytes_read.get('sum', 0),
                    'cpu_nanos_sum': cpu_nanos.get('sum', 0),
                    'used_disk_count': used_disk.get('true', 0),
                    'has_sort_stage_count': has_sort_stage.get('true', 0),
                    # P2 metrics
                    'read_time_micros_sum': read_time_micros.get('sum', 0),
                    'working_time_millis_sum': working_time_millis.get('sum', 0),
                    # Timestamps
                    'first_seen_timestamp': self._format_timestamp(metrics.get('firstSeenTimestamp')),
                    'latest_seen_timestamp': self._format_timestamp(metrics.get('latestSeenTimestamp')),
                }

                normalized.append(row)

            except Exception as e:
                self._check.log.debug("Failed to normalize query stats row: %s", e)
                continue

        return normalized

    def _format_timestamp(self, ts) -> str | None:
        """Format a timestamp for output."""
        if ts is None:
            return None
        if hasattr(ts, 'isoformat'):
            return ts.isoformat()
        return str(ts)

    def _get_query_metrics_payloads(self, payload_wrapper: dict, rows: list) -> list[str]:
        """
        Generate batched payloads for query metrics.

        Follows the PostgreSQL pattern of binary splitting for oversized payloads.
        """
        payloads = []
        max_size = 20000000  # 20MB max payload size
        queue = [rows]

        while queue:
            current = queue.pop()
            if len(current) == 0:
                continue

            payload = copy.deepcopy(payload_wrapper)
            payload['mongo_rows'] = current
            serialized_payload = json.dumps(payload, default=default_json_event_encoding)
            size = len(serialized_payload)

            if size < max_size:
                payloads.append(serialized_payload)
            else:
                if len(current) == 1:
                    self._check.log.warning(
                        "A single query is too large to send to Datadog. This query will be dropped. size=%d", size
                    )
                    continue
                # Split in half and retry
                mid = len(current) // 2
                queue.append(current[:mid])
                queue.append(current[mid:])

        return payloads

    def _rows_to_fqt_events(self, rows: list[QueryMetricsRow]) -> Iterator[dict]:
        """
        Generate Full Query Text events for new queries.

        This allows the backend to store the full (obfuscated) query text
        separately from the metrics payload.
        """
        tags = self._check._get_tags(include_internal_resource_tags=True)
        tags_no_db = [t for t in tags if not t.startswith('db:')]

        for row in rows:
            query_cache_key = get_query_stats_row_key(row)
            if query_cache_key in self._full_statement_text_cache:
                continue

            self._full_statement_text_cache[query_cache_key] = True

            row_tags = tags_no_db + [f"db:{row['db_name']}"]

            yield {
                'timestamp': time.time() * 1000,
                'host': self._check._resolved_hostname,
                'ddagentversion': datadog_agent.get_version(),
                'ddsource': 'mongo',
                'ddtags': ','.join(row_tags),
                'dbm_type': 'fqt',
                'service': self._check._config.service,
                'db': {
                    'instance': row['db_name'],
                    'query_signature': row['query_signature'],
                    'statement': row['obfuscated_command'],
                    'metadata': {
                        'collection': row['collection'],
                        'command_type': row['command_type'],
                    },
                },
                'mongodb': {
                    'collection': row['collection'],
                    'command_type': row['command_type'],
                },
            }
