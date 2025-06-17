# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import re
from urllib.parse import urlparse

import mock
from pyVmomi import vim, vmodl

from datadog_checks.base.utils.time import get_current_datetime
from datadog_checks.dev.http import MockResponse
from datadog_checks.vsphere.api_rest import VSphereRestAPI

HERE = os.path.abspath(os.path.dirname(__file__))

VSPHERE_VERSION = os.environ.get('VSPHERE_VERSION')

VSPHERE_USERNAME = 'FAKE'
VSPHERE_PASSWORD = 'FAKE'
VSPHERE_URL = 'FAKE'

LAB_USERNAME = os.environ.get('TEST_VSPHERE_USER')
LAB_PASSWORD = os.environ.get('TEST_VSPHERE_PASS')

LAB_INSTANCE = {
    'host': 'aws.vcenter.localdomain',
    'username': LAB_USERNAME,
    'password': LAB_PASSWORD,
    'collection_level': 4,
    'collection_type': 'both',
    'use_legacy_check_version': False,
    'collect_metric_instance_values': True,
    'empty_default_hostname': True,
    'ssl_verify': False,
    'collect_tags': True,
    'collect_events': True,
    'use_collect_events_fallback': True,
}

LEGACY_DEFAULT_INSTANCE = {
    'use_legacy_check_version': True,
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
}

LEGACY_REALTIME_INSTANCE = {
    'use_legacy_check_version': True,
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
    'collect_realtime_only': True,
}

LEGACY_HISTORICAL_INSTANCE = {
    'use_legacy_check_version': True,
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
    'collect_historical_only': True,
}

DEFAULT_INSTANCE = {
    'use_legacy_check_version': False,
    'empty_default_hostname': True,
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
    'ssl_verify': False,
}

REALTIME_INSTANCE = {
    'use_legacy_check_version': False,
    'empty_default_hostname': True,
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
    'ssl_verify': False,
    'collection_level': 4,
    'rest_api_options': None,
}

HISTORICAL_INSTANCE = {
    'use_legacy_check_version': False,
    'empty_default_hostname': True,
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
    'ssl_verify': False,
    'collection_level': 4,
    'collection_type': 'historical',
}

EVENTS_ONLY_INSTANCE = {
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': VSPHERE_URL,
    'username': VSPHERE_USERNAME,
    'password': VSPHERE_PASSWORD,
    'ssl_verify': False,
    'collect_events_only': True,
}


def build_rest_api_client(config, logger):
    if VSPHERE_VERSION.startswith('7.'):
        return VSphereRestAPI(config, logger, False)
    return VSphereRestAPI(config, logger, True)


EVENTS = [
    vim.event.VmMessageEvent(
        createdTime=get_current_datetime(),
        vm=vim.event.VmEventArgument(name="vm1"),
        fullFormattedMessage="First event in time",
    ),
    vim.event.VmMessageEvent(
        createdTime=get_current_datetime(),
        vm=vim.event.VmEventArgument(name="vm2"),
        fullFormattedMessage="Second event in time",
    ),
]


PERF_METRIC_ID = [
    vim.PerformanceManager.MetricId(counterId=100),
    vim.PerformanceManager.MetricId(counterId=101),
    vim.PerformanceManager.MetricId(counterId=102),
    vim.PerformanceManager.MetricId(counterId=103),
]


PERF_COUNTER_INFO = [
    vim.PerformanceManager.CounterInfo(
        key=100,
        groupInfo=vim.ElementDescription(key='datastore'),
        nameInfo=vim.ElementDescription(key='busResets'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
        unitInfo=vim.ElementDescription(key='command'),
    ),
    vim.PerformanceManager.CounterInfo(
        key=101,
        groupInfo=vim.ElementDescription(key='cpu'),
        nameInfo=vim.ElementDescription(key='totalmhz'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.average,
        unitInfo=vim.ElementDescription(key='megahertz'),
    ),
    vim.PerformanceManager.CounterInfo(
        key=102,
        groupInfo=vim.ElementDescription(key='vmop'),
        nameInfo=vim.ElementDescription(key='numChangeDS'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.latest,
        unitInfo=vim.ElementDescription(key='operation'),
    ),
    vim.PerformanceManager.CounterInfo(
        key=103,
        groupInfo=vim.ElementDescription(key='cpu'),
        nameInfo=vim.ElementDescription(key='costop'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
        unitInfo=vim.ElementDescription(key='millisecond'),
    ),
    vim.PerformanceManager.CounterInfo(
        key=104,
        groupInfo=vim.ElementDescription(key='mem'),
        nameInfo=vim.ElementDescription(key='active'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.average,
        unitInfo=vim.ElementDescription(key='kibibyte'),
    ),
    vim.PerformanceManager.CounterInfo(
        key=105,
        groupInfo=vim.ElementDescription(key='datastore'),
        nameInfo=vim.ElementDescription(key='busResets'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
        unitInfo=vim.ElementDescription(key='operation'),
    ),
    vim.PerformanceManager.CounterInfo(
        key=106,
        groupInfo=vim.ElementDescription(key='datastore'),
        nameInfo=vim.ElementDescription(key='commandsAborted'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
        unitInfo=vim.ElementDescription(key='operation'),
    ),
]


PERF_ENTITY_METRICS = [
    vim.PerformanceManager.EntityMetric(
        entity=vim.VirtualMachine(moId="vm1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[47, 52],
                id=vim.PerformanceManager.MetricId(counterId=103),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.VirtualMachine(moId="vm2"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[30, 11],
                id=vim.PerformanceManager.MetricId(counterId=103),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.VirtualMachine(moId="vm3"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[32, 92],
                id=vim.PerformanceManager.MetricId(counterId=103),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datastore(moId="ds1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[2, 5],
                id=vim.PerformanceManager.MetricId(
                    counterId=100,
                    instance='ds1',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.ClusterComputeResource(moId="c1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[2, 5],
                id=vim.PerformanceManager.MetricId(
                    counterId=101,
                    instance='c1',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datacenter(moId="dc1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[1, 7],
                id=vim.PerformanceManager.MetricId(
                    counterId=102,
                    instance='dc1',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datacenter(moId="dc2"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[1, 3],
                id=vim.PerformanceManager.MetricId(
                    counterId=102,
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.HostSystem(moId="host1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[34, 61],
                id=vim.PerformanceManager.MetricId(
                    counterId=103,
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.HostSystem(moId="host2"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[34, 61],
                id=vim.PerformanceManager.MetricId(
                    counterId=103,
                ),
            )
        ],
    ),
]


PROPERTIES_EX_VM_OFF = vim.PropertyCollector.RetrieveResult(
    objects=[
        vim.ObjectContent(
            obj=vim.VirtualMachine(moId="vm1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='vm1',
                ),
                vmodl.DynamicProperty(
                    name='runtime.powerState',
                    val=vim.VirtualMachinePowerState.poweredOff,
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.VirtualMachine(moId="vm2"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='vm2',
                ),
                vmodl.DynamicProperty(
                    name='runtime.powerState',
                    val=vim.VirtualMachinePowerState.poweredOn,
                ),
            ],
        ),
    ]
)

PROPERTIES_EX = vim.PropertyCollector.RetrieveResult(
    objects=[
        vim.ObjectContent(
            obj=vim.VirtualMachine(moId="vm1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='vm1',
                ),
                vmodl.DynamicProperty(
                    name='runtime.powerState',
                    val=vim.VirtualMachinePowerState.poweredOn,
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.VirtualMachine(moId="vm2"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='vm2',
                ),
                vmodl.DynamicProperty(
                    name='runtime.powerState',
                    val=vim.VirtualMachinePowerState.poweredOn,
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Datastore(moId="ds1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='ds1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.ClusterComputeResource(moId="c1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='c1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Folder(moId="folder_1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='folder_1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Datacenter(moId="dc1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='dc1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Datacenter(moId="dc2"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='dc2',
                ),
                vmodl.DynamicProperty(
                    name='parent',
                    val=vim.Folder(moId="folder_1"),
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.HostSystem(moId="host1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='host1',
                ),
            ],
        ),
    ],
)


# VM 1 disk
disk = vim.vm.GuestInfo.DiskInfo()
disk.diskPath = '\\'
disk.capacity = 2064642048
disk.freeSpace = 1270075392
disk.filesystemType = 'ext4'
DISKS = vim.ArrayOfAnyType()
DISKS.append(disk)

# VM 1 net
ip_address = vim.net.IpConfigInfo.IpAddress()
ip_address.ipAddress = 'fe70::150:46ff:fe47:6311'
ip_config = vim.net.IpConfigInfo()
ip_config.ipAddress = vim.ArrayOfAnyType()
ip_config.ipAddress.append(ip_address)
net = vim.vm.GuestInfo.NicInfo()
net.macAddress = '00:61:58:72:53:13'
net.connected = True
net.ipConfig = ip_config
NETS = vim.ArrayOfAnyType()
NETS.append(net)

# VM 1 ip stack
dns_config = vim.net.DnsConfigInfo()
dns_config.hostName = 'test-hostname'
dns_config.domainName = 'example.com'
gateway = vim.net.IpRouteConfigInfo.Gateway()
gateway.device = '0'
gateway.ipAddress = None
ip_route = vim.net.IpRouteConfigInfo.IpRoute()
ip_route.prefixLength = 64
ip_route.network = 'fe83::'
ip_route.gateway = gateway
ip_route_config = vim.net.IpRouteConfigInfo()
ip_route_config.ipRoute = vim.ArrayOfAnyType()
ip_route_config.ipRoute.append(ip_route)
ip_stack = vim.vm.GuestInfo.StackInfo()
ip_stack.dnsConfig = dns_config
ip_stack.ipRouteConfig = ip_route_config
IP_STACKS = vim.ArrayOfAnyType()
IP_STACKS.append(ip_stack)

# VM 3 disk
DISKS_3 = vim.ArrayOfAnyType()

# VM 3 net
ip_address3 = vim.net.IpConfigInfo.IpAddress()
ip_address3.ipAddress = 'fe70::150:46ff:fe47:6311'
ip_address4 = vim.net.IpConfigInfo.IpAddress()
ip_address4.ipAddress = 'fe80::170:46ff:fe27:6311'
ip_config3 = vim.net.IpConfigInfo()
ip_config3.ipAddress = vim.ArrayOfAnyType()
ip_config3.ipAddress.append(ip_address3)
ip_config3.ipAddress.append(ip_address4)
net3 = vim.vm.GuestInfo.NicInfo()
net3.macAddress = None
net3.deviceConfigId = 43
net3.ipConfig = ip_config3
NETS_3 = vim.ArrayOfAnyType()
NETS_3.append(net3)

# VM 3 ip stack
gateway3 = vim.net.IpRouteConfigInfo.Gateway()
gateway3.device = '0'
gateway3.ipAddress = '0.0.0.0'
ip_route3 = vim.net.IpRouteConfigInfo.IpRoute()
ip_route3.prefixLength = 32
ip_route3.network = 'fe83::'
ip_route3.gateway = gateway3
ip_route_config3 = vim.net.IpRouteConfigInfo()
ip_route_config3.ipRoute = vim.ArrayOfAnyType()
ip_route_config3.ipRoute.append(ip_route3)
ip_stack3 = vim.vm.GuestInfo.StackInfo()
ip_stack3.dnsConfig = None
ip_stack3.ipRouteConfig = ip_route_config3
IP_STACKS_3 = vim.ArrayOfAnyType()
IP_STACKS_3.append(ip_stack3)

# VM invalid
ip_config_invalid = vim.net.IpConfigInfo()
net_invalid = vim.vm.GuestInfo.NicInfo()
net_invalid.macAddress = '00:61:58:72:53:13'
net_invalid.connected = True
NETS_INVALID = vim.ArrayOfAnyType()
NETS_INVALID.append(net_invalid)

# VM invalid ip stack
ip_stack_invalid = vim.vm.GuestInfo.StackInfo()
ip_stack_invalid.dnsConfig = None
IP_STACKS_INVALID = vim.ArrayOfAnyType()
IP_STACKS_INVALID.append(ip_stack_invalid)

# VM invalid ip route gateway
ip_route_invalid2 = vim.net.IpRouteConfigInfo.IpRoute()
ip_route_invalid2.prefixLength = 32
ip_route_invalid2.network = 'fe83::'
ip_route_config_invalid2 = vim.net.IpRouteConfigInfo()
ip_route_config_invalid2.ipRoute = vim.ArrayOfAnyType()
ip_route_config_invalid2.ipRoute.append(ip_route_invalid2)
ip_stack_invalid2 = vim.vm.GuestInfo.StackInfo()
ip_stack_invalid2.dnsConfig = None
ip_stack_invalid2.ipRouteConfig = ip_route_config_invalid2
IP_STACKS_INVALID2 = vim.ArrayOfAnyType()
IP_STACKS_INVALID2.append(ip_stack_invalid2)

VM_PROPERTIES_EX = mock.MagicMock(
    return_value=vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.powerState',
                        val=vim.VirtualMachinePowerState.poweredOn,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numCpu',
                        val=2,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.memorySizeMB',
                        val=2048,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numVirtualDisks',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numEthernetCards',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.quickStats.uptimeSeconds',
                        val=12184573,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.guestFullName',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.disk',
                        val=DISKS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.net',
                        val=NETS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.ipStack',
                        val=IP_STACKS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsVersion',
                        val='11296',
                    ),
                    vmodl.DynamicProperty(
                        name='config.hardware.numCoresPerSocket',
                        val='2',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Folder(moId="root"),
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val=vim.HostSystem(moId="host1"),
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm3"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm3',
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.powerState',
                        val=vim.VirtualMachinePowerState.poweredOn,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numCpu',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.memorySizeMB',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numVirtualDisks',
                        val=3,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numEthernetCards',
                        val=3,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.quickStats.uptimeSeconds',
                        val=1218453,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.guestFullName',
                        val='Debian GNU/Linux 12 (32-bit)',
                    ),
                    vmodl.DynamicProperty(name='guest.disk', val=DISKS_3),
                    vmodl.DynamicProperty(
                        name='guest.net',
                        val=NETS_3,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.ipStack',
                        val=IP_STACKS_3,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsRunningStatus',
                        val='guestToolsRunning',
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsVersionStatus2',
                        val='guestToolsSupportedOld',
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsVersion',
                        val='11296',
                    ),
                    vmodl.DynamicProperty(
                        name='config.hardware.numCoresPerSocket',
                        val='2',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.limit',
                        val='10',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.overheadLimit',
                        val='24',
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.overheadLimit',
                        val='59',
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Folder(moId="root"),
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val=vim.HostSystem(moId="host2"),
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm2"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm2',
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.powerState',
                        val=vim.VirtualMachinePowerState.poweredOff,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numCpu',
                        val=2,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.memorySizeMB',
                        val=2048,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numVirtualDisks',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numEthernetCards',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.quickStats.uptimeSeconds',
                        val=12184573,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.guestFullName',
                        val='Debian GNU/Linux 12 (32-bit)',
                    ),
                    vmodl.DynamicProperty(name='guest.disk', val=DISKS),
                    vmodl.DynamicProperty(
                        name='guest.net',
                        val=NETS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.ipStack',
                        val=IP_STACKS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsRunningStatus',
                        val='guestToolsRunning',
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsVersion',
                        val='11296',
                    ),
                    vmodl.DynamicProperty(
                        name='config.hardware.numCoresPerSocket',
                        val='2',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Folder(moId="root"),
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val=vim.HostSystem(moId="host2"),
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.HostSystem(moId="host1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='host1',
                    ),
                    vmodl.DynamicProperty(
                        name='hardware.cpuPowerManagementInfo.currentPolicy',
                        val='Balanced',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.runtime.connectionState',
                        val='connected',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.runtime.powerState',
                        val='poweredOn',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.runtime.inMaintenanceMode',
                        val=False,
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.HostSystem(moId="host2"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='host2',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.runtime.connectionState',
                        val='notResponding',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.runtime.powerState',
                        val='unknown',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.runtime.inMaintenanceMode',
                        val=True,
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.ClusterComputeResource(moId="c1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='c1',
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.dasConfig.enabled',
                        val=True,
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.drsConfig.enabled',
                        val=True,
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.drsConfig.defaultVmBehavior',
                        val='fullyAutomated',
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.drsConfig.vmotionRate',
                        val=2,
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.ClusterComputeResource(moId="c2"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='c2',
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.dasConfig.enabled',
                        val=False,
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.drsConfig.enabled',
                        val=False,
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.drsConfig.defaultVmBehavior',
                        val='fullyAutomated',
                    ),
                    vmodl.DynamicProperty(
                        name='configuration.drsConfig.vmotionRate',
                        val=1,
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.Datastore(moId="ds1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='ds1',
                    ),
                    vmodl.DynamicProperty(
                        name='summary.freeSpace',
                        val=305,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.capacity',
                        val=100,
                    ),
                ],
            ),
            vim.ObjectContent(
                obj=vim.Datacenter(moId="dc2"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='dc2',
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Folder(moId="folder_1"),
                    ),
                ],
            ),
        ],
    )
)


VM_INVALID_PROPERTIES_EX = mock.MagicMock(
    return_value=vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.powerState',
                        val=vim.VirtualMachinePowerState.poweredOn,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numCpu',
                        val=2,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.memorySizeMB',
                        val=2048,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numVirtualDisks',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numEthernetCards',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.quickStats.uptimeSeconds',
                        val=12184573,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.guestFullName',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.disk',
                        val=DISKS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.net',
                        val=NETS_INVALID,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.ipStack',
                        val=IP_STACKS_INVALID,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsVersion',
                        val='11296',
                    ),
                    vmodl.DynamicProperty(
                        name='config.hardware.numCoresPerSocket',
                        val='2',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Folder(moId="root"),
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val=vim.HostSystem(moId="host1"),
                    ),
                ],
            ),
        ]
    )
)

VM_INVALID_GATEWAY_PROPERTIES_EX = mock.MagicMock(
    return_value=vim.PropertyCollector.RetrieveResult(
        objects=[
            vim.ObjectContent(
                obj=vim.VirtualMachine(moId="vm1"),
                propSet=[
                    vmodl.DynamicProperty(
                        name='name',
                        val='vm1',
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.powerState',
                        val=vim.VirtualMachinePowerState.poweredOn,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numCpu',
                        val=2,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.memorySizeMB',
                        val=2048,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numVirtualDisks',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.config.numEthernetCards',
                        val=1,
                    ),
                    vmodl.DynamicProperty(
                        name='summary.quickStats.uptimeSeconds',
                        val=12184573,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.guestFullName',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.disk',
                        val=DISKS,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.net',
                        val=NETS_INVALID,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.ipStack',
                        val=IP_STACKS_INVALID2,
                    ),
                    vmodl.DynamicProperty(
                        name='guest.toolsVersion',
                        val='11296',
                    ),
                    vmodl.DynamicProperty(
                        name='config.hardware.numCoresPerSocket',
                        val='2',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.cpuAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.limit',
                        val='-1',
                    ),
                    vmodl.DynamicProperty(
                        name='config.memoryAllocation.overheadLimit',
                        val=None,
                    ),
                    vmodl.DynamicProperty(
                        name='parent',
                        val=vim.Folder(moId="root"),
                    ),
                    vmodl.DynamicProperty(
                        name='runtime.host',
                        val=vim.HostSystem(moId="host1"),
                    ),
                ],
            ),
        ]
    )
)


class MockHttpV6:
    def __init__(self):
        self.exceptions = {}

    def get(self, url, *args, **kwargs):
        if '/api/' in url:
            return MockResponse({}, 404)
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/category/id:.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    "value": {
                        "name": "my_cat_name_{}".format(num),
                        "description": "",
                        "id": "cat_id_{}".format(num),
                        "used_by": [],
                        "cardinality": "SINGLE",
                    }
                },
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag/id:.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    "value": {
                        "category_id": "cat_id_{}".format(num),
                        "name": "my_tag_name_{}".format(num),
                        "description": "",
                        "id": "xxx",
                        "used_by": [],
                    }
                },
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('get', url))

    def post(self, url, *args, **kwargs):
        if '/api/' in url:
            return MockResponse({}, 404)
        assert kwargs['headers']['Content-Type'] == 'application/json'
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/session$', url):
            return MockResponse(
                json_data={"value": "dummy-token"},
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag-association\?~action=list-attached-tags-on-objects$', url):
            return MockResponse(
                json_data={
                    "value": [
                        {"object_id": {"id": "vm1", "type": "VirtualMachine"}, "tag_ids": ["tag_id_1", "tag_id_2"]},
                        {"object_id": {"id": "host1", "type": "HostSystem"}, "tag_ids": ["tag_id_2"]},
                        {"object_id": {"id": "ds1", "type": "Datastore"}, "tag_ids": ["tag_id_2"]},
                    ]
                },
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('post', url))


class MockHttpV7:
    def __init__(self):
        self.exceptions = []

    def get(self, url, *args, **kwargs):
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/category/.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    'name': 'my_cat_name_{}'.format(num),
                    'description': 'VM category description',
                    'id': 'cat_id_{}'.format(num),
                    'used_by': [],
                    'cardinality': 'SINGLE',
                },
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag/.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    'category_id': 'cat_id_{}'.format(num),
                    'name': 'my_tag_name_{}'.format(num),
                    'description': '',
                    'id': 'tag_id_{}'.format(num),
                    'used_by': [],
                },
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('get', url))

    def post(self, url, *args, **kwargs):
        assert kwargs['headers']['Content-Type'] == 'application/json'
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/session$', url):
            return MockResponse(
                json_data="dummy-token",
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag-association\?action=list-attached-tags-on-objects$', url):
            return MockResponse(
                json_data=[
                    {'tag_ids': ['tag_id_1', 'tag_id_2'], 'object_id': {'id': 'vm1', 'type': 'VirtualMachine'}},
                    {'tag_ids': ['tag_id_2'], 'object_id': {'id': 'ds1', 'type': 'Datastore'}},
                    {'tag_ids': ['tag_id_2'], 'object_id': {'id': 'host1', 'type': 'HostSystem'}},
                ],
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('post', url))
