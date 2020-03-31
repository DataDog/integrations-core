# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import List, Pattern, Tuple

from pyVmomi import vim

from datadog_checks.vsphere.types import InfrastructureData


def make_inventory_path(mor, infrastructure_data):
    # type: (vim.ManagedEntity, InfrastructureData) -> str
    mor_name = infrastructure_data[mor].get('name', '')
    mor_parent = infrastructure_data[mor].get('parent')
    if mor_parent:
        return make_inventory_path(mor_parent, infrastructure_data) + '/' + mor_name
    return ''


def match_any_regex(string, regexes):
    # type: (str, List[Pattern]) -> bool
    for regex in regexes:
        match = regex.match(string)
        if match:
            return True
    return False


class ResourceFilter:
    """Represents a given resource filter as defined in the conf.yaml file."""

    def __init__(self, resource_type, property_name, patterns, is_whitelist=True):
        # type: (str, str, List[Pattern], bool) -> None
        self.resource_type = resource_type
        self.property_name = property_name
        self.patterns = patterns
        self.is_whitelist = is_whitelist

    def unique_key(self):
        # type: () -> Tuple[str, str, bool]
        """Unique identifier for this given resource filter. To prevent users defining multiple filters that overlap
        each other, there should never be two ResourceFilters with the same unique key."""
        return self.resource_type, self.property_name, self.is_whitelist

    def match(self, mor, infrastructure_data, resource_tags):
        # type: (vim.ManagedEntity, InfrastructureData, List[str]) -> bool
        raise NotImplementedError()


class NameFilter(ResourceFilter):
    def match(self, mor, infrastructure_data, resource_tags):
        mor_name = infrastructure_data[mor].get("name", "")
        return match_any_regex(mor_name, self.patterns)


class InventoryPathFilter(ResourceFilter):
    def match(self, mor, infrastructure_data, resource_tags):
        path = make_inventory_path(mor, infrastructure_data)
        return match_any_regex(path, self.patterns)


class TagFilter(ResourceFilter):
    def match(self, mor, infrastructure_data, resource_tags):
        for resource_tag in resource_tags:
            if match_any_regex(resource_tag, self.patterns):
                return True
        return False


class HostnameFilter(ResourceFilter):
    def match(self, mor, infrastructure_data, resource_tags):
        host = infrastructure_data[mor].get("runtime.host")
        if host and host in infrastructure_data:
            hostname = infrastructure_data[host].get("name", "")
            if match_any_regex(hostname, self.patterns):
                return True
        return False


class GuestHostnameFilter(ResourceFilter):
    def match(self, mor, infrastructure_data, resource_tags):
        guest_hostname = infrastructure_data.get(mor, {}).get("guest.hostName", "")
        return match_any_regex(guest_hostname, self.patterns)


FILTER_PROP_TO_FILTER_CLASS = {
    'name': NameFilter,
    'inventory_path': InventoryPathFilter,
    'tag': TagFilter,
    'hostname': HostnameFilter,
    'guest_hostname': GuestHostnameFilter,
}
