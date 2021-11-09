# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'kong_status_url' not in values and 'openmetrics_endpoint' not in values:
        raise ValueError('Field `kong_status_url` or `openmetrics_endpoint` must be set')

    return values
