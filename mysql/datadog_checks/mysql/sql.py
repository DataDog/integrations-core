import mmh3

import datadog_agent


def compute_sql_signature(query):
    """
    Given a raw SQL query or prepared statement, generate a 64-bit hex signature
    on the normalized query.
    """
    normalized = datadog_agent.obfuscate_sql(query)
    return format(mmh3.hash64(normalized, signed=False)[0], 'x')
