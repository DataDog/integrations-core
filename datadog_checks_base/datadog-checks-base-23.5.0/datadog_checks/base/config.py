# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def is_affirmative(value):
    """
    Attempt to convert different type of values to a meaningful boolean
    """
    # try string cast
    if isinstance(value, str):
        return value.lower() in {'yes', 'true', '1', 'y', 'on'}

    # use object's implementation of `__bool__`, it's faster than cast.
    # None -> False, 0 -> False, 1 -> True, etc.
    return not not value


# Deprecated compatibility layer for Agent 5, will be removed in Agent 8
_is_affirmative = is_affirmative
