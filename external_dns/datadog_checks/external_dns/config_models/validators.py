# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if not values.get('prometheus_url') and not values.get('openmetrics_endpoint'):
        raise ValueError('Field `prometheus_url` or `openmetrics_endpoint` must be set')

    return values
