# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import List, Pattern, Tuple  # noqa: F401


def match_any_regex(string, regexes):
    for regex in regexes:
        if regex.match(string):
            return True
    return False


def create_resource_filter(resource_type, property_name, patterns, is_include=True):
    FilterClass = FILTER_PROP_TO_FILTER_CLASS[property_name]
    filter_instance = FilterClass(resource_type, property_name, patterns, is_include)
    return filter_instance


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


class NameFilter(ResourceFilter):
    def match(self, mor, resources):
        mor_name = resources[mor].get("name", "")
        return match_any_regex(mor_name, self.patterns)


class HostnameFilter(ResourceFilter):
    def match(self, mor, resources):
        host = resources[mor].get("runtime.host")
        if host and host in resources:
            hostname = resources[host].get("name", "")
            if match_any_regex(hostname, self.patterns):
                return True
        return False


class GuestHostnameFilter(ResourceFilter):
    def match(self, mor, resources):
        guest_hostname = resources.get(mor, {}).get("guest.hostName", "")
        return match_any_regex(guest_hostname, self.patterns)


FILTER_PROP_TO_FILTER_CLASS = {
    'name': NameFilter,
    'hostname': HostnameFilter,
    'guest_hostname': GuestHostnameFilter,
}
