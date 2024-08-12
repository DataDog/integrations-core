# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import time
from datetime import datetime

from bson import json_util

from datadog_checks.mongo.dbm.utils import format_key_name

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


def agent_check_getter(self):
    return self._check


class MongoSlowOperations(DBMAsyncJob):
    def __init__(self, check):
        self._slow_operations_config = check._config.slow_operations
        self._collection_interval = self._slow_operations_config["collection_interval"]
        self._max_operations = self._slow_operations_config["max_operations"]

        super(MongoSlowOperations, self).__init__(
            check,
            rate_limit=1 / self._collection_interval,
            run_sync=self._slow_operations_config.get("run_sync", False),
            enabled=self._slow_operations_config["enabled"],
            dbms="mongo",
            min_collection_interval=check._config.min_collection_interval,
            job_name="slow-operations",
        )

        self._last_collection_timestamp = None

    def run_job(self):
        self.collect_slow_operations()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_slow_operations(self):
        if not self._should_collect_slow_operations():
            return

        is_mongos = isinstance(self._check.deployment_type, MongosDeployment)

        # set of db names for which we need to collect slow operations from logs
        slow_operations_from_logs = set()

        last_collection_timestamp = self._last_collection_timestamp
        if not last_collection_timestamp:
            # First run, set the lookback to 2x the collection interval
            last_collection_timestamp = time.time() - 2 * self._collection_interval
        self._last_collection_timestamp = time.time()

        slow_operation_events = []

        for db_name in self._check._database_autodiscovery.databases:
            if not is_mongos and self._is_profiling_enabled(db_name):
                for slow_operation in self._collect_slow_operations_from_profiler(
                    db_name, last_ts=last_collection_timestamp
                ):
                    slow_operation_events.append(self._create_slow_operation_event(slow_operation))
                    if len(slow_operation_events) >= self._max_operations:
                        break
            else:
                slow_operations_from_logs.add(db_name)

        if slow_operations_from_logs and len(slow_operation_events) < self._max_operations:
            for slow_operation in self._collect_slow_operations_from_logs(
                slow_operations_from_logs, last_ts=last_collection_timestamp
            ):
                slow_operation_events.append(self._create_slow_operation_event(slow_operation))
                if len(slow_operation_events) >= self._max_operations:
                    break

        self._check.log.debug(
            "Collected %d slow operations, capped at %d", len(slow_operation_events), self._max_operations
        )
        self._check.log.debug("Sending slow operations: %s", slow_operation_events)
        if slow_operation_events:
            self._submit_slow_operation_payload(slow_operation_events)

    def _should_collect_slow_operations(self) -> bool:
        deployment = self._check.deployment_type
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self._check.log.debug("Skipping slow operations collection on arbiter node")
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

    def _collect_slow_operations_from_profiler(self, db_name, last_ts):
        profiling_data = self._check.api_client.get_profiling_data(db_name, datetime.fromtimestamp(last_ts))

        for profile in profiling_data:
            if 'command' not in profile:
                continue
            profile["ts"] = profile["ts"].timestamp()  # convert datetime to timestamp
            yield self._obfuscate_slow_operation(profile, db_name)

    def _collect_slow_operations_from_logs(self, db_names, last_ts):
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
                yield self._obfuscate_slow_operation(log_attr, db_name)

    def _obfuscate_slow_operation(self, slow_operation, db_name):
        command = slow_operation['command']
        obfuscated_command = datadog_agent.obfuscate_mongodb_string(json_util.dumps(command))
        query_signature = compute_exec_plan_signature(obfuscated_command)
        slow_operation['dbname'] = db_name
        slow_operation['command'] = obfuscated_command
        slow_operation['query_signature'] = query_signature

        if slow_operation.get('originatingCommand'):
            slow_operation['originatingCommand'] = datadog_agent.obfuscate_mongodb_string(
                json_util.dumps(slow_operation['originatingCommand'])
            )

        return slow_operation

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

    def _create_slow_operation_event(self, slow_operation):
        event = {
            "timestamp": slow_operation["ts"] * 1000,
            "dbname": slow_operation["dbname"],
            "op": slow_operation.get("op") or slow_operation.get("type"),
            "ns": slow_operation.get("ns"),
            "plan_summary": slow_operation.get("planSummary"),
            "query_signature": slow_operation["query_signature"],
            "user": slow_operation.get("user"),  # only available with profiling
            "application": slow_operation.get("appName"),  # only available with profiling
            "statement": slow_operation.get("command"),
            "query_hash": slow_operation.get("queryHash"),  # only available with profiling
            "plan_cache_key": slow_operation.get("planCacheKey"),  # only available with profiling
            "query_framework": slow_operation.get("queryFramework"),
            # metrics
            "mills": slow_operation.get("millis", slow_operation.get("durationMillis", 0)),
            "num_yields": slow_operation.get("numYield", 0),
            "response_length": slow_operation.get("responseLength", 0),
            "nreturned": slow_operation.get("nreturned"),
            "nmatched": slow_operation.get("nMatched"),
            "nmodified": slow_operation.get("nModified"),
            "ninserted": slow_operation.get("ninserted"),
            "ndeleted": slow_operation.get("ndeleted"),
            "keys_examined": slow_operation.get("keysExamined"),
            "docs_examined": slow_operation.get("docsExamined"),
            "keys_inserted": slow_operation.get("keysInserted"),
            "write_conflicts": slow_operation.get("writeConflicts"),
            "cpu_nanos": slow_operation.get("cpuNanos"),
            "planning_time_micros": slow_operation.get("planningTimeMicros"),  # only available with profiling
            "upsert": slow_operation.get("upsert"),  # only available with profiling
            "has_sort_stage": slow_operation.get("hasSortStage"),  # only available with profiling
            "used_disk": slow_operation.get("usedDisk"),  # only available with profiling
            "from_multi_planner": slow_operation.get("fromMultiPlanner"),  # only available with profiling
            "replanned": slow_operation.get("replanned"),  # only available with profiling
            "replan_reason": slow_operation.get("replanReason"),  # only available with profiling
        }

        calling_client_hostname = slow_operation.get("client") or slow_operation.get("remote")
        if calling_client_hostname:
            event["client"] = {"hostname": calling_client_hostname}

        cursor_id = slow_operation.get("cursorid")
        originating_command = slow_operation.get("originatingCommand")
        if cursor_id or originating_command:
            event["cursor"] = {
                "cursor_id": cursor_id,
                "originating_command": originating_command,
            }

        lock_stats = slow_operation.get("locks")
        if lock_stats:
            event["lock_stats"] = format_key_name(self._check.convert_to_underscore_separated, lock_stats)

        flow_control_stats = slow_operation.get("flowControl")
        if flow_control_stats:
            event["flow_control_stats"] = format_key_name(
                self._check.convert_to_underscore_separated, flow_control_stats
            )

        return self._sanitize_event(event)

    def _sanitize_event(self, event):
        # remove empty fields
        return {k: v for k, v in event.items() if v is not None}

    def _submit_slow_operation_payload(self, slow_operation_events):
        payload = {
            "host": self._check._resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongo",
            "dbm_type": "slow_query",
            "collection_interval": self._collection_interval,
            "ddtags": self._check._get_tags(include_deployment_tags=True),
            "timestamp": time.time() * 1000,
            "mongodb_slow_queries": slow_operation_events,
        }
        self._check.database_monitoring_query_activity(json_util.dumps(payload))
