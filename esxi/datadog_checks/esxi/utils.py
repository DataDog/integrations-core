# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pyVmomi import vim
from six import iteritems

from datadog_checks.base import to_string

from .constants import METRIC_TO_INSTANCE_TAG_MAPPING, RESOURCE_TYPE_TO_NAME


def get_tags_recursively(mor, infrastructure_data, include_only=None):
    """Go up the resources hierarchy from the given mor. Note that a host running a VM is not considered to be a
    parent of that VM.

    rootFolder(vim.Folder):
    - vm(vim.Folder):
        VM1-1
        VM1-2
    - host(vim.Folder):
        HOST1
        HOST2

    """
    tags = []
    properties = infrastructure_data.get(mor, {})
    entity_name = to_string(properties.get('name', 'unknown'))
    if isinstance(mor, vim.HostSystem):
        tags.append('esxi_host:{}'.format(entity_name))
    elif isinstance(mor, vim.Folder):
        if isinstance(mor, vim.StoragePod):
            tags.append('esxi_datastore_cluster:{}'.format(entity_name))
        else:
            tags.append('esxi_folder:{}'.format(entity_name))
    elif isinstance(mor, vim.ComputeResource):
        if isinstance(mor, vim.ClusterComputeResource):
            tags.append('esxi_cluster:{}'.format(entity_name))
        tags.append('esxi_compute:{}'.format(entity_name))
    elif isinstance(mor, vim.Datacenter):
        tags.append('esxi_datacenter:{}'.format(entity_name))
    elif isinstance(mor, vim.Datastore):
        tags.append('esxi_datastore:{}'.format(entity_name))

    parent = infrastructure_data.get(mor, {}).get('parent')
    if parent is not None:
        tags.extend(get_tags_recursively(parent, infrastructure_data))
    if not include_only:
        return tags
    filtered_tags = []
    for tag in tags:
        for prefix in include_only:
            if not tag.startswith(prefix + ":"):
                continue
            filtered_tags.append(tag)
    return filtered_tags


def match_any_regex(string, regexes):
    for regex in regexes:
        if regex.match(string):
            return True
    return False


def should_collect_per_instance_values(collect_per_instance_filters, metric_name, resource_type):
    filters = collect_per_instance_filters.get(RESOURCE_TYPE_TO_NAME[resource_type], [])
    metric_matched = match_any_regex(metric_name, filters)
    return metric_matched


def get_mapped_instance_tag(metric_name):
    """
    When collecting per-instance metric, the `instance` tag can mean a lot of different things. The meaning of the
    tag cannot be guessed by looking at the api results and has to be inferred using documentation or experience.
    This method acts as a utility to map a metric_name to the meaning of its instance tag.
    """
    for prefix, tag_key in iteritems(METRIC_TO_INSTANCE_TAG_MAPPING):
        if metric_name.startswith(prefix):
            return tag_key
    return 'instance'
