# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pyVmomi import vim

from datadog_checks.base import to_string


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
