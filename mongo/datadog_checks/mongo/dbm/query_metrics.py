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
from datadog_checks.mongo.common import HostingType, ReplicaSetDeployment

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
# For Atlas deployments, $queryStats is available in MongoDB 7.0+
# For self-hosted deployments, $queryStats requires MongoDB 8.0+
MINIMUM_MONGODB_VERSION_ATLAS = Version("7.0")
MINIMUM_MONGODB_VERSION_SELF_HOSTED = Version("8.0")

# Mapping from MongoDB $queryStats field names to our normalized field names
# Each entry maps: mongodb_field -> (our_field_name, extraction_type)
# extraction_type: 'sum' for sum-based metrics, 'true_count' for boolean counters, 'direct' for direct values
METRICS_FIELD_MAPPING = {
    'execCount': ('exec_count', 'direct'),
    'totalExecMicros': ('total_exec_micros_sum', 'sum'),
    'firstResponseExecMicros': ('first_response_exec_micros_sum', 'sum'),
    'keysExamined': ('keys_examined_sum', 'sum'),
    'docsExamined': ('docs_examined_sum', 'sum'),
    'docsReturned': ('docs_returned_sum', 'sum'),
    # MongoDB 8.0+
    'bytesRead': ('bytes_read_sum', 'sum'),
    'cpuNanos': ('cpu_nanos_sum', 'sum'),
    'usedDisk': ('used_disk_count', 'true_count'),
    'hasSortStage': ('has_sort_stage_count', 'true_count'),
    'readTimeMicros': ('read_time_micros_sum', 'sum'),
    'workingTimeMillis': ('working_time_millis_sum', 'sum'),
}


def agent_check_getter(self):
    return self._check


class MongoQueryMetrics(DBMAsyncJob):
    """
    Collects query metrics from MongoDB using $queryStats aggregation pipeline.

    This is available in MongoDB 7.0+ for Atlas deployments and MongoDB 8.0+ for self-hosted.

    The implementation flow:
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

        # Check MongoDB version
        # Atlas supports $queryStats in MongoDB 7.0+, self-hosted requires 8.0+
        if not self._check._mongo_version_parsed:
            self._check.log.debug("MongoDB version not available yet, skipping query metrics collection")
            return False

        # Determine minimum version based on hosting type
        is_atlas = deployment.hosting_type == HostingType.ATLAS
        min_version = MINIMUM_MONGODB_VERSION_ATLAS if is_atlas else MINIMUM_MONGODB_VERSION_SELF_HOSTED

        if self._check._mongo_version_parsed < min_version:
            if not self._version_warning_logged:
                version_requirement = "7.0+" if is_atlas else "8.0+"
                self._check.log.warning(
                    "Query metrics collection requires MongoDB %s for %s deployments. "
                    "Current version: %s. Skipping collection.",
                    version_requirement,
                    "Atlas" if is_atlas else "self-hosted",
                    self._check._mongo_version,
                )
                self._version_warning_logged = True
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
                "Ensure the user has the clusterMonitor role and MongoDB version supports $queryStats "
                "(7.0+ for Atlas, 8.0+ for self-hosted).",
                e,
            )

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

        normalized_rows = self._normalize_rows(raw_rows)
        if not normalized_rows:
            return []

        # Dynamically determine which metric columns exist based on MongoDB version
        metrics_columns = self._get_available_metrics_columns(normalized_rows)

        # Compute derivative metrics
        rows = self._statement_metrics.compute_derivative_rows(
            normalized_rows, metrics_columns, key=get_query_stats_row_key, execution_indicators=['exec_count']
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

                # Skip if database not in monitored list or is admin
                if db_name not in databases_monitored or db_name == 'admin':
                    continue

                # Reconstruct command and obfuscate
                reconstructed_cmd = reconstruct_command_from_query_shape(query_shape)
                obfuscated_command = obfuscate_command(reconstructed_cmd)
                query_signature = compute_exec_plan_signature(obfuscated_command)

                # Build row with required fields
                row: QueryMetricsRow = {
                    'query_signature': query_signature,
                    'db_name': db_name,
                    'collection': coll_name,
                    'obfuscated_command': obfuscated_command,
                    'command_type': query_shape.get('command', 'unknown'),
                    'key_hash': doc.get('keyHash', ''),
                    'query_shape_hash': doc.get('queryShapeHash', ''),
                    # Timestamps
                    'first_seen_timestamp': self._format_timestamp(metrics.get('firstSeenTimestamp')),
                    'latest_seen_timestamp': self._format_timestamp(metrics.get('latestSeenTimestamp')),
                }

                # Dynamically extract metrics based on what's available in $queryStats response
                for mongo_field, (our_field, extraction_type) in METRICS_FIELD_MAPPING.items():
                    raw_value = metrics.get(mongo_field)
                    if raw_value is None:
                        continue

                    if extraction_type == 'direct':
                        row[our_field] = raw_value
                    elif extraction_type == 'sum':
                        if isinstance(raw_value, dict) and 'sum' in raw_value:
                            row[our_field] = raw_value['sum']
                    elif extraction_type == 'true_count':
                        if isinstance(raw_value, dict) and 'true' in raw_value:
                            row[our_field] = raw_value['true']

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

    def _get_available_metrics_columns(self, normalized_rows: list[QueryMetricsRow]) -> list[str]:
        """
        Determine which metric columns are available in the normalized rows.

        Returns only columns that exist in at least one row, handling differences
        between MongoDB versions (7.0 has fewer metrics than 8.0).
        """
        if not normalized_rows:
            return []

        # Get all possible metric column names from the mapping
        all_metric_columns = {field_name for field_name, _ in METRICS_FIELD_MAPPING.values()}

        # Find which columns actually exist in the normalized rows
        available_columns = set()
        for row in normalized_rows:
            for col in all_metric_columns:
                if col in row:
                    available_columns.add(col)

        return list(available_columns)

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
