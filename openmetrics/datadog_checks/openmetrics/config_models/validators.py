# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import PY2


def initialize_instance(values, **kwargs):
    v2_endpoint = values.get('openmetrics_endpoint')
    v1_endpoint = values.get('prometheus_url')
    v1_possible_urls = values.get('possible_prometheus_urls')
    if PY2 and v2_endpoint:
        raise ValueError('`openmetrics_endpoint` cannot be used if the agent is running Python 2')
    if v1_endpoint and v2_endpoint:
        raise ValueError('`prometheus_url` cannot be used along `openmetrics_endpoint`')
    if v1_endpoint and v1_possible_urls:
        raise ValueError('Only one of `prometheus_url` or `possible_prometheus_urls` may be used.')
    if v2_endpoint and v1_possible_urls:
        raise ValueError('`openmetrics_endpoint` cannot be used along `possible_prometheus_urls`')
    if not v1_endpoint and not v2_endpoint:
        if PY2:
            raise ValueError('`prometheus_url` is required')
        elif not v1_possible_urls:
            raise ValueError('`openmetrics_endpoint` is required')
        else:
            raise ValueError('`openmetrics_endpoint` is required')
    return values
