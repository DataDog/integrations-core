# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from pyVmomi import vim

ALLOWED_FILTER_PROPERTIES = ['name', 'inventory_path']
EXTRA_FILTER_PROPERTIES_FOR_VMS = ['hostname', 'guest_hostname']
SHORT_ROLLUP = {
    "average": "avg",
    "summation": "sum",
    "maximum": "max",
    "minimum": "min",
    "latest": "latest",
    "none": "raw",
}

MOR_TYPE_AS_STRING = {
    vim.HostSystem: 'host',
    vim.VirtualMachine: 'vm',
    vim.Datacenter: 'datacenter',
    vim.Datastore: 'datastore',
    vim.ClusterComputeResource: 'cluster',
}

ALL_RESOURCES = [
    vim.VirtualMachine,
    vim.HostSystem,
    vim.Datacenter,
    vim.Datastore,
    vim.ClusterComputeResource,
    vim.ComputeResource,
    vim.Folder,
]
REALTIME_RESOURCES = [vim.VirtualMachine, vim.HostSystem]
HISTORICAL_RESOURCES = [vim.Datacenter, vim.Datastore, vim.ClusterComputeResource]
ALL_RESOURCES_WITH_METRICS = REALTIME_RESOURCES + HISTORICAL_RESOURCES

REALTIME_METRICS_INTERVAL_ID = 20

DEFAULT_BATCH_COLLECTOR_SIZE = 500
DEFAULT_METRICS_PER_QUERY = 500
UNLIMITED_HIST_METRICS_PER_QUERY = float('inf')
DEFAULT_MAX_QUERY_METRICS = 256
MAX_QUERY_METRICS_OPTION = "config.vpxd.stats.maxQueryMetrics"
DEFAULT_THREAD_COUNT = 4

DEFAULT_REFRESH_METRICS_METADATA_CACHE_INTERVAL = 1800
DEFAULT_REFRESH_INFRASTRUCTURE_CACHE_INTERVAL = 300
DEFAULT_REFRESH_TAGS_CACHE_INTERVAL = 300

REFERENCE_METRIC = "cpu.usage.avg"

DEFAULT_VSPHERE_TAG_PREFIX = ""
