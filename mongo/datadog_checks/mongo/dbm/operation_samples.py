# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from bson import json_util
from collections import defaultdict
from enum import Enum
import time

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.sql import compute_exec_plan_signature


class MongoDbExplainExceptionBase(Exception):
    pass


class CommandTruncationState(Enum):
    """
    Denotes the various possible states of an operation command truncation
    """

    truncated = 'truncated'
    not_truncated = 'not_truncated'
    unknown = 'unknown'


class MongoOperationSamples(object):
    def __init__(self, check):
        self._check = check
        self._last_collection_time = None

    @property
    def enabled(self):
        return self._check._config.operation_samples['enabled']

    @property
    def collection_interval(self):
        return self._check._config.operation_samples['collection_interval']

    def run(self):
        if not self.enabled:
            self._check.log.debug("Operation samples are disabled")
            return
        
        now = time.time()
        
        if not self._last_collection_time is None and now - self._last_collection_time < self.collection_interval:
            self._check.log.debug("Operation samples collection interval has not passed")
            return

        active_connections = defaultdict(int)
        activities = []

        for sample in self._get_operation_samples(now, active_connections, activities):
            self._check.log.debug("Sending operation sample: %s", sample)

        activities_payload = self._create_activities_payload(now, activities, active_connections)
        self._check.log.debug("Sending activities payload: %s", activities_payload)

        self._last_collection_time = now

    def _get_current_op(self):
        with self._check.api_client['admin'].aggregate(
            [{'$currentOp': { 'allUsers': True, 'idleSessions': True }}]
        ) as operations:
            for operation in operations:
                yield operation
    
    def _get_explain_plan(self, command):
        if command.get("$db") == "admin":
            # Skip system operations
            self._check.log.debug("Skipping system operation: %s", command)
            return

        dbname = command.pop("$db")
        try:
            explain_plan = self._check.api_client[dbname].command("explain", command)
            explain_plan.pop('command')  # Remove the original command from the explain plan
            return {
                "definition": explain_plan,
                "query_hash": explain_plan.get('queryPlanner', {}).get('queryHash'),
                'plan_cache_key': explain_plan.get('queryPlanner', {}).get('planCacheKey'),
                "signature": compute_exec_plan_signature(json_util.dumps(explain_plan)),
            },
        except Exception as e:
            self._check.log.error("Could not explain command %s: %s", command, e)
            return {
                "collection_errors": [str(e)],
            }
            
    def _get_command_collection(self, command):
        for key in ('collection', 'find', 'aggregate', 'update', 'insert', 'delete', 'findAndModify'):
            collection = command.get(key)
            if collection:
                return collection
            
    def _get_operation_client(self, operation):
        return {
            'hostname': operation.get('client') or operation.get('client_s'),
        }
    
    def _get_operation_user(self, operation):
        effective_users = operation.get('effectiveUsers')
        if not effective_users:
            return None
        return effective_users[0].get('user')

    def _get_operation_metadata(self, operation):
        command = operation.get('command', {})
        return {
            "type": operation.get('type'),
            "operation": operation.get('op'),
            "shard": operation.get('shard'),
            'dbname': command.get("$db"),
            "application": operation.get('appName'),
            'collection': self._get_command_collection(command),
            'comments': [command.get("comment")],
            'truncated': CommandTruncationState.truncated if command.get("$truncated") else CommandTruncationState.not_truncated,
            "client": self._get_operation_client(operation),
            "user": self._get_operation_user(operation),
        }
        
    def _get_operation_stats(self, operation):
        return {
            'active': operation.get('active', False),  # bool
            'desc': operation.get('desc'),  # str
            'opid': operation.get('opid'),  # str
            'ns': operation.get('ns'),  # str
            'plan_summary': operation.get('planSummary'),  # str
            'microsecs_running': operation.get('microsecs_running'),  # int
            # Conflicts
            'prepare_read_conflicts': operation.get('prepareReadConflicts', 0),  # int
            'write_conflicts': operation.get('writeConflicts', 0),  # int
            'num_yields': operation.get('numYields', 0),  # int
            # Locks
            'waiting_for_lock': operation.get('waitingForLock', False),  # bool
            'locks': self._format_key_name(operation.get('locks', {})),  # dict
            'lock_stats': self._format_key_name(operation.get('lockStats', {})),  # dict
            # Flow control
            'waiting_for_flow_control': operation.get('waitingForFlowControl', False),  # bool
            'flow_control_stats': self._format_key_name(operation.get('flowControlStats', {})),  # dict
            # Latches
            'waiting_for_latch': operation.get('waitingForLatch', False),  # bool
        }

    def _format_key_name(self, metric_dict):
        # convert camelCase to snake_case
        formatted = {}
        for key, value in metric_dict.items():
            key = self._check.convert_to_underscore_separated(key)
            if isinstance(value, dict):
                formatted[key] = self._format_key_name(value)
            else:
                formatted[key] = value
        return formatted

    def _get_query_signature(self, command):
        obfuscated_command = datadog_agent.obfuscate_mongodb_string(json_util.dumps(command))
        return compute_exec_plan_signature(obfuscated_command)

    def _create_operation_sample_payload(self, operation, operation_metadata, query_signature, explain_plan):
        event = {
            "host": self._check._resolved_hostname,
            "dbm_type": "plan",
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongodb",
            "ddtags": ",".join(self._check._get_tags(include_deployment_tags=True)),
            "timestamp": time.time() * 1000,
            "network": {
                "client": operation_metadata['client'],
            },
            "db": {
                "instance": operation_metadata['dbname'],
                "plan": explain_plan,
                "query_signature": query_signature,
                "resource_hash": query_signature,
                "application": operation_metadata['application'],
                "user": operation_metadata['user'],
                "statement": json_util.dumps(operation['command']),
                "metadata": {
                    "operation": operation_metadata['operation'],
                    "shard": operation_metadata['shard'],
                    "collection": operation_metadata['collection'],
                    "comments": operation_metadata['comments'],
                },
                "query_truncated": operation_metadata['truncated'].value,
            },
            'mongodb': self._get_operation_stats(operation),
        }
        return event
            
    def _get_operation_samples(self, now, active_connections, activities):
        for operation in self._get_current_op():
            command = operation.get("command")
            if not command:
                self._check.log.debug("Skipping operation without command: %s", operation)
                continue

            query_signature = self._get_query_signature(command)
            operation_metadata = self._get_operation_metadata(command)

            self._record_active_connection(operation, operation_metadata, active_connections)
            self._record_activity(now, operation, operation_metadata, query_signature, activities)

            explain_plan = self._get_explain_plan(command)
            yield self._create_operation_sample_payload(operation, operation_metadata, query_signature, explain_plan)

    def _record_active_connection(self, operation, operation_metadata, active_connections):
        if not operation.get('active'):
            return
        key = (
            operation_metadata['application'],
            operation_metadata['dbname'],
            operation.get('type'),
            operation_metadata['user']
        )
        active_connections[key] += 1

    def _record_activity(self, now, operation, operation_metadata, query_signature, activities):
        if not operation.get('active'):
            return

        activity = {
            'now': now,
            'query_signature': query_signature,
        } | self._get_operation_stats(operation) | operation_metadata

        activities.append(activity)

    def _create_activities_payload(self, now, activities, active_connections):
        return {
            "host": self._check._resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongodb",
            "dbm_type": "activity",
            "collection_interval": self.collection_interval,
            "ddtags": ",".join(self._check._get_tags(include_deployment_tags=True)),
            "timestamp": now * 1000,
            "mongodb_activity": activities,
            "mongodb_connections": [
                {
                    'application': app,
                    'dbname': dbname,
                    'type': type,
                    'user': user,
                    'count': count,
                }
                for (app, dbname, type, user), count in active_connections.items()
            ],
        }
