# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re


def deep_compare(obj1, obj2):
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        if set(obj1.keys()) != set(obj2.keys()):
            return False
        return all(deep_compare(obj1[key], obj2[key]) for key in obj1)
    elif isinstance(obj1, list) and isinstance(obj2, list):
        if len(obj1) != len(obj2):
            return False
        return all(any(deep_compare(item1, item2) for item2 in obj2) for item1 in obj1)
    else:
        return obj1 == obj2


def obfuscate_sql_literals(query, options=None):
    """
    Stand-in for the agent SQL obfuscator, whose testing stub leaves literals in place.
    Replaces string and number literals with `?`, and normalizes whitespace unless the
    `obfuscation_mode` option is `obfuscate_only`.
    """
    obfuscated = re.sub(r"'[^']*'|\b\d+\b", '?', query or '')
    if not options or json.loads(options).get('obfuscation_mode') != 'obfuscate_only':
        obfuscated = re.sub(r'\s+', ' ', obfuscated)
    return json.dumps({'query': obfuscated.strip(), 'metadata': {}})


def obfuscate_exec_plan_literals(plan, normalize=False):
    """Stand-in for the agent plan obfuscator, replacing the string literals of a JSON plan with `?`."""
    return re.sub(r"'[^']*'", '?', plan)
