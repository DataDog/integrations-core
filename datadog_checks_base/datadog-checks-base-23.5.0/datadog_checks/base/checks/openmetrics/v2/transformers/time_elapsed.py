# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .....utils.time import get_timestamp


def get_time_elapsed(check, metric_name, modifiers, global_options):
    """
    This sends the number of seconds elapsed from a time in the past as a `gauge`.
    """
    gauge_method = check.gauge

    def time_elapsed(metric, sample_data, runtime_data):
        for sample, tags, hostname in sample_data:
            gauge_method(metric_name, get_timestamp() - sample.value, tags=tags, hostname=hostname)

    del check
    del modifiers
    del global_options
    return time_elapsed
