# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.


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
    return value.lower() in ('yes', 'true', '1')


# Compatibility layer for Agent5
_is_affirmative = is_affirmative
