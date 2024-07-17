# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import time
from collections import defaultdict
from datetime import datetime

from bson import json_util

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment

EXPECTED_METRICS = {
    "keysExamined",
    "docsExamined",
    "ndeleted",
    "ninserted",
    "nMatched",
    "nModified",
    "keysInserted",
    "writeConflicts",
    "numYield",
    "nreturned",
    "responseLength",
    "cpuNanos",
    "millis",
    "planningTimeMicros",
    "calls",
    "locks",
    "flowControl",
    "storage",
    "hasSortStage",  # true when the query has a sort stage
    "usedDisk",  # true when any stage wrote to temp files
    "fromMultiPlanner",  # true when the query planner evaluated multiple plans
    "replanned",  # true when the query system evicted cached plan
}

EXPECTED_METADATA = {
    "dbname",
    "op",
    "ns",
    "planSummary",
    "command",
    "replanReason",
    "query_signature",
}

REMAPPED_METRICS = {
    'durationMillis': 'millis',  # log uses durationMillis, profiler uses millis
}


def agent_check_getter(self):
    return self._check


class MongoOperationMetrics(DBMAsyncJob):
    def __init__(self, check):
        self._operation_metrics_config = check._config.operation_metrics
        self._collection_interval = self._operation_metrics_config["collection_interval"]

        super(MongoOperationMetrics, self).__init__(
            check,
            rate_limit=1 / self._collection_interval,
            run_sync=self._operation_metrics_config.get("run_sync", False),
            enabled=self._operation_metrics_config["enabled"],
            dbms="mongodb",
            min_collection_interval=check._config.min_collection_interval,
            job_name="operation-metricss",
        )

        self._last_collection_timestamp = None
        self.query_signature_to_metrics = defaultdict(dict)

    def run_job(self):
        self.collect_operation_metricss()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_operation_metricss(self):
        if not self._should_collect_operation_metrics():
            return

        is_mongos = isinstance(self._check.api_client.deployment_type, MongosDeployment)

        self.query_signature_to_metrics.clear()
        metrics_from_logs = set()

        last_collection_timestamp = self._last_collection_timestamp
        if not last_collection_timestamp:
            # First run, set the lookback to 2x the collection interval
            last_collection_timestamp = time.time() - 2 * self._collection_interval
        self._last_collection_timestamp = time.time()

        for db_name in self._check._database_autodiscovery.databases:
            if not is_mongos and self._is_profiling_enabled(db_name):
                self._collect_operation_metrics_from_profiler(db_name, last_ts=last_collection_timestamp)
            else:
                metrics_from_logs.add(db_name)

        if metrics_from_logs:
            self._collect_operation_metrics_from_logs(metrics_from_logs, last_ts=last_collection_timestamp)

        self._submit_metrics_payload()

    def _should_collect_operation_metrics(self) -> bool:
        deployment = self._check.api_client.deployment_type
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self._check.log.debug("Skipping operation metrics collection on arbiter node")
            return False
        return True

    def _is_profiling_enabled(self, db_name):
        profiling_level = self._check.api_client.get_profiling_level(db_name)
        level = profiling_level.get("was", 0)  # profiling by default is disabled
        slowms = profiling_level.get("slowms", 100)  # slowms threshold is 100ms by default
        tags = self._check._get_tags(include_deployment_tags=True, include_internal_resource_tags=True)
        tags.append("db:%s" % db_name)
        # Emit the profiling level and slowms as raw metrics
        # raw ensures that level = 0 is also emitted
        self._check.gauge('mongodb.profiling.level', level, tags=tags, raw=True)
        self._check.gauge('mongodb.profiling.slowms', slowms, tags=tags, raw=True)
        return level > 0

    def _collect_operation_metrics_from_profiler(self, db_name, last_ts):
        """
        Collect operation metrics from database profiler collections
        """
        profiling_data = self._check.api_client.get_profiling_data(db_name, datetime.fromtimestamp(last_ts))

        for profile in profiling_data:
            if 'command' not in profile:
                continue
            self._obfuscate_and_aggregate_metrics(profile, db_name)

    def _collect_operation_metrics_from_logs(self, db_names, last_ts):
        logs = self._check.api_client.get_log_data()
        log_entries = logs.get("log", [])
        start_index = self._binary_search(log_entries, last_ts)
        for i in range(start_index, len(log_entries)):
            parsed_log = log_entries[i]
            if isinstance(parsed_log, str):
                try:
                    parsed_log = json_util.loads(parsed_log)
                except Exception as e:
                    self._check.log.error("Failed to parse log line: %s", e)
                    continue
            if parsed_log.get("msg", "").lower() == 'slow query':
                ts = parsed_log["t"].timestamp()
                if ts <= last_ts:
                    # This check is still needed when binary search fails to parse a log line
                    # we need to performance linear search for the rest of the logs
                    continue
                log_attr = parsed_log.get("attr")
                if not log_attr or "command" not in log_attr:
                    continue
                db_name = self._get_db_name(log_attr.get("command"), log_attr.get("ns"))
                if db_name not in db_names:
                    continue
                self._obfuscate_and_aggregate_metrics(log_attr, db_name)

    def _obfuscate_and_aggregate_metrics(self, query_metrics, db_name):
        command = query_metrics['command']
        obfuscated_command = datadog_agent.obfuscate_mongodb_string(json_util.dumps(command))
        query_signature = compute_exec_plan_signature(obfuscated_command)
        query_metrics['dbname'] = db_name
        query_metrics['command'] = obfuscated_command
        query_metrics['query_signature'] = query_signature
        query_metrics['calls'] = 1

        key = (
            db_name,
            query_metrics.get("op"),
            query_metrics.get("ns"),
            query_metrics.get("planSummary"),
            query_signature,
        )
        self._aggregate_metrics_by_signature(key=key, query_metrics=query_metrics)

    def _aggregate_metrics_by_signature(self, key, query_metrics):
        if key not in self.query_signature_to_metrics:
            # Initialize the dictionary with the metadata fields
            for metadata_name in EXPECTED_METADATA:
                formatted_metadata_name = to_native_string(self._check.convert_to_underscore_separated(metadata_name))
                self.query_signature_to_metrics[key][formatted_metadata_name] = query_metrics.get(metadata_name)

        for metric_name in REMAPPED_METRICS:
            if metric_name in query_metrics:
                query_metrics[REMAPPED_METRICS[metric_name]] = query_metrics.pop(metric_name)

        for metric_name in EXPECTED_METRICS:
            # Loop through the expected metrics and aggregate them by the query key
            formatted_metric_name = to_native_string(self._check.convert_to_underscore_separated(metric_name))
            self.query_signature_to_metrics[key][formatted_metric_name] = self._merge_metrics(
                self.query_signature_to_metrics[key].get(formatted_metric_name),
                query_metrics.get(metric_name),
            )

    def _merge_metrics(self, prev_metrics, new_metrics):
        # Merge the metrics from the previous with the new metrics
        # if prev_metrics or new_metrics is a dict, recursively merge the values
        if not new_metrics:
            return prev_metrics

        if isinstance(new_metrics, dict):
            if not prev_metrics:
                prev_metrics = {}
            for key in new_metrics:
                formatted_key = to_native_string(self._check.convert_to_underscore_separated(key))
                if isinstance(new_metrics[key], dict):
                    prev_metrics[formatted_key] = self._merge_metrics(
                        prev_metrics.get(formatted_key, {}), new_metrics[key]
                    )
                else:
                    prev_metrics[formatted_key] = prev_metrics.get(formatted_key, 0) + new_metrics[key]
        elif isinstance(new_metrics, bool):
            # For metrics with boolean value, e.g. hasSortStage, usedDisk, replanned, etc.
            # We keep the true value if any of behavior happened for the normalized query over the collection interval
            prev_metrics = bool(new_metrics or prev_metrics)
        else:
            prev_metrics = new_metrics + (prev_metrics or 0)
        return prev_metrics

    def _get_db_name(self, command, ns):
        return command.get('$db') or ns.split('.', 1)[0]

    def _binary_search(self, logs, ts):
        # Binary search to find the index of the first log line with timestamp >= ts
        # In case of failure to parse a log line, we skip binary search and linearly search the rest of the logs
        left, right = 0, len(logs) - 1
        while left <= right:
            mid = (left + right) // 2
            try:
                parsed_log = json_util.loads(logs[mid])
            except Exception as e:
                self._check.log.debug("Failed to parse log line: %s", e)
                # If we can't parse the log, skip binary search and linearly search the rest of the logs
                return left
            logs[mid] = parsed_log
            log_ts = parsed_log["t"].timestamp()
            if log_ts < ts:
                left = mid + 1
            elif log_ts > ts:
                right = mid - 1
            else:
                return mid + 1
        return left

    def _submit_metrics_payload(self):
        payload = {
            'host': self._check._resolved_hostname,
            'ddagentversion': datadog_agent.get_version(),
            'timestamp': time.time() * 1000,
            'min_collection_interval': self._collection_interval,
            'tags': self._check._get_tags(include_deployment_tags=True),
            'mongodb_rows': list(self.query_signature_to_metrics.values()),
            'mongodb_version': self._check._mongo_version,
        }
        self._check.log.debug("Submitting operation metrics payload: %s", payload)
        self._check.database_monitoring_query_metrics(json_util.dumps(payload))
