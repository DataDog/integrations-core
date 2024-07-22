# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import time
from collections import defaultdict
from datetime import datetime

from bson import json_util
from datadog_checks.mongo.dbm.utils import format_key_name

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


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

    def run_job(self):
        self.collect_operation_metricss()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_operation_metricss(self):
        if not self._should_collect_operation_metrics():
            return

        is_mongos = isinstance(self._check.api_client.deployment_type, MongosDeployment)

        metrics_from_logs = set()

        last_collection_timestamp = self._last_collection_timestamp
        if not last_collection_timestamp:
            # First run, set the lookback to 2x the collection interval
            last_collection_timestamp = time.time() - 2 * self._collection_interval
        self._last_collection_timestamp = time.time()

        for db_name in self._check._database_autodiscovery.databases:
            if not is_mongos and self._is_profiling_enabled(db_name):
                for slow_query in self._collect_operation_metrics_from_profiler(db_name, last_ts=last_collection_timestamp):
                    self._submit_slow_query_payload(slow_query)
            else:
                metrics_from_logs.add(db_name)

        if metrics_from_logs:
            for slow_query in self._collect_operation_metrics_from_logs(metrics_from_logs, last_ts=last_collection_timestamp):
                self._submit_slow_query_payload(slow_query)

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
            profile["ts"] = profile["ts"].timestamp()  # convert datetime to timestamp
            yield self._obfuscate_slow_query(profile, db_name)

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
                log_attr["ts"] = ts
                yield self._obfuscate_slow_query(log_attr, db_name)

    def _obfuscate_slow_query(self, slow_query, db_name):
        command = slow_query['command']
        obfuscated_command = datadog_agent.obfuscate_mongodb_string(json_util.dumps(command))
        query_signature = compute_exec_plan_signature(obfuscated_command)
        slow_query['dbname'] = db_name
        slow_query['command'] = obfuscated_command
        slow_query['query_signature'] = query_signature

        if slow_query.get('originatingCommand'):
            slow_query['originatingCommand'] = datadog_agent.obfuscate_mongodb_string(json_util.dumps(slow_query['originatingCommand']))

        yield slow_query

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
    
    def _submit_slow_query_payload(self, slow_query):
        event = {
            "host": self._check._resolved_hostname,
            "dbm_type": "slow_query",
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongo",
            "ddtags": ",".join(self._check._get_tags(include_deployment_tags=True)),
            "timestamp": slow_query["ts"],
            "network": {
                "client": {
                    "ip": slow_query.get("client"),
                }
            },
            "db": {
                "instance": slow_query["dbname"],
                "query_signature": slow_query["query_signature"],
                "user": slow_query.get("user"),
                "application": slow_query.get("appName"),
                "statement": slow_query.get("command"),
            },
            "mongodb": {
                # metadata
                "op": slow_query.get("op"),
                "ns": slow_query.get("ns"),
                "plan_summary": slow_query.get("planSummary"),
                "exec_stats": slow_query.get("execStats"),
                "originating_command": slow_query.get("originatingCommand"),
                "query_hash": slow_query.get("queryHash"),  # only available with profiling
                "plan_cache_key": slow_query.get("planCacheKey"),  # only available with profiling
                "query_framework": slow_query.get("queryFramework"),
                # metrics
                "duration": slow_query.get("millis", slow_query.get("durationMillis")),
                "num_yield": slow_query.get("numYield"),
                "response_length": slow_query.get("responseLength"),
                "nreturned": slow_query.get("nreturned"),
                "nmatched": slow_query.get("nMatched"),
                "nmodified": slow_query.get("nModified"),
                "ninserted": slow_query.get("ninserted"),
                "ndeleted": slow_query.get("ndeleted"),
                "keys_examined": slow_query.get("keysExamined"),
                "docs_examined": slow_query.get("docsExamined"),
                "keys_inserted": slow_query.get("keysInserted"),
                "write_conflicts": slow_query.get("writeConflicts"),
                "cpu_nanos": slow_query.get("cpuNanos"),
                "planning_time_micros": slow_query.get("planningTimeMicros"),
                "upsert": slow_query.get("upsert", False),
                "has_sort_stage": slow_query.get("hasSortStage", False),
                "used_disk": slow_query.get("usedDisk", False),
                "from_multi_planner": slow_query.get("fromMultiPlanner", False),
                "replanned": slow_query.get("replanned", False),
                "storage": format_key_name(self._check, slow_query.get("storage", {})),
                "locks": format_key_name(self._check, slow_query.get("locks", {})),
                "flow_control": format_key_name(self._check, slow_query.get("flowControl", {})),
            },
        }
        self._check.database_monitoring_query_sample(json_util.dumps(event))
