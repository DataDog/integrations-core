# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def is_affirmative(value):
    """
    Attempt to convert different type of values to a meaningful boolean
    """
    if value is None:
        return False

    # int or real bool
    if isinstance(value, int):
        return bool(value)

    # try string cast
    return value.lower() in ('yes', 'true', '1', 'y', 'on')


# Compatibility layer for Agent5
_is_affirmative = is_affirmative
