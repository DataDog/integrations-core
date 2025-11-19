# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import List, Pattern, Tuple  # noqa: F401


def match_any_regex(string, regexes):
    for regex in regexes:
        if regex.match(string):
            return True
    return False


def create_resource_filter(resource_type, property_name, patterns, is_include=True):
    return ResourceFilter(resource_type, property_name, patterns, is_include)


class ResourceFilter:
    """Represents a given resource filter as defined in the conf.yaml file."""

    def __init__(self, resource_type, property_name, patterns, is_include=True):
        # type: (str, str, List[Pattern], bool) -> None
        self.resource_type = resource_type
        self.property_name = property_name
        self.patterns = patterns
        self.is_include = is_include

    def unique_key(self):
        # type: () -> Tuple[str, str, bool]
        """Unique identifier for this given resource filter. To prevent users defining multiple filters that overlap
        each other, there should never be two ResourceFilters with the same unique key."""
        return self.resource_type, self.property_name, self.is_include

    def match(self, resource):
        prop = resource.get(self.property_name, "")
        return match_any_regex(prop, self.patterns)


def is_resource_collected_by_filters(resource, resource_filters):
    if not resource:
        return False
    resource_type = resource.get("resource_type")

    # Limit filters to those for the resource_type of the mor
    resource_filters = [f for f in resource_filters if f.resource_type == resource_type]

    include_filters = [f for f in resource_filters if f.is_include]
    exclude_filters = [f for f in resource_filters if not f.is_include]

    # First check if the resource match any exclude filter, if so do not collect it.
    for resource_filter in exclude_filters:
        if resource_filter.match(resource):
            return False

    # Extra logic to consider that no include filters means "collect everything"
    if not include_filters:
        return True

    # Finally check if the resource match any include filter, if so collect it
    for resource_filter in include_filters:
        if resource_filter.match(resource):
            return True

    # Otherwise, do not collect it
    return False
