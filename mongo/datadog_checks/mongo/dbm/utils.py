# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from typing import Optional, Tuple

from bson import json_util, regex
from pymongo.errors import ExecutionTimeout, NetworkTimeout

from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import RateLimitingTTLCache
from datadog_checks.mongo.common import MONGODB_SYSTEM_DATABASES

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


# exclude keys in sampled operation that cause issues with the explain command
EXPLAIN_COMMAND_EXCLUDE_KEYS = frozenset(
    [
        'readConcern',
        'writeConcern',
        'needsMerge',
        'fromMongos',
        'let',  # let set's the CLUSTER_TIME and NOW in mongos
        'mayBypassWriteBlocking',
    ]
)

COMMAND_COLLECTION_KEY = frozenset(
    [
        "collection",
        "find",
        "aggregate",
        "update",
        "insert",
        "delete",
        "findAndModify",
        "distinct",
        "count",
    ]
)

UNEXPLAINABLE_COMMANDS = frozenset(
    [
        "getMore",
        "insert",
        "update",
        "delete",
        "explain",
        "profile",  # command to get profile level
        "listCollections",
        "listDatabases",
        'dbStats',
        'createIndexes',
        'shardCollection',
        'serverStatus',
    ]
)

UNEXPLAINABLE_PIPELINE_STAGES = frozenset(
    [
        "$collStats",
        "$currentOp",
        "$indexStats",
        "$listSearchIndexes",
        "$sample",
        "$shardedDataDistribution",
        "$mergeCursors",
    ]
)

COMMAND_KEYS_TO_REMOVE = frozenset(["comment", "lsid", "$clusterTime"])

EXPLAIN_PLAN_KEYS_TO_REMOVE = frozenset(
    [
        "serverInfo",
        "serverParameters",
        "command",
        "ok",
        "$clusterTime",
        "operationTime",
        "$configServerState",
        "lastCommittedOpTime",
        "$gleStats",
    ]
)

log = get_check_logger()


def format_key_name(formatter, metric_dict: dict) -> dict:
    # convert camelCase to snake_case
    formatted = {}
    for key, value in metric_dict.items():
        formatted_key = to_native_string(formatter(key))
        if formatted_key in metric_dict:
            # If the formatted_key already exists (conflict), use the original key
            formatted_key = key
        if isinstance(value, dict):
            formatted[formatted_key] = format_key_name(formatter, value)
        else:
            formatted[formatted_key] = value
    return formatted


def should_explain_operation(
    namespace: str,
    op: Optional[str],
    command: dict,
    explain_plan_rate_limiter: RateLimitingTTLCache,
    explain_plan_cache_key: Tuple[str, str],
    verbosity: str = 'queryPlanner',
) -> bool:
    if verbosity == "disabled":
        return False
    if not op or op == "none":
        # Skip operations that are not queries
        return False

    if op in ("insert", "update", "getmore", "killcursors", "remove"):
        # Skip operations that are not queries
        return False

    # if UNEXPLAINABLE_COMMANDS in command, skip
    if any(command.get(key) for key in UNEXPLAINABLE_COMMANDS):
        return False

    # if UNEXPLAINABLE_PIPELINE_STAGES in command pipeline stages, skip
    if pipeline := command.get("pipeline"):
        stages = [list(stage.keys())[0] for stage in pipeline if isinstance(stage, dict)]
        if any(stage in UNEXPLAINABLE_PIPELINE_STAGES for stage in stages):
            return False

    if namespace:
        # namespace is in the form of db.collection
        # however, some database level commands in earlier versions of MongoDB <= 5.0
        # do not have a collection name in the namespace
        # e.g. "admin.$cmd" vs. "admin"
        db = get_db_from_namespace(namespace)
        if db in MONGODB_SYSTEM_DATABASES:
            return False

        if not explain_plan_rate_limiter.acquire(explain_plan_cache_key):
            # Skip operations that have been explained recently
            return False
    else:
        return False

    return True


def get_explain_plan(
    api_client, command: dict, dbname: str, op_duration: int, cursor_timeout: int, verbosity: str = 'queryPlanner'
) -> dict:
    if verbosity != "queryPlanner" and op_duration >= cursor_timeout:
        # If the operation duration exceeds the cursor timeout,
        # explain with non-queryPlanner verbosity will likely timeout
        # so we log a warning and fallback to queryPlanner
        log.warning(
            "Operation took %s seconds to execute, which exceeds the cursor timeout of %s seconds. "
            "Falling back to queryPlanner verbosity for the explain command.",
            op_duration,
            cursor_timeout,
        )
        verbosity = "queryPlanner"
    dbname = command.pop("$db", dbname)
    try:
        for key in EXPLAIN_COMMAND_EXCLUDE_KEYS:
            command.pop(key, None)
        try:
            explain_plan = api_client.explain_command(dbname, command, verbosity)
            return format_explain_plan(explain_plan)
        except (ExecutionTimeout, NetworkTimeout) as e:
            # If the operation times out, we try one more time with a different verbosity
            if verbosity != "queryPlanner":
                log.warning("Explaining command timed out with verbosity %s, retrying with queryPlanner", verbosity)
                verbosity = "queryPlanner"
                explain_plan = api_client.explain_command(dbname, command, verbosity)
                return format_explain_plan(explain_plan)
            raise e
    except Exception as e:
        return {
            "collection_errors": [
                {
                    "code": str(type(e).__name__),
                    "message": str(e),
                    "strategy": verbosity,
                }
            ],
        }


def format_explain_plan(explain_plan: dict) -> dict:
    if not explain_plan:
        return None

    plan = {key: value for key, value in explain_plan.items() if key not in EXPLAIN_PLAN_KEYS_TO_REMOVE}

    obfuscated_plan = obfuscate_explain_plan(plan)

    return {
        "definition": obfuscated_plan,
        "signature": compute_exec_plan_signature(json_util.dumps(obfuscated_plan)),
    }


def get_command_truncation_state(command: dict) -> Optional[str]:
    if not command:
        return None
    return "truncated" if command.get("$truncated") else "not_truncated"


def get_command_collection(command: dict, ns: str) -> Optional[str]:
    if ns:
        collection = get_collection_from_namespace(ns)
        if collection != '$cmd':
            return collection

    # If the collection name parsed from namespace is $cmd
    # we try to look for the collection in the command
    for key in COMMAND_COLLECTION_KEY:
        collection = command.get(key)
        if collection and isinstance(collection, str):  # edge case like {"aggregate": 1}
            return collection
    return None


def obfuscate_command(command: dict):
    # Obfuscate the command to remove sensitive information
    # Remove the following keys from the command before obfuscating
    # - comment: The comment field should not contribute to the query signature
    # - lsid: The lsid field is a unique identifier for the session
    # - $clusterTime: The $clusterTime field is a logical time used for ordering of operations
    obfuscated_command = command.copy()
    for key in COMMAND_KEYS_TO_REMOVE:
        obfuscated_command.pop(key, None)
    return datadog_agent.obfuscate_mongodb_string(json_util.dumps(obfuscated_command))


def obfuscate_explain_plan(plan):
    if isinstance(plan, dict):
        obfuscated_plan = {}
        for key, value in plan.items():
            if key in ["filter", "parsedQuery", "indexBounds"]:
                obfuscated_plan[key] = obfuscate_literals(value)
            else:
                obfuscated_plan[key] = obfuscate_explain_plan(value)
        return obfuscated_plan
    elif isinstance(plan, list):
        return [obfuscate_explain_plan(item) for item in plan]
    else:
        return plan


def obfuscate_literals(value):
    if isinstance(value, dict):
        return {k: obfuscate_literals(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [obfuscate_literals(v) for v in value]
    elif isinstance(value, (str, int, float, bool)):
        return "?"
    elif isinstance(value, regex.Regex):
        return regex.Regex("?", value.flags)
    else:
        return value


def get_db_from_namespace(namespace: str) -> Optional[str]:
    if not namespace:
        return None
    return namespace.split(".", 1)[0]


def get_collection_from_namespace(namespace: str) -> Optional[str]:
    if not namespace:
        return None
    splitted_ns = namespace.split(".", 1)
    return splitted_ns[1] if len(splitted_ns) > 1 else None
