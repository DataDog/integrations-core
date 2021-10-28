# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_rate(check, metric_name, modifiers, global_options):
    """
    Send with the `AgentCheck.rate` method.
    """
    rate_method = check.rate

    def rate(metric, sample_data, runtime_data):
        for sample, tags, hostname in sample_data:
            rate_method(metric_name, sample.value, tags=tags, hostname=hostname)

    del check
    del modifiers
    del global_options
    return rate
