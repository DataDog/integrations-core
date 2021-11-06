# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'status_url' not in values and 'ping_url' not in values:
        raise ValueError('Field `status_url` or `ping_url` must be set')

    return values
