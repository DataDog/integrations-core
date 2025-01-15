# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_info(check, metric_name, modifiers, global_options):
    """
    https://prometheus.io/docs/concepts/metric_types/#gauge
    https://github.com/OpenObservability/OpenMetrics/blob/master/specification/OpenMetrics.md#gauge-1
    """
    # gauge_method = check.gauge

    def info(metric, sample_data, runtime_data):
        pass

    del check
    del modifiers
    del global_options
    return info
