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
MAX_PROPERTIES = 100

RESOURCE_TYPE_TO_NAME = {HOST_RESOURCE: 'Host', VM_RESOURCE: 'VM'}
