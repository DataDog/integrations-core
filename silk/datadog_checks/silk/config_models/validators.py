# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if 'host_address' not in values:
        raise ValueError('host_address is a required parameter.')

    return values
