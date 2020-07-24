# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from typing import Any, Dict

from .constants import RESOURCE_TYPES


class Config:
    def __init__(self, instance):
        self.tags = instance.get('tags', [])
        self.resource_filters = self.build_resource_filters(instance.get('resource_filters', []))

    @staticmethod
    def build_resource_filters(raw_filters):
        created_filters = {'included': [], 'excluded': []}
        for f in raw_filters:
            included = f.get('type', 'included') == 'included'
            regex = re.compile(f['pattern'])
            if included:
                created_filters['included'].append(
                    ResourceFilter(f['resource'], regex, True, f.get('group'))
                )
            else:
                created_filters['excluded'].append(
                    ResourceFilter(f['resource'], regex, False, f.get('group'))
                )

        return created_filters


class ResourceFilter:
    """Represents a given resource filter as defined in the conf.yaml file."""

    def __init__(self, resource, regex, is_included=True, group=None):
        # type: (str, Pattern, bool, Optional[str]) -> None
        self.resource = RESOURCE_TYPES[resource]['plural'] if RESOURCE_TYPES.get(resource) else resource
        self.regex = regex
        self.is_included = is_included
        self.group = group

    def match(self, resource, name, id, group=None):
        # type: (str, str, str, Optional[str]) -> bool
        return (self.resource == resource and self.regex.match(name) and self.group == group)

    def __str__(self):
        return "{} | {} | {} | {}".format(self.resource, self.regex, self.is_included, self.group)
