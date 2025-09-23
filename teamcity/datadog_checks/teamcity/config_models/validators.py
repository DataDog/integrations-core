# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
def initialize_instance(values):
    if not values.get('use_openmetrics', False):
        if 'build_configuration' in values and 'projects' in values:
            raise ValueError('Only one of `projects` or `build_configuration` may be configured, not both.')
        if 'build_configuration' not in values and 'projects' not in values:
            raise ValueError('One of `projects` or `build_configuration` must be configured.')
    return values
