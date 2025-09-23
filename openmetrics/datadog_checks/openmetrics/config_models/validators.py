# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    v2_endpoint = values.get('openmetrics_endpoint')
    v1_endpoint = values.get('prometheus_url')
    if v1_endpoint and v2_endpoint:
        raise ValueError('`prometheus_url` cannot be used along `openmetrics_endpoint`')
    if not v1_endpoint and not v2_endpoint:
        raise ValueError('`openmetrics_endpoint` is required')
    return values
