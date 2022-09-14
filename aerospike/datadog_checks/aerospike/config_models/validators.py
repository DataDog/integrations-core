# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'openmetrics_endpoint' in values and 'metrics' in values:
        # metrics is a legacy parameter and should not be used explicitly in OpenMetricsV2BaseCheck
        raise ValueError(
            "Do not use 'metrics' parameter with 'openmetrics_endpoint'. "
            "Use 'extra_metrics' or 'exclude_metrics*' settings instead."
        )
    return values
