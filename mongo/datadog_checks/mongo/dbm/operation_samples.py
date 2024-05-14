# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from enum import Enum
import json
import time
from datadog_checks.mongo import MongoDb

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


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
    def __init__(self, check: MongoDb):
        self._check = check

    def run(self):
        pass

    def _get_current_op(self):
        with self._check.api_client['admin'].aggregate(
            [{'$currentOp': { 'allUsers': True, 'idleSessions': True }}]
        ) as operations:
            for operation in operations:
                yield operation
    
    def _get_explain_plan(self, command, dbnames):
        if command.get("$db") == "admin":
            # Skip system operations
            self._check.log.debug("Skipping system operation: %s", command)
            return

        dbname = command.pop("$db")
        if not dbname or dbname not in dbnames:
            # Skip operations on databases we don't monitor
            self._check.log.debug("Skipping operation on database %s: %s", dbname, command)
            return
        try:
            explain_plan = self._check.api_client[dbname].command("explain", command)
            return explain_plan
        except Exception as e:
            self._check.log.error("Could not explain command %s: %s", command, e)
            return
            
    def _get_command_metadata(self, command):
        return {
            'dbname': command.get("$db"),
            'collection': command.get("collection"),
            'comment': command.get("comment"),
            'truncated': CommandTruncationState.truncated if command.get("$truncated") else CommandTruncationState.not_truncated,
        }
    
    def _get_operation_metrics(self, operation):
        return {
            'active': operation.get('active', False),
            'desc': operation.get('desc'),
            'opid': operation.get('opid'),
            'ns': operation.get('ns'),
            'planSummary': operation.get('planSummary'),
            'microsecsRunning': operation.get('microsecs_running'),
            # Conflicts
            'prepareReadConflicts': operation.get('prepareReadConflicts', 0),
            'writeConflicts': operation.get('writeConflicts', 0),
            'numYields': operation.get('numYields', 0),
            # Locks
            'waitingForLock': operation.get('waitingForLock', False),
            'locks': operation.get('locks', {}),
            'lockStats': operation.get('lockStats', {}),
            # Flow control
            'waitingForFlowControl': operation.get('waitingForFlowControl', False),
            'flowControlStats': operation.get('flowControlStats', {}),
            # Latches
            'waitingForLatch': operation.get('waitingForLatch', False),
            # Transaction
            'twoPhaseCommitCoordinator': operation.get('twoPhaseCommitCoordinator', {}),
            'transaction': operation.get('transaction', {}),
        }


    def _create_operation_sample_payload(self, operation, operation_metadata, explain_plan):
        event = {
            "host": self._check._resolved_hostname,
            "dbm_type": "plan",
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "mongodb",
            "ddtags": ",".join([]),  # TODO: add check deployment tags
            "timestamp": time.time() * 1000,
            "network": {
                "client": {
                    "hostname": operation.get('client') or operation.get('client_s'),
                }
            },
            "db": {
                "instance": operation_metadata['dbname'],
                "plan": {
                    "definition": explain_plan,
                    # "signature": plan_signature,
                    # "collection_errors": collection_errors,
                },
                # "query_signature": row['query_signature'],
                # "resource_hash": row['query_signature'],
                "application": operation.get('appName', None),
                "user": operation.get('effectiveUsers', {}).get('user', None),
                "statement": json.dumps(operation['command']),
                "metadata": {
                    "operation": operation.get('op'),
                    "shard": operation.get('shard'),
                    "collection": operation_metadata['collection'],
                    "comments": operation_metadata['comment'],
                },
                "query_truncated": operation_metadata['truncated'].value,
            },
            'mongodb': {}
        }
        return event

            
    def _get_operation_samples(self):
        dbnames = set(self._check._get_db_names())
        for operation in self._get_current_op():
            command = operation.get("command")
            if not command:
                self._check.log.debug("Skipping operation without command: %s", operation)
                continue
            operation_metadata = self._get_command_metadata(command)
            explain_plan = self._get_explain_plan(command, dbnames)
            
                
