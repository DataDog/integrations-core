# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Dict  # noqa: F401

from .config import Config  # noqa: F401


def is_resource_included(resource, config):
    # type: (Dict[str, str], Config) -> bool
    # If the resource is in an include filter and not in an exclude filter, return True, otherwise return False.
    for exclude_filter in config.resource_filters['excluded']:
        if exclude_filter.match(resource['type'], resource['name'], resource.get('group')):
            return False

    for include_filter in config.resource_filters['included']:
        if include_filter.match(resource['type'], resource['name'], resource.get('group')):
            return True

    return False
