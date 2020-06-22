import json

import datadog_agent
import mmh3


def compute_sql_signature(query):
    """
    Given a raw SQL query or prepared statement, generate a 64-bit hex signature
    on the normalized query.
    """
    normalized = datadog_agent.obfuscate_sql(query)
    return format(mmh3.hash64(normalized, signed=False)[0], 'x')


def compute_exec_plan_signature(normalized_json_plan):
    """
    Given a normalized json query execution plan, generate its 64-bit hex signature
    """
    with_sorted_keys = json.dumps(json.loads(normalized_json_plan), sort_keys=True)
    return format(mmh3.hash64(with_sorted_keys, signed=False)[0], 'x')
