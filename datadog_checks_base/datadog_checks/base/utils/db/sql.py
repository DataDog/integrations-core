# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import mmh3


def compute_sql_signature(normalized_query):
    """
    Given an already obfuscated & normalized SQL query, generate its 64-bit hex signature.
    """
    if not normalized_query:
        return None
    return format(mmh3.hash64(normalized_query, signed=False)[0], 'x')


def compute_exec_plan_signature(normalized_json_plan):
    """
    Given an already normalized json string query execution plan, generate its 64-bit hex signature.
    """
    if not normalized_json_plan:
        return None
    with_sorted_keys = json.dumps(json.loads(normalized_json_plan), sort_keys=True)
    return format(mmh3.hash64(with_sorted_keys, signed=False)[0], 'x')
