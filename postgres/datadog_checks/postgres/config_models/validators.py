# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if values.get('collect_wal_metrics'):
        if 'data_directory' not in values:
            raise ValueError('Field `data_directory` is required when `collect_wal_metrics` is enabled')

    return values
