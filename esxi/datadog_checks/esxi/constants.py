# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pyVmomi import vim

SHORT_ROLLUP = {
    "average": "avg",
    "summation": "sum",
    "maximum": "max",
    "minimum": "min",
    "latest": "latest",
    "none": "raw",
}

HOST_RESOURCE = vim.HostSystem
VM_RESOURCE = vim.VirtualMachine
DC_RESOURCE = vim.Datacenter
DS_RESOURCE = vim.Datastore
CC_RESOURCE = vim.ClusterComputeResource
COMPUTE_RESOURCE = vim.ComputeResource
FOLDER_RESOURCE = vim.Folder

MAX_PROPERTIES = 100
ALL_RESOURCES = [
    VM_RESOURCE,
    HOST_RESOURCE,
    DC_RESOURCE,
    DS_RESOURCE,
    CC_RESOURCE,
    COMPUTE_RESOURCE,
    FOLDER_RESOURCE,
]

RESOURCE_TYPE_TO_NAME = {
    HOST_RESOURCE: 'host',
    VM_RESOURCE: 'vm',
}

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

AVAILABLE_HOST_TAGS = [
    "esxi_url",
    "esxi_type",
    "esxi_host",
    "esxi_compute",
    "esxi_datastore",
]

ALLOWED_FILTER_TYPES = ['include', 'exclude']
ALLOWED_FILTER_PROPERTIES = ['name']
EXTRA_FILTER_PROPERTIES_FOR_VMS = ['hostname', 'guest_hostname']
