# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def initialize_instance(values, **kwargs):
    if not values['use_openmetrics']:
        if 'build_configuration' in values and 'projects' in values:
            raise ValueError('Only one of `projects` or `build_configuration` must be configured, not both.')
        if 'build_configuration' not in values and 'projects' not in values:
            raise ValueError('`projects` must be configured.')
    return values
