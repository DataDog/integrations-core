# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .....utils.time import get_timestamp


def get_time_elapsed(check, metric_name, modifiers):
    """
    This sends the number of seconds elapsed from a time in the past as a `gauge`.
    """
    gauge_method = check.gauge

    def time_elapsed(value, *, tags=None):
        gauge_method(metric_name, get_timestamp() - value, tags=tags)

    del check
    del modifiers
    return time_elapsed
