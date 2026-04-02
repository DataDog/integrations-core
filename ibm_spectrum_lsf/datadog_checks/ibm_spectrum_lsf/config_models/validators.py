# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'metric_sources' in values:
        valid_options = {
            'lsclusters',
            'lshosts',
            'bhosts',
            'lsload',
            'bqueues',
            'bslots',
            'bjobs',
            'bhist',
            'lsload_gpu',
            'bhosts_gpu',
            'badmin_perfmon',
            'bhist_details',
        }
        for val in values['metric_sources']:
            if val not in valid_options:
                raise ValueError(f'Invalid metric source: {val}')

        if 'bhist_details' in values['metric_sources'] and 'bhist' not in values['metric_sources']:
            raise ValueError(
                'bhist_details is dependent on bhist, please enable bhist to collect bhist_details metrics'
            )

    return values
