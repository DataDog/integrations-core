# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from pyVmomi import vim
from six import iteritems

from datadog_checks.base import to_native_string
from datadog_checks.vsphere.constants import MOR_TYPE_AS_STRING, REFERENCE_METRIC, SHORT_ROLLUP
from datadog_checks.vsphere.types import Counter

METRIC_TO_INSTANCE_TAG_MAPPING = {
    # Structure:
    # prefix: tag key used for instance value
    'cpu.': 'cpu_core',
    # Examples: 0, 15
    'datastore.': 'vmfs_uuid',
    # Examples: fd3f776b-2ca26041, 5deed40f-cef2b3f6-0bcd-000c2927ce06
    'disk.': 'device_path',
    # Examples: mpx.vmhba0:C0:T1:L0, mpx.vmhba0:C0:T1:L0
    'net.': 'nic',
    # Examples: vmnic1, 4000
    'storageAdapter.': 'storage_adapter',
    # Examples: vmhba1, vmhba64
    'storagePath.': 'storage_path',
    # Examples: ide.vmhba64-ide.0:0-mpx.vmhba64:C0:T0:L0, pscsi.vmhba0-pscsi.0:1-mpx.vmhba0:C0:T1:L0
    'sys.resource': 'resource_path',
    # Examples: host/system/vmotion, host/system
    'virtualDisk.': 'disk',
    # Examples: scsi0:0, scsi0:0
}


def format_metric_name(counter):
    # type: (Counter) -> str
    return "{}.{}.{}".format(
        to_native_string(counter.groupInfo.key),
        to_native_string(counter.nameInfo.key),
        SHORT_ROLLUP[str(counter.rollupType)],
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
        parent_name = to_native_string(parent_props.get('name', 'unknown'))
        if isinstance(parent, vim.HostSystem):
            tags.append('vsphere_host:{}'.format(parent_name))
        elif isinstance(parent, vim.Folder):
            tags.append('vsphere_folder:{}'.format(parent_name))
        elif isinstance(parent, vim.ComputeResource):
            if isinstance(parent, vim.ClusterComputeResource):
                tags.append('vsphere_cluster:{}'.format(parent_name))
            tags.append('vsphere_compute:{}'.format(parent_name))
        elif isinstance(parent, vim.Datacenter):
            tags.append('vsphere_datacenter:{}'.format(parent_name))
        elif isinstance(parent, vim.Datastore):
            tags.append('vsphere_datastore:{}'.format(parent_name))

        parent_tags = get_parent_tags_recursively(parent, infrastructure_data)
        parent_tags.extend(tags)
        return parent_tags
    return []


def should_collect_per_instance_values(config, metric_name, resource_type):
    filters = config.collect_per_instance_filters.get(MOR_TYPE_AS_STRING[resource_type], [])
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
