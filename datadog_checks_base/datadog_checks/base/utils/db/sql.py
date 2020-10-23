# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mmh3


def compute_sql_signature(normalized_query):
    """
    Given an already obfuscated & normalized SQL query, generate its 64-bit hex signature.
    """
    if not normalized_query:
        return None
    # Note: please be cautious when changing this function as some features rely on this
    # hash matching the APM resource hash generated on our backend.
    return format(mmh3.hash64(normalized_query, signed=False)[0], 'x')
