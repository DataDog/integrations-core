# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from typing import Optional, Tuple

from bson import json_util

from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.sql import compute_exec_plan_signature
from datadog_checks.base.utils.db.utils import RateLimitingTTLCache

MONGODB_SYSTEM_DATABASES = frozenset(["admin", "config", "local"])

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
    ]
)


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
) -> bool:
    if not op or op == "none":
        # Skip operations that are not queries
        return False

    if op in ("insert", "update", "getmore", "killcursors", "remove"):
        # Skip operations that are not queries
        return False

    # if UNEXPLAINABLE_COMMANDS in command, skip
    if any(command.get(key) for key in UNEXPLAINABLE_COMMANDS):
        return False

    db, _ = namespace.split(".", 1)
    if db in MONGODB_SYSTEM_DATABASES:
        return False

    if not explain_plan_rate_limiter.acquire(explain_plan_cache_key):
        # Skip operations that have been explained recently
        return False

    return True


def get_explain_plan(api_client, op: Optional[str], command: dict, dbname: str):
    dbname = command.pop("$db", dbname)
    try:
        for key in EXPLAIN_COMMAND_EXCLUDE_KEYS:
            command.pop(key, None)
        explain_plan = api_client[dbname].command("explain", command, verbosity="executionStats")
        return format_explain_plan(explain_plan)
    except Exception as e:
        return {
            "collection_errors": [
                {
                    "code": str(type(e).__name__),
                    "message": str(e),
                }
            ],
        }


def format_explain_plan(explain_plan: dict) -> dict:
    if not explain_plan:
        return None

    plan = {
        key: value
        for key, value in explain_plan.items()
        if key not in ("serverInfo", "serverParameters", "command", "ok", "$clusterTime", "operationTime")
    }

    return {
        "definition": plan,
        "signature": compute_exec_plan_signature(json_util.dumps(plan)),
    }


def get_command_truncation_state(command: dict) -> Optional[str]:
    if not command:
        return None
    return "truncated" if command.get("$truncated") else "not_truncated"


def get_command_collection(command: dict, ns: str) -> Optional[str]:
    if ns:
        _, collection = ns.split(".", 1)
        if collection != '$cmd':
            return collection

    # If the collection name parsed from namespace is $cmd
    # we try to look for the collection in the command
    for key in COMMAND_COLLECTION_KEY:
        collection = command.get(key)
        if collection and isinstance(collection, str):  # edge case like {"aggregate": 1}
            return collection
    return None
