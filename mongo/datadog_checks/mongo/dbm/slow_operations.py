# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import time
from datetime import datetime

from bson import json_util
from cachetools import TTLCache
from pymongo.errors import OperationFailure

from datadog_checks.mongo.dbm.utils import (
    format_explain_plan,
    format_key_name,
    get_command_collection,
    get_command_truncation_state,
    get_db_from_namespace,
    get_explain_plan,
    obfuscate_command,
    should_explain_operation,
)

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, RateLimitingTTLCache
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mongo.common import MongosDeployment, ReplicaSetDeployment


def agent_check_getter(self):
    return self._check


class MongoSlowOperations(DBMAsyncJob):
    def __init__(self, check):
        self._slow_operations_config = check._config.slow_operations
        self._collection_interval = self._slow_operations_config["collection_interval"]
        self._max_operations = self._slow_operations_config["max_operations"]

        # _explained_operations_ratelimiter: limit how often we try to re-explain the same query
        self._explained_operations_ratelimiter = RateLimitingTTLCache(
            maxsize=self._slow_operations_config['explained_operations_cache_maxsize'],
            ttl=45 * 60 / self._slow_operations_config['explained_operations_per_hour_per_query'],
        )
        # _database_profiling_levels: cache the profiling levels for each database
        self._database_profiling_levels = TTLCache(
            maxsize=check._database_autodiscovery._max_databases,
            ttl=60 * 60,  # 1 hour
        )

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

        self._log_json_opts = json_util.JSONOptions(tz_aware=True)

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

        for db_name in self._check.databases_monitored:
            if not is_mongos and self._is_profiling_enabled(db_name):
                for slow_operation in self._collect_slow_operations_from_profiler(
                    db_name, last_ts=last_collection_timestamp
                ):
                    slow_operation_events.append(self._create_slow_operation_event(slow_operation))

                    self._collect_slow_operation_explain_plan(slow_operation, db_name)

                    if len(slow_operation_events) >= self._max_operations:
                        break
            else:
                slow_operations_from_logs.add(db_name)

        if slow_operations_from_logs and len(slow_operation_events) < self._max_operations:
            for slow_operation in self._collect_slow_operations_from_logs(
                slow_operations_from_logs, last_ts=last_collection_timestamp
            ):
                slow_operation_events.append(self._create_slow_operation_event(slow_operation))

                self._collect_slow_operation_explain_plan(slow_operation, slow_operation["dbname"])

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
        try:
            if db_name in self._database_profiling_levels:
                return self._database_profiling_levels[db_name] > 0

            profiling_level = self._check.api_client.get_profiling_level(db_name)
            level = profiling_level.get("was", 0)  # profiling by default is disabled
            slowms = profiling_level.get("slowms", 100)  # slowms threshold is 100ms by default
            tags = self._check._get_tags(include_internal_resource_tags=True)
            tags.append("db:%s" % db_name)
            # Emit the profiling level and slowms as raw metrics
            # raw ensures that level = 0 is also emitted
            self._check.gauge('mongodb.profiling.level', level, tags=tags, raw=True)
            self._check.gauge('mongodb.profiling.slowms', slowms, tags=tags, raw=True)
            # Cache the profiling level
            self._database_profiling_levels[db_name] = level
            return level > 0
        except OperationFailure:
            # If the command fails, we assume profiling is not enabled
            self._database_profiling_levels[db_name] = 0
            return False

    def _collect_slow_operations_from_profiler(self, db_name, last_ts):
        profiling_data = self._check.api_client.get_profiling_data(db_name, datetime.fromtimestamp(last_ts))

        for profile in profiling_data:
            if 'command' not in profile:
                continue
            profile["ts"] = profile["ts"].timestamp()  # convert datetime to timestamp
            yield self._obfuscate_slow_operation(profile, db_name)

    def _collect_slow_operations_from_logs(self, db_names, last_ts):
        self._check.log.debug(
            "Collecting slow operations from logs for databases %s with lookback ts %s", db_names, last_ts
        )
        logs = self._check.api_client.get_log_data()
        log_entries = logs.get("log", [])
        self._check.log.debug("Found %d log entries", len(log_entries))
        start_index = self._binary_search(log_entries, last_ts)
        self._check.log.debug("Starting log search from index: %d", start_index)
        for i in range(start_index, len(log_entries)):
            parsed_log = log_entries[i]
            if isinstance(parsed_log, str):
                try:
                    parsed_log = json_util.loads(parsed_log, json_options=self._log_json_opts)
                except Exception as e:
                    self._check.log.error("Failed to parse log line: %s", e)
                    continue
            log_msg = parsed_log.get("msg", "")
            if log_msg.lower() == 'slow query':
                ts = parsed_log["t"].timestamp()
                if ts <= last_ts:
                    # This check is still needed when binary search fails to parse a log line
                    # we need to performance linear search for the rest of the logs
                    continue
                log_attr = parsed_log.get("attr")
                if not log_attr or "command" not in log_attr:
                    continue
                db_name = self._get_db_name(log_attr["command"], log_attr.get("ns"))
                if db_name not in db_names:
                    continue
                log_attr["ts"] = ts
                yield self._obfuscate_slow_operation(log_attr, db_name)
            else:
                self._check.log.debug("Skipping non-slow query log entry: %s", log_msg)

    def _collect_slow_operation_explain_plan(self, slow_operation, dbname):
        try:
            if should_explain_operation(
                namespace=slow_operation.get("ns"),
                op=self._get_slow_operation_op_type(slow_operation),
                command=slow_operation["command"],
                explain_plan_rate_limiter=self._explained_operations_ratelimiter,
                explain_plan_cache_key=(dbname, slow_operation["query_signature"]),
            ):
                if slow_operation.get("execStats"):
                    # execStats is available with profiling, so we just need to format it
                    explain_plan = format_explain_plan({"executionStats": slow_operation.get("execStats")})
                else:
                    # explain the slow operation from the logs
                    explain_plan = get_explain_plan(
                        self._check.api_client, slow_operation.get("op"), slow_operation["command"], dbname
                    )

                explain_plan_payload = self._create_slow_operation_explain_plan_payload(slow_operation, explain_plan)
                self._check.database_monitoring_query_sample(json_util.dumps(explain_plan_payload))
        except Exception as e:
            # Log the error and continue
            # Failures to collect explain plans should not prevent the slow operation from being sent
            self._check.log.error("Failed to collect explain plan for slow operation: %s", e)

    def _obfuscate_slow_operation(self, slow_operation, db_name):
        obfuscated_command = obfuscate_command(slow_operation["command"])
        query_signature = compute_exec_plan_signature(obfuscated_command)
        slow_operation['dbname'] = db_name
        slow_operation['obfuscated_command'] = obfuscated_command
        slow_operation['query_signature'] = query_signature

        originating_command = slow_operation.get('originatingCommand')
        if originating_command:
            slow_operation['originatingCommandComment'] = originating_command.get('comment')
            slow_operation['originatingCommand'] = obfuscate_command(originating_command)

        return slow_operation

    def _get_db_name(self, command, ns):
        return command.get('$db') or get_db_from_namespace(ns)

    def _binary_search(self, logs, ts):
        # Binary search to find the index of the first log line with timestamp >= ts
        # In case of failure to parse a log line, we skip binary search and linearly search the rest of the logs
        left, right = 0, len(logs) - 1
        while left <= right:
            mid = (left + right) // 2
            try:
                parsed_log = json_util.loads(logs[mid], json_options=self._log_json_opts)
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
            "op": self._get_slow_operation_op_type(slow_operation),
            "ns": slow_operation.get("ns"),
            "plan_summary": slow_operation.get("planSummary"),
            "query_signature": slow_operation["query_signature"],
            "user": slow_operation.get("user"),  # only available with profiling
            "application": slow_operation.get("appName"),  # only available with profiling
            "statement": slow_operation["obfuscated_command"],
            "query_hash": slow_operation.get("queryHash") or slow_operation.get("planCacheShapeHash"),
            "plan_cache_key": slow_operation.get("planCacheKey"),  # only available with profiling
            "query_framework": slow_operation.get("queryFramework"),
            "comment": slow_operation["command"].get("comment"),
            # metrics
            # mills from profiler, durationMillis from logs
            "mills": slow_operation.get("millis", slow_operation.get("durationMillis", 0)),
            # numYield from profiler, numYields from logs
            "num_yields": slow_operation.get("numYield", slow_operation.get("numYields", 0)),
            # responseLength from profiler, reslen from logs
            "response_length": slow_operation.get("responseLength", slow_operation.get("reslen", 0)),
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
            "cursor_exhausted": slow_operation.get("cursorExhausted"),
            "upsert": slow_operation.get("upsert"),  # only available with profiling
            "has_sort_stage": slow_operation.get("hasSortStage"),  # only available with profiling
            "used_disk": slow_operation.get("usedDisk"),
            "from_multi_planner": slow_operation.get("fromMultiPlanner"),  # only available with profiling
            "replanned": slow_operation.get("replanned"),  # only available with profiling
            "replan_reason": slow_operation.get("replanReason"),  # only available with profiling
            "client": self._get_slow_operation_client(slow_operation),
            "cursor": self._get_slow_operation_cursor(slow_operation),
            "lock_stats": self._get_slow_operation_lock_stats(slow_operation),
            "flow_control_stats": self._get_slow_operation_flow_control_stats(slow_operation),
            # MongoDB 5.0+ specific fields
            "resolved_views": self._get_slow_operation_resolved_views(slow_operation),
            # MongoDB 8.0+ specific fields
            "working_millis": slow_operation.get("workingMillis"),  # the amount of time spends working on the operation
            "queues": self._get_slow_operation_queues(slow_operation),
        }

        return self._sanitize_event(event)

    def _create_slow_operation_explain_plan_payload(self, slow_operation: dict, explain_plan: dict):
        '''
        Create a slow operation explain plan payload
        '''
        event = {
            "host": self._check._resolved_hostname,
            "dbm_type": "plan",
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongo",
            "ddtags": ",".join(self._check._get_tags()),
            "cloud_metadata": self._check._config.cloud_metadata,
            "timestamp": slow_operation["ts"] * 1000,
            "service": self._check._config.service,
            "network": {
                "client": self._get_slow_operation_client(slow_operation),
            },
            "db": {
                "instance": slow_operation["dbname"],
                "plan": explain_plan,
                "query_signature": slow_operation["query_signature"],
                "application": slow_operation.get("appName"),
                "user": slow_operation.get("user"),
                "statement": slow_operation["obfuscated_command"],
                "operation_metadata": {
                    "op": slow_operation.get("op") or slow_operation.get("type"),
                    "ns": slow_operation.get("ns"),
                    "collection": get_command_collection(slow_operation["command"], slow_operation.get("ns")),
                    "comment": slow_operation["command"].get("comment"),
                },
                "truncated": get_command_truncation_state(slow_operation["command"]),
                "source": "slow_query",
            },
            "mongodb": self._sanitize_event(
                {
                    "op": self._get_slow_operation_op_type(slow_operation),
                    "ns": slow_operation.get("ns"),
                    "plan_summary": slow_operation.get("planSummary"),
                    "microsecs_running": slow_operation.get("millis", slow_operation.get("durationMillis", 0)) * 1000,
                    "num_yields": slow_operation.get("numYield", slow_operation.get("numYields", 0)),
                    "write_conflicts": slow_operation.get("writeConflicts"),
                    "lock_stats": self._get_slow_operation_lock_stats(slow_operation),
                    "flow_control_stats": self._get_slow_operation_flow_control_stats(slow_operation),
                    "cursor": self._get_slow_operation_cursor(slow_operation),
                }
            ),
        }
        return self._sanitize_event(event)

    def _get_slow_operation_op_type(self, slow_operation):
        return slow_operation.get("op") or slow_operation.get("type")

    def _get_slow_operation_client(self, slow_operation):
        calling_client_hostname = slow_operation.get("client") or slow_operation.get("remote")
        if calling_client_hostname:
            return {"hostname": calling_client_hostname}
        return None

    def _get_slow_operation_cursor(self, slow_operation):
        cursor_id = slow_operation.get("cursorid")
        originating_command = slow_operation.get("originatingCommand")
        if cursor_id or originating_command:
            return {
                "cursor_id": cursor_id,
                "originating_command": originating_command,
                "comment": slow_operation.get("originatingCommandComment"),
            }
        return None

    def _get_slow_operation_lock_stats(self, slow_operation):
        lock_stats = slow_operation.get("locks")
        if lock_stats:
            return format_key_name(self._check.convert_to_underscore_separated, lock_stats)
        return None

    def _get_slow_operation_flow_control_stats(self, slow_operation):
        flow_control_stats = slow_operation.get("flowControl")
        if flow_control_stats:
            return format_key_name(self._check.convert_to_underscore_separated, flow_control_stats)
        return None

    def _get_slow_operation_queues(self, slow_operation):
        queues = slow_operation.get("queues")
        if queues:
            return format_key_name(self._check.convert_to_underscore_separated, queues)
        return

    def _get_slow_operation_resolved_views(self, slow_operation):
        resolved_views = slow_operation.get("resolvedViews")
        result = []
        if resolved_views:
            for view in resolved_views:
                view.pop("resolvedPipeline", None)
                result.append(format_key_name(self._check.convert_to_underscore_separated, view))
        return result or None

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
            "ddtags": self._check._get_tags(),
            "cloud_metadata": self._check._config.cloud_metadata,
            "timestamp": time.time() * 1000,
            "service": self._check._config.service,
            "mongodb_slow_queries": slow_operation_events,
        }
        self._check.database_monitoring_query_activity(json_util.dumps(payload))
