# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from pyVmomi import vim

SOURCE_TYPE = 'vsphere'

BOTH = 'both'
HISTORICAL = 'historical'
REALTIME = 'realtime'

ALLOWED_FILTER_TYPES = ['whitelist', 'blacklist']
ALLOWED_FILTER_PROPERTIES = ['name', 'inventory_path', 'tag', 'attribute']
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
    vim.StoragePod: 'storage_pod',
    vim.vslm.vcenter.VStorageObjectManager: 'vstorage_object_manager',
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

HOST_RESOURCES = [vim.VirtualMachine, vim.HostSystem]

ALL_RESOURCES_WITH_METRICS = [
    vim.VirtualMachine,
    vim.HostSystem,
    vim.Datacenter,
    vim.Datastore,
    vim.ClusterComputeResource,
]

REALTIME_METRICS_INTERVAL_ID = 20

DEFAULT_BATCH_COLLECTOR_SIZE = 500
DEFAULT_TAGS_COLLECTOR_SIZE = 200
DEFAULT_METRICS_PER_QUERY = 500
UNLIMITED_HIST_METRICS_PER_QUERY = float('inf')
DEFAULT_MAX_QUERY_METRICS = 256  # type: float
MAX_QUERY_METRICS_OPTION = "config.vpxd.stats.maxQueryMetrics"
DEFAULT_THREAD_COUNT = 4

DEFAULT_REFRESH_METRICS_METADATA_CACHE_INTERVAL = 1800
DEFAULT_REFRESH_INFRASTRUCTURE_CACHE_INTERVAL = 300

REFERENCE_METRIC = "cpu.usage.avg"

DEFAULT_VSPHERE_TAG_PREFIX = ""
DEFAULT_VSPHERE_ATTR_PREFIX = ""

DEFAULT_EVENT_RESOURCES = ['vm', 'host']

PROPERTY_COUNT_METRICS = [
    "guest.net",
    "guest.ipStack.ipRoute",
    "guest.net.ipConfig.address",
    "guest.toolsRunningStatus",
    "guest.toolsVersionStatus2",
    "guest.toolsVersion",
    "guest.guestFullName",
    "hardware.cpuPowerManagementInfo.currentPolicy",
    "summary.runtime.connectionState",
    "summary.runtime.powerState",
    "summary.runtime.inMaintenanceMode",
    "configuration.drsConfig.enabled",
    "configuration.drsConfig.defaultVmBehavior",
    "configuration.dasConfig.enabled",
]
VM_OBJECT_PROPERTIES = ["guest.disk", "guest.net", "guest.ipStack"]

VM_SIMPLE_PROPERTIES = [
    "guest.toolsRunningStatus",
    "guest.toolsVersionStatus2",
    "guest.toolsVersion",
    "config.hardware.numCoresPerSocket",
    "config.cpuAllocation.limit",
    "config.cpuAllocation.overheadLimit",
    "config.memoryAllocation.limit",
    "config.memoryAllocation.overheadLimit",
    "summary.config.numCpu",
    "summary.config.memorySizeMB",
    "summary.config.numEthernetCards",
    "summary.config.numVirtualDisks",
    "summary.quickStats.uptimeSeconds",
    "guest.guestFullName",
]

HOST_SIMPLE_PROPERTIES = [
    "hardware.cpuPowerManagementInfo.currentPolicy",
    "summary.runtime.connectionState",
    "summary.runtime.powerState",
    "summary.runtime.inMaintenanceMode",
]

CLUSTER_SIMPLE_PROPERTIES = [
    "configuration.drsConfig.enabled",
    "configuration.drsConfig.defaultVmBehavior",
    "configuration.drsConfig.vmotionRate",
    "configuration.dasConfig.enabled",
]


DATASTORE_SIMPLE_PROPERTIES = [
    "summary.capacity",
    "summary.freeSpace",
]

DATASTORE_PROPERTIES = DATASTORE_SIMPLE_PROPERTIES

CLUSTER_PROPERTIES = CLUSTER_SIMPLE_PROPERTIES

HOST_PROPERTIES = HOST_SIMPLE_PROPERTIES

VM_PROPERTIES = VM_OBJECT_PROPERTIES + VM_SIMPLE_PROPERTIES

ALL_PROPERTIES = VM_PROPERTIES + HOST_PROPERTIES + CLUSTER_PROPERTIES + DATASTORE_PROPERTIES


OBJECT_PROPERTIES_TO_METRIC_NAME = {
    "guest.net": ["guest.net.ipConfig.address", "guest.net"],
    "guest.ipStack": ["guest.ipStack.ipRoute", "guest.ipStack"],
    "guest.disk": ["guest.disk.freeSpace", "guest.disk.capacity"],
}

VM_OBJECT_PROPERTY_METRICS = [
    "guest.net.ipConfig.address",
    "guest.net",
    "guest.ipStack.ipRoute",
    "guest.ipStack",
    "guest.disk.freeSpace",
    "guest.disk.capacity",
]
OBJECT_PROPERTIES_BY_RESOURCE_TYPE = {
    'vm': VM_OBJECT_PROPERTIES,
}

SIMPLE_PROPERTIES_BY_RESOURCE_TYPE = {
    'vm': VM_SIMPLE_PROPERTIES,
    'host': HOST_SIMPLE_PROPERTIES,
    'cluster': CLUSTER_SIMPLE_PROPERTIES,
    'datastore': DATASTORE_SIMPLE_PROPERTIES,
}

PROPERTIES_BY_RESOURCE_TYPE = {
    'vm': VM_PROPERTIES,
    'host': HOST_PROPERTIES,
    'cluster': CLUSTER_PROPERTIES,
    'datastore': DATASTORE_PROPERTIES,
}

PROPERTY_METRICS_BY_RESOURCE_TYPE = {
    'vm': VM_SIMPLE_PROPERTIES + VM_OBJECT_PROPERTY_METRICS,
    'host': HOST_SIMPLE_PROPERTIES,
    'cluster': CLUSTER_SIMPLE_PROPERTIES,
    'datastore': DATASTORE_SIMPLE_PROPERTIES,
}

EXCLUDE_FILTERS = {
    'AlarmStatusChangedEvent': [r'Gray to Green', r'Green to Gray'],
    'TaskEvent': [
        r'Initialize powering On',
        r'Power Off virtual machine',
        r'Power On virtual machine',
        r'Reconfigure virtual machine',
        r'Relocate virtual machine',
        r'Suspend virtual machine',
        r'Migrate virtual machine',
    ],
    'VmBeingHotMigratedEvent': [],
    'VmMessageEvent': [],
    'VmMigratedEvent': [],
    'VmPoweredOnEvent': [],
    'VmPoweredOffEvent': [],
    'VmReconfiguredEvent': [],
    'VmSuspendedEvent': [],
}

PER_RESOURCE_EVENTS = [
    'AlarmAcknowledgedEvent',
    'AlarmActionTriggeredEvent',
    'AlarmClearedEvent',
    'AlarmCreatedEvent',
    'AlarmEmailCompletedEvent',
    'AlarmEmailFailedEvent',
    'AlarmReconfiguredEvent',
    'AlarmRemovedEvent',
    'AlarmScriptCompleteEvent',
    'AlarmScriptFailedEvent',
    'AlarmSnmpCompletedEvent',
    'AlarmSnmpFailedEvent',
    'AlarmStatusChangedEvent',
    'CustomFieldValueChangedEvent',
    'GeneralUserEvent',
    'PermissionEvent',
    'ScheduledTaskEvent',
]

HOSTNAME_CASE_OPTIONS = ['default', 'lower', 'upper']
