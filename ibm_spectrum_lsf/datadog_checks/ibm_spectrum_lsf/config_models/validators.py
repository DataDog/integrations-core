# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'metric_sources' in values:
        valid_options = [
            'lsclusters',
            'lshosts',
            'bhosts',
            'lsload',
            'bqueues',
            'bslots',
            'bjobs',
            'lsload_gpu',
            'bhosts_gpu',
        ]
        for val in values['metric_sources']:
            if val not in valid_options:
                raise ValueError(f'Invalid metric source: {val}')

    return values
