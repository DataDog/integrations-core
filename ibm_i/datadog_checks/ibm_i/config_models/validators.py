# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def instance_severity_threshold(value, *, field):
    v = int(value)
    if v < 0 or v > 99:
        raise ValueError("severity threshold must be in the range [0,99]")
    return v


def instance_query_timeout(value, *, field):
    v = int(value)
    return v
