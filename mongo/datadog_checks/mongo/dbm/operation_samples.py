# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import time
from datetime import datetime
from typing import List, Optional, Tuple

from bson import json_util

from datadog_checks.mongo.dbm.utils import format_key_name

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import DBMAsyncJob, RateLimitingTTLCache
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.mongo.common import ReplicaSetDeployment

from .types import (
    OperationActivityEvent,
    OperationSampleActivityRecord,
    OperationSampleClient,
    OperationSampleEvent,
    OperationSampleOperationMetadata,
    OperationSampleOperationStats,
    OperationSampleOperationStatsCursor,
    OperationSamplePlan,
)


class MongoDbExplainExceptionBase(Exception):
    pass


SAMPLE_EXCLUDE_KEYS = {
    "statement",
    "application",
    "dbname",
    "user",
    "client",
}

SYSTEM_DATABASES = {"admin", "config", "local"}

# exclude keys in sampled operation that cause issues with the explain command
COMMAND_EXCLUDE_KEYS = {
    'readConcern',
    'writeConcern',
    'needsMerge',
    'fromMongos',
    'let',  # let set's the CLUSTER_TIME and NOW in mongos
    'mayBypassWriteBlocking',
}


def agent_check_getter(self):
    return self._check


class MongoOperationSamples(DBMAsyncJob):
    def __init__(self, check):
        self._operation_samples_config = check._config.operation_samples
        self._collection_interval = self._operation_samples_config["collection_interval"]

        # _explained_operations_ratelimiter: limit how often we try to re-explain the same query
        self._explained_operations_ratelimiter = RateLimitingTTLCache(
            maxsize=self._operation_samples_config['explained_operations_cache_maxsize'],
            ttl=45 * 60 / self._operation_samples_config['explained_operations_per_hour_per_query'],
        )

        super(MongoOperationSamples, self).__init__(
            check,
            rate_limit=1 / self._collection_interval,
            run_sync=self._operation_samples_config.get("run_sync", False),
            enabled=self._operation_samples_config["enabled"],
            dbms="mongo",
            min_collection_interval=check._config.min_collection_interval,
            job_name="operation-samples",
        )

        self._last_sampled_timestamp = None

    def run_job(self):
        self.collect_operation_samples()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_operation_samples(self):
        if not self._should_collect_operation_samples():
            return
        now = time.time()

        activities = []

        for activity, sample in self._get_operation_samples(
            now, databases_monitored=self._check._database_autodiscovery.databases
        ):
            if sample:
                self._check.log.debug("Sending operation sample: %s", sample)
                self._check.database_monitoring_query_sample(json_util.dumps(sample))
            activities.append(activity)
        activities_payload = self._create_activities_payload(now, activities)
        self._check.log.debug("Sending activities payload: %s", activities_payload)
        self._check.database_monitoring_query_activity(json_util.dumps(activities_payload))

        self._last_sampled_timestamp = now

    def _should_collect_operation_samples(self) -> bool:
        deployment = self._check.deployment_type
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self._check.log.debug("Skipping operation samples collection on arbiter node")
            return False
        return True

    def _get_operation_samples(self, now, databases_monitored: List[str]):
        for operation in self._get_current_op():
            try:
                if not self._should_include_operation(operation, databases_monitored):
                    continue

                command = operation.get("command")
                obfuscated_command = datadog_agent.obfuscate_mongodb_string(json_util.dumps(command))
                query_signature = self._get_query_signature(obfuscated_command)
                operation_metadata = self._get_operation_metadata(operation)

                activity = self._create_activity(
                    now, operation, operation_metadata, obfuscated_command, query_signature
                )

                if not self._should_explain(
                    namespace=operation.get("ns"),
                    op=operation.get("op"),
                    command=command,
                    explain_plan_cache_key=(operation_metadata["dbname"], query_signature),
                ):
                    yield activity, None
                    continue

                explain_plan = self._get_explain_plan(
                    op=operation.get("op"), command=command, dbname=operation_metadata["dbname"]
                )
                sample = self._create_operation_sample_payload(
                    now, operation_metadata, obfuscated_command, query_signature, explain_plan, activity
                )
                yield activity, sample
            except Exception as e:
                self._check.log.error("Unexpected error while collecting operation samples: %s", e)
                continue

    def _get_current_op(self):
        operations = self._check.api_client.current_op()
        for operation in operations:
            self._check.log.debug("Found operation: %s", operation)
            yield operation

    def _should_include_operation(self, operation: dict, databases_monitored: List[str]) -> bool:
        # Skip operations from db that are not configured to be monitored
        namespace = operation.get("ns")
        if not namespace:
            self._check.log.debug("Skipping operation without namespace: %s", operation)
            return False

        db, _ = namespace.split(".", 1)
        if db not in databases_monitored:
            self._check.log.debug("Skipping operation for database %s because it is not configured to be monitored", db)
            return False
        if db == "admin":
            self._check.log.debug("Skipping operation for admin database: %s", operation)
            return False

        # Skip operations without a command
        command = operation.get("command")
        if not command:
            self._check.log.debug("Skipping operation without command: %s", operation)
            return False
        if "hello" in command and operation.get("op") == "command":
            # MongoDB drivers and clients use hello to determine the state of
            # the replica set members and to discover additional members of a replica set.
            self._check.log.debug("Skipping hello operation: %s", operation)
            return False
        if "explain" in command:
            # Skip explain operations as explain cannot explain itself
            self._check.log.debug("Skipping explain operation: %s", operation)
            return False

        # Skip sampled operations that are older than the last sampled timestamp
        current_op_time = operation.get("currentOpTime")
        if not current_op_time:
            self._check.log.debug("Skipping operation without currentOpTime: %s", operation)
            return False

        current_op_time_ts = datetime.strptime(current_op_time, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp()
        if self._last_sampled_timestamp and current_op_time_ts <= self._last_sampled_timestamp:
            self._check.log.debug("Skipping operation older than last sampled timestamp: %s", operation)
            return False

        return True

    def _should_explain(
        self, namespace: str, op: Optional[str], command: dict, explain_plan_cache_key: Tuple[str, str]
    ) -> bool:
        if not op or op == "none":
            # Skip operations that are not queries
            self._check.log.debug("Skipping explain operation without operation type: %s", command)
            return False

        if op in ("insert", "update", "getmore", "killcursors", "remove"):
            # Skip operations that are not queries
            self._check.log.debug("Skipping explain operation type %s: %s", op, command)
            return False

        if "getMore" in command or "insert" in command or "delete" in command or "update" in command:
            # Skip operations as they are not queries
            self._check.log.debug("Skipping operations that are not queries: %s", op, command)
            return False

        db, _ = namespace.split(".", 1)
        if db in SYSTEM_DATABASES:
            self._check.log.debug("Skipping operation for system database %s", db)
            return False

        if not self._explained_operations_ratelimiter.acquire(explain_plan_cache_key):
            # Skip operations that have been explained recently
            self._check.log.debug("Skipping explain operation that was recently explained: %s", command)
            return False

        return True

    def _get_explain_plan(self, op: Optional[str], command: dict, dbname: str) -> OperationSamplePlan:
        dbname = command.pop("$db", dbname)
        try:
            for key in COMMAND_EXCLUDE_KEYS:
                command.pop(key, None)
            explain_plan = self._check.api_client[dbname].command("explain", command, verbosity="executionStats")
            explain_plan = self._format_explain_plan(explain_plan)
            return {
                "definition": explain_plan,
                "signature": compute_exec_plan_signature(json_util.dumps(explain_plan)),
            }
        except Exception as e:
            self._check.log.error("Could not explain command %s: %s", command, e)
            return {
                "collection_errors": [
                    {
                        "code": str(type(e).__name__),
                        "message": str(e),
                    }
                ],
            }

    def _format_explain_plan(self, explain_plan: dict) -> dict:
        if not explain_plan:
            return None

        return {
            key: value
            for key, value in explain_plan.items()
            if key not in ("serverInfo", "serverParameters", "command", "ok", "$clusterTime", "operationTime")
        }

    def _get_operation_client(self, operation: dict) -> OperationSampleClient:
        client_metadata = operation.get("clientMetadata", {})

        return {
            "hostname": operation.get("client") or operation.get("client_s"),
            "driver": client_metadata.get("driver"),
            "os": client_metadata.get("os"),
            "platform": client_metadata.get("platform"),
        }

    def _get_operation_user(self, operation: dict) -> Optional[str]:
        effective_users = operation.get("effectiveUsers")
        if not effective_users:
            return None
        return effective_users[0].get("user")

    def _get_command_truncation_state(self, command: dict) -> Optional[str]:
        if not command:
            return None
        return "truncated" if command.get("$truncated") else "not_truncated"

    def _get_command_collection(self, command: dict, collection_from_ns: str) -> Optional[str]:
        if collection_from_ns != '$cmd':
            return collection_from_ns

        # If the collection name parsed from namespace is $cmd
        # we try to look for the collection in the command
        for key in (
            "collection",
            "find",
            "aggregate",
            "update",
            "insert",
            "delete",
            "findAndModify",
            "distinct",
            "count",
        ):
            collection = command.get(key)
            if collection and isinstance(collection, str):  # edge case like {"aggregate": 1}
                return collection

    def _get_operation_metadata(self, operation: dict) -> OperationSampleOperationMetadata:
        namespace = operation.get("ns")
        db, collection = namespace.split(".", 1)
        command = operation.get("command", {})
        return {
            "type": operation.get("type"),
            "op": operation.get("op"),
            "shard": operation.get("shard"),
            "dbname": command.get("$db", db),
            "application": operation.get("appName"),
            "collection": self._get_command_collection(command, collection),
            "comment": command.get("comment"),
            "truncated": self._get_command_truncation_state(command),
            "client": self._get_operation_client(operation),
            "user": self._get_operation_user(operation),
            "ns": namespace,
        }

    def _get_operation_cursor(self, operation: dict) -> Optional[OperationSampleOperationStatsCursor]:
        cursor = operation.get("cursor")
        if not cursor:
            return None

        created_date = cursor.get("createdDate")
        if created_date:
            created_date = created_date.isoformat()
        last_access_date = cursor.get("lastAccessDate")
        if last_access_date:
            last_access_date = last_access_date.isoformat()

        originating_command = cursor.get("originatingCommand")
        if originating_command:
            originating_command = datadog_agent.obfuscate_mongodb_string(json_util.dumps(originating_command))

        return {
            "cursor_id": cursor.get("cursorId"),
            "created_date": created_date,
            "last_access_date": last_access_date,
            "n_docs_returned": cursor.get("nDocsReturned", 0),
            "n_batches_returned": cursor.get("nBatchesReturned", 0),
            "no_cursor_timeout": cursor.get("noCursorTimeout", False),
            "tailable": cursor.get("tailable", False),
            "await_data": cursor.get("awaitData", False),
            "originating_command": originating_command,
            "plan_summary": cursor.get("planSummary"),
            "operation_using_cursor_id": cursor.get("operationUsingCursorId"),
        }

    def _get_operation_stats(self, operation: dict) -> OperationSampleOperationStats:
        return {
            "active": operation.get("active", False),  # bool
            "desc": operation.get("desc"),  # str
            "opid": operation.get("opid"),  # str
            "ns": operation.get("ns"),  # str
            "plan_summary": operation.get("planSummary"),  # str
            "current_op_time": operation.get("currentOpTime"),  # str  start time of the operation
            "microsecs_running": operation.get("microsecs_running"),  # int
            "transaction_time_open_micros": operation.get("transaction", {}).get("timeOpenMicros"),  # int
            # Conflicts
            "prepare_read_conflicts": operation.get("prepareReadConflicts", 0),  # int
            "write_conflicts": operation.get("writeConflicts", 0),  # int
            "num_yields": operation.get("numYields", 0),  # int
            # Locks
            "waiting_for_lock": operation.get("waitingForLock", False),  # bool
            "locks": format_key_name(self._check.convert_to_underscore_separated, operation.get("locks", {})),  # dict
            "lock_stats": format_key_name(
                self._check.convert_to_underscore_separated, operation.get("lockStats", {})
            ),  # dict
            # Flow control
            "waiting_for_flow_control": operation.get("waitingForFlowControl", False),  # bool
            "flow_control_stats": format_key_name(
                self._check.convert_to_underscore_separated, operation.get("flowControlStats", {})
            ),  # dict
            # Latches
            "waiting_for_latch": format_key_name(
                self._check.convert_to_underscore_separated, operation.get("waitingForLatch", {})
            ),  # dict
            # cursor
            "cursor": self._get_operation_cursor(operation),  # dict
        }

    def _get_query_signature(self, obfuscated_command: str) -> str:
        return compute_exec_plan_signature(obfuscated_command)

    def _create_operation_sample_payload(
        self,
        now: float,
        operation_metadata: OperationSampleOperationMetadata,
        obfuscated_command: str,
        query_signature: str,
        explain_plan: OperationSamplePlan,
        activity: OperationSampleActivityRecord,
    ) -> OperationSampleEvent:
        event = {
            "host": self._check._resolved_hostname,
            "dbm_type": "plan",
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongo",
            "ddtags": ",".join(self._check._get_tags(include_deployment_tags=True)),
            "timestamp": now * 1000,
            "network": {
                "client": operation_metadata["client"],
            },
            "db": {
                "instance": operation_metadata["dbname"],
                "plan": explain_plan,
                "query_signature": query_signature,
                "application": operation_metadata["application"],
                "user": operation_metadata["user"],
                "statement": obfuscated_command,
                "operation_metadata": {
                    "op": operation_metadata["op"],
                    "shard": operation_metadata["shard"],
                    "collection": operation_metadata["collection"],
                    "comment": operation_metadata["comment"],
                    "ns": operation_metadata["ns"],
                },
                "query_truncated": operation_metadata["truncated"],
            },
            "mongodb": {key: value for key, value in activity.items() if key not in SAMPLE_EXCLUDE_KEYS},
        }
        return event

    def _create_activity(
        self,
        now: float,
        operation: dict,
        operation_metadata: OperationSampleOperationMetadata,
        obfuscated_command: str,
        query_signature: str,
    ) -> Optional[OperationSampleActivityRecord]:
        activity = (
            {
                "now": now,
                "query_signature": query_signature,
                "statement": obfuscated_command,
            }
            | self._get_operation_stats(operation)
            | operation_metadata
        )

        return activity

    def _create_activities_payload(
        self, now: float, activities: List[OperationSampleActivityRecord]
    ) -> OperationActivityEvent:
        return {
            "host": self._check._resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongo",
            "dbm_type": "activity",
            "collection_interval": self._collection_interval,
            "ddtags": self._check._get_tags(include_deployment_tags=True),
            "timestamp": now * 1000,
            "mongodb_activity": activities,
        }
