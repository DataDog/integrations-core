# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


# Here you can include additional config validators or transformers
#
def initialize_instance(values, **kwargs):
    if 'projects' not in values and 'project_groups' not in values and 'spaces' not in values:
        raise ValueError('A configuration for projects, project_groups, or spaces is required for this integration.')
    return values
