# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if values.get('use_prometheus'):
        if 'prometheus_url' not in values:
            raise ValueError('Field `prometheus_url` is required when `use_prometheus` is enabled')
    elif 'url' not in values:
        raise ValueError('Field `url` is required when `use_prometheus` is disabled')

    return values
