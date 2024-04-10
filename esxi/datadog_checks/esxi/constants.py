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

AVAILABLE_HOST_TAGS = [
    "esxi_url",
    "esxi_type",
    "esxi_host",
    "esxi_folder",
    "esxi_cluster",
    "esxi_compute",
    "esxi_datacenter",
    "esxi_datastore"
]