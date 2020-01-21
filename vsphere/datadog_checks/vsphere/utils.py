# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from pyVmomi import vim

from datadog_checks.base import ensure_unicode
from datadog_checks.vsphere.constants import MOR_TYPE_AS_STRING, SHORT_ROLLUP, REFERENCE_METRIC


def format_metric_name(counter):
    return "{}.{}.{}".format(
        ensure_unicode(counter.groupInfo.key),
        ensure_unicode(counter.nameInfo.key),
        ensure_unicode(SHORT_ROLLUP[str(counter.rollupType)]),
    )


def match_any_regex(string, regexes):
    for regex in regexes:
        match = regex.match(string)
        if match:
            return True
    return False


def is_resource_excluded_by_filters(mor, infrastructure_data, resource_filters):
    resource_type = MOR_TYPE_AS_STRING[type(mor)]

    if not [f for f in resource_filters if f[0] == resource_type]:
        # No filter for this resource, collect everything
        return False

    name_filter = resource_filters.get((resource_type, 'name'))
    inventory_path_filter = resource_filters.get((resource_type, 'inventory_path'))
    hostname_filter = resource_filters.get((resource_type, 'hostname'))
    guest_hostname_filter = resource_filters.get((resource_type, 'guest_hostname'))

    if name_filter:
        mor_name = infrastructure_data.get(mor).get("name", "")
        if match_any_regex(mor_name, name_filter):
            return False
    if inventory_path_filter:
        path = make_inventory_path(mor, infrastructure_data)
        if match_any_regex(path, inventory_path_filter):
            return False

    if hostname_filter and isinstance(mor, vim.VirtualMachine):
        host = infrastructure_data.get(mor).get("runtime.host")
        hostname = infrastructure_data.get(host, {}).get("name", "")
        if match_any_regex(hostname, hostname_filter):
            return False
    if guest_hostname_filter and isinstance(mor, vim.VirtualMachine):
        guest_hostname = infrastructure_data.get(mor, {}).get("guest.hostName", "")
        if match_any_regex(guest_hostname, guest_hostname_filter):
            return False

    return True


def is_metric_excluded_by_filters(metric_name, mor_type, metric_filters):
    if metric_name.startswith(REFERENCE_METRIC):
        # Always collect at least one metric for reference
        return False
    filters = metric_filters.get(MOR_TYPE_AS_STRING[mor_type])
    if not filters:
        # No filters means collect everything
        return False
    if match_any_regex(metric_name, filters):
        return False

    return True


def make_inventory_path(mor, infrastructure_data):
    mor_name = infrastructure_data.get(mor).get('name', '')
    mor_parent = infrastructure_data.get(mor).get('parent')
    if mor_parent:
        return make_inventory_path(mor_parent, infrastructure_data) + '/' + mor_name
    return ''


def get_parent_tags_recursively(mor, infrastructure_data):
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
    mor_props = infrastructure_data.get(mor)
    parent = mor_props.get('parent')
    if parent:
        tags = []
        parent_props = infrastructure_data.get(parent, {})
        parent_name = ensure_unicode(parent_props.get('name', 'unknown'))
        if isinstance(parent, vim.HostSystem):
            tags.append(u'vsphere_host:{}'.format(parent_name))
        elif isinstance(parent, vim.Folder):
            tags.append(u'vsphere_folder:{}'.format(parent_name))
        elif isinstance(parent, vim.ComputeResource):
            if isinstance(parent, vim.ClusterComputeResource):
                tags.append(u'vsphere_cluster:{}'.format(parent_name))
            tags.append(u'vsphere_compute:{}'.format(parent_name))
        elif isinstance(parent, vim.Datacenter):
            tags.append(u'vsphere_datacenter:{}'.format(parent_name))
        elif isinstance(parent, vim.Datastore):
            tags.append(u'vsphere_datastore:{}'.format(parent_name))

        parent_tags = get_parent_tags_recursively(parent, infrastructure_data)
        parent_tags.extend(tags)
        return parent_tags
    return []


def should_collect_per_instance_values(metric_name, resource_type):
    # TODO: Implement. For now we don't collect per-instance level metrics (aka per-core for cpu, per-vm for disk etc.)
    # TODO: Collecting per-instance metrics is really expensive for big environments and has usually little value.
    # TODO: Also that adds an extra layer of complexity where users have to set `instance:none` to see the correct
    # value.
    return False


def get_mapped_instance_tag(metric_name):
    """When collecting per-instance metric, the `instance` tag can mean a lot of different things. The meaning of the
    tag cannot be guessed by looking at the api results and has to be infered using documentation or experience.
    This method acts as a utility to map a metric_name to the meaning of its instance tag.
    TODO: More
    """
    if metric_name.startswith('cpu'):
        return 'cpu_core'
    elif metric_name.startswith('disk'):
        return 'vm'
    return 'instance'
