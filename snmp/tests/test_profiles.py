# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.snmp import SnmpCheck

from . import common
from .metrics import (
    ADAPTER_IF_COUNTS,
    CIE_METRICS,
    CPU_METRICS,
    DISK_GAUGES,
    DRS_GAUGES,
    FRU_METRICS,
    IF_COUNTS,
    IF_GAUGES,
    IF_RATES,
    IP_COUNTS,
    IP_IF_COUNTS,
    IPX_COUNTS,
    LTM_GAUGES,
    LTM_NODES_COUNTS,
    LTM_NODES_GAUGES,
    LTM_NODES_RATES,
    LTM_POOL_COUNTS,
    LTM_POOL_GAUGES,
    LTM_POOL_MEMBER_COUNTS,
    LTM_POOL_MEMBER_GAUGES,
    LTM_POOL_MEMBER_RATES,
    LTM_POOL_RATES,
    LTM_VIRTUAL_SERVER_COUNTS,
    LTM_VIRTUAL_SERVER_GAUGES,
    LTM_VIRTUAL_SERVER_RATES,
    MEMORY_METRICS,
    PEER_GAUGES,
    PEER_RATES,
    PROBE_GAUGES,
    SYSTEM_STATUS_GAUGES,
    TCP_COUNTS,
    TCP_GAUGES,
    UDP_COUNTS,
    VOLTAGE_GAUGES,
)

pytestmark = pytest.mark.usefixtures("dd_environment")


def test_load_profiles():
    instance = common.generate_instance_config([])
    check = SnmpCheck('snmp', {}, [instance])
    for name, profile in check.profiles.items():
        try:
            check._config.refresh_with_profile(profile)
        except ConfigurationError as e:
            pytest.fail("Profile `{}` is not configured correctly: {}".format(name, e))


def run_profile_check(recording_name):
    """
    Run a single check with the provided `recording_name` used as
    `community_string` by the docker SNMP endpoint.
    """
    instance = common.generate_instance_config([])

    instance['community_string'] = recording_name
    instance['enforce_mib_constraints'] = False
    check = SnmpCheck('snmp', {}, [instance])
    check.check(instance)


def test_cisco_voice(aggregator):
    run_profile_check('cisco_icm')

    tags = ['snmp_profile:cisco_icm', 'snmp_host:test'] + common.CHECK_TAGS

    resources = ["hrSWRunPerfMem", "hrSWRunPerfCPU", "hrSWRunStatus"]

    for resource in resources:
        aggregator.assert_metric('snmp.{}'.format(resource), metric_type=aggregator.GAUGE, tags=tags)

    cvp_gauges = [
        "ccvpSipIntAvgLatency1",
        "ccvpSipIntAvgLatency2",
        "ccvpSipIntConnectsRcv",
        "ccvpSipIntNewCalls",
        "ccvpSipRtActiveCalls",
        "ccvpSipRtTotalCallLegs",
        "ccvpLicRtPortsInUse",
    ]

    cvp_counts = [
        "ccvpLicAggMaxPortsInUse",
    ]
    for cvp in cvp_gauges:
        aggregator.assert_metric('snmp.{}'.format(cvp), metric_type=aggregator.GAUGE, tags=tags)

    for cvp in cvp_counts:
        aggregator.assert_metric('snmp.{}'.format(cvp), metric_type=aggregator.RATE, tags=tags)

    ccms = ["ccmRegisteredGateways", "ccmRejectedPhones", "ccmRegisteredPhones", "ccmUnregisteredPhones"]

    for ccm in ccms:
        aggregator.assert_metric('snmp.{}'.format(ccm), metric_type=aggregator.RATE, tags=tags)

    calls = [
        "cvCallVolPeerIncomingCalls",
        "cvCallVolPeerOutgoingCalls",
        "cvCallVolMediaIncomingCalls",
        "cvCallVolMediaOutgoingCalls",
    ]

    for call in calls:
        aggregator.assert_metric('snmp.{}'.format(call), metric_type=aggregator.GAUGE, tags=tags)

    dial_controls = [
        "dialCtlPeerStatsAcceptCalls",
        "dialCtlPeerStatsFailCalls",
        "dialCtlPeerStatsRefuseCalls",
        "dialCtlPeerStatsSuccessCalls",
    ]

    for ctl in dial_controls:
        aggregator.assert_metric('snmp.{}'.format(ctl), metric_type=aggregator.MONOTONIC_COUNT, tags=tags)

    pim_tags = tags + ['pim_host:test', 'pim_name:name', 'pim_num:2']
    aggregator.assert_metric('snmp.{}'.format("cccaPimStatus"), metric_type=aggregator.GAUGE, tags=pim_tags)
    aggregator.assert_metric('snmp.{}'.format("sysUpTimeInstance"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_f5(aggregator):
    run_profile_check('f5')

    gauges = [
        'sysStatMemoryTotal',
        'sysStatMemoryUsed',
        'sysGlobalTmmStatMemoryTotal',
        'sysGlobalTmmStatMemoryUsed',
        'sysGlobalHostOtherMemoryTotal',
        'sysGlobalHostOtherMemoryUsed',
        'sysGlobalHostSwapTotal',
        'sysGlobalHostSwapUsed',
        'sysTcpStatOpen',
        'sysTcpStatCloseWait',
        'sysTcpStatFinWait',
        'sysTcpStatTimeWait',
        'sysUdpStatOpen',
        'sysClientsslStatCurConns',
    ]
    counts = [
        'sysTcpStatAccepts',
        'sysTcpStatAcceptfails',
        'sysTcpStatConnects',
        'sysTcpStatConnfails',
        'sysUdpStatAccepts',
        'sysUdpStatAcceptfails',
        'sysUdpStatConnects',
        'sysUdpStatConnfails',
        'sysClientsslStatEncryptedBytesIn',
        'sysClientsslStatEncryptedBytesOut',
        'sysClientsslStatDecryptedBytesIn',
        'sysClientsslStatDecryptedBytesOut',
        'sysClientsslStatHandshakeFailures',
    ]
    cpu_rates = [
        'sysMultiHostCpuUser',
        'sysMultiHostCpuNice',
        'sysMultiHostCpuSystem',
        'sysMultiHostCpuIdle',
        'sysMultiHostCpuIrq',
        'sysMultiHostCpuSoftirq',
        'sysMultiHostCpuIowait',
    ]

    interfaces = ['1.0', 'mgmt', '/Common/internal', '/Common/http-tunnel', '/Common/socks-tunnel']
    tags = ['snmp_profile:f5-big-ip', 'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal']
    tags += common.CHECK_TAGS

    for metric in gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in counts:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)
    for metric in cpu_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:0'] + tags, count=1)
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=['cpu:1'] + tags, count=1)
    for interface in interfaces:
        interface_tags = ['interface:{}'.format(interface)] + tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=interface_tags, count=1,
            )
        for metric in IF_RATES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=interface_tags, count=1
            )
    for metric in IF_GAUGES:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=['interface:{}'.format(interface)] + tags,
                count=1,
            )

    for metric in LTM_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    servers = ['server1', 'server2', 'server3']
    for server in servers:
        server_tags = tags + ['server:{}'.format(server)]
        for metric in LTM_VIRTUAL_SERVER_GAUGES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=server_tags, count=1,
            )
        for metric in LTM_VIRTUAL_SERVER_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=server_tags, count=1,
            )
        for metric in LTM_VIRTUAL_SERVER_RATES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=server_tags, count=1,
            )

    nodes = ['node1', 'node2', 'node3']
    for node in nodes:
        node_tags = tags + ['node:{}'.format(node)]
        for metric in LTM_NODES_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=node_tags, count=1)
        for metric in LTM_NODES_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=node_tags, count=1
            )
        for metric in LTM_NODES_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=node_tags, count=1)

    pools = ['pool1', 'pool2']
    for pool in pools:
        pool_tags = tags + ['pool:{}'.format(pool)]
        for metric in LTM_POOL_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=pool_tags, count=1)
        for metric in LTM_POOL_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=pool_tags, count=1
            )
        for metric in LTM_POOL_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=pool_tags, count=1)

    pool_members = [('pool1', 'node1'), ('pool1', 'node2'), ('pool2', 'node3')]
    for pool, node in pool_members:
        pool_member_tags = tags + ['pool:{}'.format(pool), 'node:{}'.format(node)]
        for metric in LTM_POOL_MEMBER_GAUGES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=pool_member_tags, count=1
            )
        for metric in LTM_POOL_MEMBER_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=pool_member_tags, count=1
            )
        for metric in LTM_POOL_MEMBER_RATES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=pool_member_tags, count=1
            )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_router(aggregator):
    run_profile_check('network')
    common_tags = common.CHECK_TAGS + ['snmp_profile:generic-router']
    for interface in ['eth0', 'eth1']:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS + IPX_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IP_IF_COUNTS:
            for interface in ['17', '21']:
                tags = ['ipversion:{}'.format(version), 'interface:{}'.format(interface)] + common_tags
                aggregator.assert_metric(
                    'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
                )

    aggregator.assert_all_metrics_covered()


def test_f5_router(aggregator):
    # Use the generic profile against the f5 device
    instance = common.generate_instance_config([])

    instance['community_string'] = 'f5'
    instance['enforce_mib_constraints'] = False

    init_config = {'profiles': {'router': {'definition_file': 'generic-router.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    interfaces = ['1.0', 'mgmt', '/Common/internal', '/Common/http-tunnel', '/Common/socks-tunnel']
    common_tags = ['snmp_profile:router', 'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal']
    common_tags.extend(common.CHECK_TAGS)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_cisco_3850(aggregator):
    run_profile_check('3850')
    # We're not covering all interfaces
    interfaces = ["Gi1/0/{}".format(i) for i in range(1, 48)]
    common_tags = common.CHECK_TAGS + ['snmp_host:Cat-3850-4th-Floor.companyname.local', 'snmp_profile:cisco-3850']
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    sensors = [1006, 1007, 1008, 2006, 2007, 2008]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)
    frus = [1001, 1010, 2001, 2010]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [1000, 2000]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in CIE_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for source in range(1, 3):
        env_tags = ['power_source:{}'.format(source)]
        aggregator.assert_metric(
            'snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=env_tags + common_tags
        )

    aggregator.assert_metric(
        'snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags,
    )

    aggregator.assert_metric('snmp.cswStackPortOperStatus', metric_type=aggregator.GAUGE)

    for switch, mac_addr in [(1, '0x046c9d42b080'), (2, '0xdccec1430680')]:
        tags = ['entity_name:Switch {}'.format(switch), 'mac_addr:{}'.format(mac_addr)] + common_tags
        aggregator.assert_metric('snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=tags)

    frus = [1011, 1012, 1013, 2011, 2012, 2013]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    for metrics in MEMORY_METRICS:
        for pool in ['Processor', 'IOS Process stack']:
            tags = ['mem_pool_name:{}'.format(pool)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metrics), metric_type=aggregator.GAUGE, tags=tags)

    neighbor_metrics = [
        ('ospfNbrEvents', aggregator.RATE),
        ('ospfNbrState', aggregator.GAUGE),
        ('ospfNbrLsRetransQLen', aggregator.GAUGE),
    ]
    for metric, metric_type in neighbor_metrics:
        tags = ['neighbor_ip:192.29.116.26', 'neighbor_id:192.29.66.79'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=metric_type, tags=tags, count=1)

    lls_metrics = ['ospfIfRetransInterval', 'ospfIfState']
    for metric in lls_metrics:
        tags = ['ospf_ip_addr:192.29.116.25'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for temp_index in [1006, 1007, 1008, 2006, 2007, 2008]:
        env_tag = ['temp_index:{}'.format(temp_index), 'temp_state:1']
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue', metric_type=aggregator.GAUGE, tags=env_tag + common_tags
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_meraki_cloud_controller(aggregator):
    run_profile_check('meraki-cloud-controller')

    common_tags = common.CHECK_TAGS + ['snmp_profile:meraki-cloud-controller']
    dev_metrics = ['devStatus', 'devClientCount']
    dev_tags = ['device:Gymnasium', 'product:MR16-HW', 'network:L_NETWORK'] + common_tags
    for metric in dev_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=dev_tags, count=1)

    if_tags = ['interface:wifi0', 'index:4'] + common_tags
    if_metrics = ['devInterfaceSentPkts', 'devInterfaceRecvPkts', 'devInterfaceSentBytes', 'devInterfaceRecvBytes']
    for metric in if_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_idrac(aggregator):
    run_profile_check('idrac')

    interfaces = ['eth0', 'en1']
    common_tags = common.CHECK_TAGS + ['snmp_profile:idrac']

    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in ADAPTER_IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in SYSTEM_STATUS_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in DISK_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    batteries = ['battery1', 'battery2']
    for battery_name in batteries:
        tags = ['battery_name:{}'.format(battery_name)] + common_tags
        aggregator.assert_metric('snmp.{}'.format("batteryState"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    controllers = ['controller1', 'controller2']
    for controller in controllers:
        tags = ['controller_name:{}'.format(controller)] + common_tags
        aggregator.assert_metric(
            'snmp.{}'.format("controllerRollUpStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    devices = ['device1', 'device2']
    indexes = ['10', '20']
    for device, index in zip(devices, indexes):
        tags = ['device_descr_name:{}'.format(device), 'chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.{}'.format("pCIDeviceStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    slots = ['slot1', 'slot2']
    indexes = ['19', '21']
    for slot, index in zip(slots, indexes):
        tags = ['slot_name:{}'.format(slot), 'chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.{}'.format("systemSlotStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    tag_mappings = [('29', 'device2', '0x9e00e0291401'), ('3', 'device1', '0x9e00e0291401')]
    for index, device, mac in tag_mappings:
        tags = [
            'chassis_index:{}'.format(index),
            'device_fqdd:{}'.format(device),
            'mac_addr:{}'.format(mac),
        ] + common_tags
        aggregator.assert_metric(
            'snmp.{}'.format("networkDeviceStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    indexes = ['3', '31']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.{}'.format("systemBIOSStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1)

    indexes = ['9', '18']
    probe_types = ['26', '26']
    for index, probe_type in zip(indexes, probe_types):
        tags = ['chassis_index:{}'.format(index), 'probe_type:{}'.format(probe_type)] + common_tags
        for gauge in PROBE_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    indexes = ['12', '22']
    probe_types = ['6', '3']
    for index, probe_type in zip(indexes, probe_types):
        tags = ['chassis_index:{}'.format(index), 'probe_type:{}'.format(probe_type)] + common_tags
        for gauge in VOLTAGE_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    indexes = ['29', '22']
    device_types = ['26', '4']
    for index, device_type in zip(indexes, device_types):
        tags = ['chassis_index:{}'.format(index), 'device_type:{}'.format(device_type)] + common_tags
        aggregator.assert_metric(
            'snmp.{}'.format("memoryDeviceStatus"), metric_type=aggregator.GAUGE, tags=tags, count=1
        )

    for gauge in DRS_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_cisco_nexus(aggregator):
    run_profile_check('cisco_nexus')

    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 9)]

    common_tags = common.CHECK_TAGS + ['snmp_host:Nexus-eu1.companyname.managed', 'snmp_profile:cisco-nexus']

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    sensors = [1, 9, 11, 12, 12, 14, 17, 26, 29, 31]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)

    frus = [6, 7, 15, 16, 19, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [3173, 6692, 11571, 19529, 30674, 38253, 52063, 54474, 55946, 63960]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for (index, state) in [(3, 3), (6, 6), (8, 6), (11, 6), (13, 3), (14, 6), (20, 6), (21, 4), (31, 5)]:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue',
            metric_type=aggregator.GAUGE,
            tags=['temp_state:{}'.format(state), 'temp_index:{}'.format(index)] + common_tags,
        )

    aggregator.assert_metric(
        'snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=['power_source:1'] + common_tags,
    )

    aggregator.assert_metric(
        'snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags,
    )

    aggregator.assert_metric('snmp.cswStackPortOperStatus', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=['mac_addr:0xffffffffffff'] + common_tags
    )

    frus = [2, 7, 8, 21, 26, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_dell_poweredge(aggregator):
    run_profile_check('dell-poweredge')

    # Poweredge
    sys_mem_gauges = [
        'operatingSystemMemoryAvailablePhysicalSize',
        'operatingSystemMemoryTotalPageFileSize',
        'operatingSystemMemoryAvailablePageFileSize',
        'operatingSystemMemoryTotalVirtualSize',
        'operatingSystemMemoryAvailableVirtualSize',
    ]
    power_supply_gauges = [
        'powerSupplyStatus',
        'powerSupplyOutputWatts',
        'powerSupplyMaximumInputVoltage',
        'powerSupplyCurrentInputVoltage',
    ]

    temperature_probe_gauges = ['temperatureProbeStatus', 'temperatureProbeReading']

    processor_device_gauges = ['processorDeviceStatus', 'processorDeviceThreadCount']

    cache_device_gauges = ['cacheDeviceStatus', 'cacheDeviceMaximumSize', 'cacheDeviceCurrentSize']

    memory_device_gauges = ['memoryDeviceStatus', 'memoryDeviceFailureModes']

    idrac_gauges = (
        ['batteryState', 'controllerRollUpStatus', 'pCIDeviceStatus', 'systemSlotStatus', 'systemBIOSStatus']
        + VOLTAGE_GAUGES
        + PROBE_GAUGES
    )

    common_tags = common.CHECK_TAGS + ['snmp_profile:dell-poweredge']

    chassis_indexes = [29, 31]
    for chassis_index in chassis_indexes:
        tags = ['chassis_index:{}'.format(chassis_index)] + common_tags
        for metric in sys_mem_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [5, 17]
    for index in indexes:
        tags = ['chassis_index:4', 'index:{}'.format(index)] + common_tags
        for metric in power_supply_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [13]
    for index in indexes:
        tags = ['chassis_index:18', 'index:{}'.format(index)] + common_tags
        for metric in temperature_probe_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [17, 28]
    for index in indexes:
        tags = ['chassis_index:5', 'index:{}'.format(index)] + common_tags
        for metric in processor_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    indexes = [15, 27]
    for index in indexes:
        tags = ['chassis_index:11', 'index:{}'.format(index)] + common_tags
        for metric in cache_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    serial_numbers = ['forward zombies acted Jaded', 'kept oxen their their oxen oxen']
    for serial_number in serial_numbers:
        tags = ['serial_number_name:{}'.format(serial_number), 'chassis_index:1'] + common_tags
        for metric in memory_device_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    ip_addresses = ['66.97.1.103', '62.148.76.32', '45.3.243.155']
    for ip_address in ip_addresses:
        tags = ['ip_address:{}'.format(ip_address)] + common_tags
        aggregator.assert_metric('snmp.networkDeviceStatus', metric_type=aggregator.GAUGE, tags=tags, at_least=1)

    # Intel Adapter
    interfaces = ['eth0', 'en1']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in ADAPTER_IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    # IDRAC
    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in SYSTEM_STATUS_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in DISK_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for gauge in idrac_gauges:
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE)

    aggregator.assert_all_metrics_covered()


def test_hp_ilo4(aggregator):
    run_profile_check('hp_ilo4')

    status_gauges = [
        'cpqHeCritLogCondition',
        'cpqHeCorrMemLogStatus',
        'cpqHeCorrMemLogCondition',
        'cpqHeAsrStatus',
        'cpqHeAsrPost',
        'cpqHeAsrCondition',
        'cpqHeAsrNetworkAccessStatus',
        'cpqHeThermalCondition',
        'cpqHeThermalTempStatus',
        'cpqHeThermalSystemFanStatus',
        'cpqHeThermalCpuFanStatus',
        'cpqNicVtVirusActivity',
        'cpqSm2CntlrServerPowerState',
        'cpqSm2CntlrBatteryStatus',
        'cpqSm2CntlrRemoteSessionStatus',
        'cpqSm2CntlrInterfaceStatus',
    ]

    cpqhlth_counts = ['cpqHeSysUtilLifeTime', 'cpqHeAsrRebootCount', 'cpqHeCorrMemTotalErrs']

    cpqhlth_gauges = ['cpqHeSysUtilEisaBusMin', 'cpqHePowerMeterCurrReading']

    cpqsm2_gauges = [
        'cpqSm2CntlrBatteryPercentCharged',
        'cpqSm2CntlrSelfTestErrors',
        'cpqSm2EventTotalEntries',
    ]

    EMBEDDED = 2
    PCMCIA = 3
    card_locations = [EMBEDDED, PCMCIA]
    network_card_counts = [
        'cpqSm2NicXmitBytes',
        'cpqSm2NicXmitTotalPackets',
        'cpqSm2NicXmitDiscardPackets',
        'cpqSm2NicXmitErrorPackets',
        'cpqSm2NicXmitQueueLength',
        'cpqSm2NicRecvBytes',
        'cpqSm2NicRecvTotalPackets',
        'cpqSm2NicRecvDiscardPackets',
        'cpqSm2NicRecvErrorPackets',
        'cpqSm2NicRecvUnknownPackets',
    ]

    interfaces = ['eth0', 'en1']
    phys_adapter_counts = [
        'cpqNicIfPhysAdapterGoodTransmits',
        'cpqNicIfPhysAdapterGoodReceives',
        'cpqNicIfPhysAdapterBadTransmits',
        'cpqNicIfPhysAdapterBadReceives',
        'cpqNicIfPhysAdapterInOctets',
        'cpqNicIfPhysAdapterOutOctets',
    ]
    phys_adapter_gauges = ['cpqNicIfPhysAdapterSpeed', 'cpqNicIfPhysAdapterSpeedMbps']

    temperature_sensors = [1, 13, 28]
    batteries = [1, 3, 4, 5]

    common_tags = common.CHECK_TAGS + ['snmp_profile:hp-ilo4']

    for metric in status_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in cpqhlth_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in cpqhlth_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in cpqsm2_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for index in temperature_sensors:
        tags = ['temperature_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeTemperatureCelsius', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cpqHeTemperatureCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for index in batteries:
        tags = ['battery_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeSysBatteryCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cpqHeSysBatteryStatus', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for location in card_locations:
        tags = ['nic_stats_location:{}'.format(location)] + common_tags
        for metric in network_card_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in phys_adapter_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in phys_adapter_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_proliant(aggregator):
    run_profile_check('hpe-proliant')

    common_tags = common.CHECK_TAGS + ['snmp_profile:hpe-proliant']

    cpu_gauges = [
        "cpqSeCpuSlot",
        "cpqSeCpuSpeed",
        "cpqSeCpuStatus",
        "cpqSeCpuExtSpeed",
        "cpqSeCpuCore",
        "cpqSeCPUCoreMaxThreads",
        "cpqSeCpuPrimary",
    ]
    cpu_indexes = [0, 4, 6, 8, 13, 15, 26, 27]
    for idx in cpu_indexes:
        tags = ['cpu_index:{}'.format(idx)] + common_tags
        for metric in cpu_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpu_util_gauges = ["cpqHoCpuUtilMin", "cpqHoCpuUtilFiveMin", "cpqHoCpuUtilThirtyMin", "cpqHoCpuUtilHour"]
    cpu_unit_idx = [4, 7, 13, 20, 22, 23, 29]
    for idx in cpu_unit_idx:
        tags = ['cpu_unit_index:{}'.format(idx)] + common_tags
        for metric in cpu_util_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    file_sys_gauges = [
        "cpqHoFileSysSpaceTotal",
        "cpqHoFileSysSpaceUsed",
        "cpqHoFileSysPercentSpaceUsed",
        "cpqHoFileSysAllocUnitsTotal",
        "cpqHoFileSysAllocUnitsUsed",
        "cpqHoFileSysStatus",
    ]
    file_sys_idx = [5, 8, 11, 15, 19, 21, 28, 30]
    for idx in file_sys_idx:
        tags = ['file_sys_index:{}'.format(idx)] + common_tags
        for metric in file_sys_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    memory_gauges = [
        "cpqSiMemModuleSize",
        "cpqSiMemModuleType",
        "cpqSiMemModuleSpeed",
        "cpqSiMemModuleTechnology",
        "cpqSiMemModuleECCStatus",
        "cpqSiMemModuleFrequency",
        "cpqSiMemModuleCellStatus",
    ]
    memory_idx = [(6, 16), (7, 17), (7, 30), (8, 20), (10, 4), (15, 27), (20, 14), (21, 14), (23, 0), (28, 20)]
    for board_idx, mem_module_index in memory_idx:
        tags = ['mem_board_index:{}'.format(board_idx), "mem_module_index:{}".format(mem_module_index)] + common_tags
        for metric in memory_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    drive_counts = [
        "cpqDaPhyDrvUsedReallocs",
        "cpqDaPhyDrvRefHours",
        "cpqDaPhyDrvHardReadErrs",
        "cpqDaPhyDrvRecvReadErrs",
        "cpqDaPhyDrvHardWriteErrs",
        "cpqDaPhyDrvRecvWriteErrs",
        "cpqDaPhyDrvHSeekErrs",
        "cpqDaPhyDrvSeekErrs",
    ]
    drive_gauges = [
        "cpqDaPhyDrvStatus",
        "cpqDaPhyDrvFactReallocs",
        "cpqDaPhyDrvSpinupTime",
        "cpqDaPhyDrvSize",
        "cpqDaPhyDrvSmartStatus",
        "cpqDaPhyDrvCurrentTemperature",
    ]
    drive_idx = [(0, 2), (0, 28), (8, 31), (9, 24), (9, 28), (10, 17), (11, 4), (12, 20), (18, 22), (23, 2)]
    for drive_cntrl_idx, drive_index in drive_idx:
        tags = ['drive_cntrl_idx:{}'.format(drive_cntrl_idx), "drive_index:{}".format(drive_index)] + common_tags
        for metric in drive_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in drive_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for interface in ['eth0', 'eth1']:
        if_tags = ['interface:{}'.format(interface)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=if_tags, count=1
            )

        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    mem_boards = ['11', '12']
    for board in mem_boards:
        tags = ['mem_board_index:{}'.format(board)] + common_tags
        aggregator.assert_metric('snmp.cpqHeResMem2ModuleCondition', metric_type=aggregator.GAUGE, tags=tags, count=1)

    adapter_gauges = ['cpqNicIfPhysAdapterStatus', 'cpqNicIfPhysAdapterState']

    for gauge in adapter_gauges:
        tags = ['adapter_name:adapter', 'adapter_mac_addr:mac'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    power_metrics = [
        'cpqHeFltTolPowerSupplyStatus',
        'cpqHeFltTolPowerSupplyCapacityUsed',
        'cpqHeFltTolPowerSupplyCapacityMaximum',
    ]
    for gauge in power_metrics:
        tags = ['chassis_num:30'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    controller_index = ['controller_index:3'] + common_tags
    aggregator.assert_metric(
        'snmp.{}'.format("cpqDaCntlrCondition"), metric_type=aggregator.GAUGE, tags=controller_index, count=1
    )

    thermal_metrics = ['cpqHeThermalCondition', 'cpqHeSysUtilLifeTime', 'cpqHeFltTolPwrSupplyStatus']

    for metric in thermal_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_generic_host_resources(aggregator):
    instance = common.generate_instance_config([])

    instance['community_string'] = 'generic_host'
    instance['enforce_mib_constraints'] = False
    instance['profile'] = 'generic'

    init_config = {'profiles': {'generic': {'definition_file': '_generic-host-resources.yaml'}}}
    check = SnmpCheck('snmp', init_config, [instance])
    check.check(instance)

    common_tags = common.CHECK_TAGS + ['snmp_profile:generic']

    sys_metrics = [
        'snmp.hrSystemUptime',
        'snmp.hrSystemNumUsers',
        'snmp.hrSystemProcesses',
        'snmp.hrSystemMaxProcesses',
    ]
    for metric in sys_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_metric('snmp.hrStorageAllocationUnits', count=2)
    aggregator.assert_metric('snmp.hrStorageSize', count=2)
    aggregator.assert_metric('snmp.hrStorageUsed', count=2)
    aggregator.assert_metric('snmp.hrStorageAllocationFailures', count=2)

    aggregator.assert_metric('snmp.hrProcessorLoad', count=2)

    aggregator.assert_all_metrics_covered()


def test_palo_alto(aggregator):
    run_profile_check('pan-common')

    common_tags = common.CHECK_TAGS + ['snmp_profile:palo-alto']

    session = [
        'panSessionUtilization',
        'panSessionMax',
        'panSessionActive',
        'panSessionActiveTcp',
        'panSessionActiveUdp',
        'panSessionActiveICMP',
        'panSessionActiveSslProxy',
        'panSessionSslProxyUtilization',
    ]

    global_protect = [
        'panGPGWUtilizationPct',
        'panGPGWUtilizationMaxTunnels',
        'panGPGWUtilizationActiveTunnels',
    ]

    entity = [
        'panEntityTotalPowerAvail',
        'panEntityTotalPowerUsed',
    ]

    entry = ['panEntryFRUModulePowerUsed', 'panEntryFRUModuleNumPorts']

    for metric in session:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in global_protect:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in entity:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in entry:
        # Needs cross table entPhysicalIsFRU tag
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)
    # Needs cross table entLogicalDescr tag
    aggregator.assert_metric('snmp.panEntryFanTrayPowerUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_all_metrics_covered()


def test_cisco_asa_5525(aggregator):
    run_profile_check('cisco_asa_5525')

    common_tags = common.CHECK_TAGS + ['snmp_profile:cisco-asa-5525', 'snmp_host:kept']

    for metric in TCP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in UDP_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    if_tags = ['interface:eth0'] + common_tags
    for metric in IF_COUNTS:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=if_tags, count=1
        )

    for metric in IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    for metric in IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=if_tags, count=1)

    aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1)

    frus = [3, 4, 5, 7, 16, 17, 24, 25]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in FRU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [7746]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in CPU_METRICS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    sensor_tags = ['sensor_id:31', 'sensor_type:9'] + common_tags
    aggregator.assert_metric('snmp.entPhySensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    aggregator.assert_metric(
        'snmp.cfwConnectionStatValue', metric_type=aggregator.GAUGE, tags=['stat_type:2'] + common_tags
    )
    aggregator.assert_metric(
        'snmp.cfwConnectionStatValue', metric_type=aggregator.GAUGE, tags=['stat_type:5'] + common_tags
    )

    aggregator.assert_metric('snmp.crasNumDeclinedSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.crasNumSetupFailInsufResources', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags
    )
    aggregator.assert_metric('snmp.cipSecGlobalActiveTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cipSecGlobalHcInOctets', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.cipSecGlobalHcOutOctets', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    for (index, state) in [(3, 3), (6, 6), (8, 6), (11, 6), (13, 3), (14, 6), (20, 6), (21, 4), (31, 5)]:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue',
            metric_type=aggregator.GAUGE,
            tags=['temp_state:{}'.format(state), 'temp_index:{}'.format(index)] + common_tags,
        )

    aggregator.assert_metric(
        'snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=['power_source:1'] + common_tags,
    )

    aggregator.assert_metric(
        'snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags,
    )

    aggregator.assert_metric('snmp.cswStackPortOperStatus', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(
        'snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=['mac_addr:0xffffffffffff'] + common_tags
    )

    frus = [2, 7, 8, 21, 26, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        aggregator.assert_metric(
            'snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=['fru:{}'.format(fru)] + common_tags
        )

    for metrics in MEMORY_METRICS:
        tags = ['mem_pool_name:test_pool'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metrics), metric_type=aggregator.GAUGE, tags=tags)

    for conn in [1, 2, 5]:
        conn_tags = ['connection_type:{}'.format(conn)] + common_tags
        aggregator.assert_metric('snmp.cfwConnectionStatCount', metric_type=aggregator.RATE, tags=conn_tags)

    aggregator.assert_metric(
        'snmp.cfwHardwareStatusValue', metric_type=aggregator.GAUGE, tags=['hardware_type:3'] + common_tags
    )

    for switch in [4684, 4850, 8851, 9997, 15228, 16580, 24389, 30813, 36264]:
        aggregator.assert_metric(
            'snmp.cvsChassisUpTime',
            metric_type=aggregator.GAUGE,
            tags=['chassis_switch_id:{}'.format(switch)] + common_tags,
        )
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_cisco_csr(aggregator):
    run_profile_check('cisco-csr1000v')

    common_tags = common.CHECK_TAGS + ['snmp_profile:cisco-csr1000v']

    tags = ['neighbor:244.12.239.177'] + common_tags
    for metric in PEER_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    for metric in PEER_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_checkpoint_firewall(aggregator):
    run_profile_check('checkpoint-firewall')

    common_tags = common.CHECK_TAGS + ['snmp_profile:checkpoint-firewall']

    cpu_metrics = [
        'multiProcUserTime',
        'multiProcSystemTime',
        'multiProcIdleTime',
        'multiProcUsage',
    ]
    cpu_cores = [7097, 13039, 13761, 28994, 29751, 33826, 40053, 48847, 61593, 65044]
    for core in cpu_cores:
        tags = ['cpu_core:{}'.format(core)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_metric('snmp.procNum', metric_type=aggregator.GAUGE, tags=common_tags)

    mem_metrics = ['memTotalReal64', 'memActiveReal64', 'memFreeReal64', 'memTotalVirtual64', 'memActiveVirtual64']
    for metric in mem_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    disk_metrics = [
        'multiDiskSize',
        'multiDiskUsed',
        'multiDiskFreeTotalBytes',
        'multiDiskFreeAvailableBytes',
        'multiDiskFreeTotalPercent',
        'multiDiskFreeAvailablePercent',
    ]
    appliance_metrics = [
        'fanSpeedSensorValue',
        'fanSpeedSensorStatus',
        'tempertureSensorValue',
        'tempertureSensorStatus',
    ]
    common_indices = range(10)
    common_names = ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth']
    for idx in common_indices:
        name = common_names[idx]
        tags = ['disk_index:{}'.format(idx), 'disk_name:{}'.format(name)] + common_tags
        for metric in disk_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

        tags = ['sensor_index:{}'.format(idx), 'sensor_name:{}'.format(name)] + common_tags
        for metric in appliance_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    fw_count_metrics = ['fwAccepted', 'fwDropped', 'fwRejected']
    for metric in fw_count_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags)

    fw_gauge_metrics = ['fwNumConn', 'fwPeakNumConn']
    for metric in fw_gauge_metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_all_metrics_covered()


def test_arista(aggregator):
    run_profile_check('arista')

    common_tags = common.CHECK_TAGS + ['snmp_profile:arista']

    aggregator.assert_metric(
        'snmp.aristaEgressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:13', 'queue_index:10'],
        count=1,
    )
    aggregator.assert_metric(
        'snmp.aristaEgressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:28', 'queue_index:22'],
        count=1,
    )
    aggregator.assert_metric(
        'snmp.aristaIngressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:7', 'queue_index:25'],
        count=1,
    )
    aggregator.assert_metric(
        'snmp.aristaIngressQueuePktsDropped',
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=common_tags + ['interface_index:8', 'queue_index:24'],
        count=1,
    )

    for (sensor_id, sensor_type) in [(1, 11), (7, 8)]:
        sensor_tags = ['sensor_id:{}'.format(sensor_id), 'sensor_type:{}'.format(sensor_type)] + common_tags
        aggregator.assert_metric('snmp.entPhySensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)
        aggregator.assert_metric('snmp.entPhySensorOperStatus', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_aruba(aggregator):
    run_profile_check('aruba')

    common_tags = common.CHECK_TAGS + ['snmp_profile:aruba']

    for fan in [18, 28]:
        fan_tags = common_tags + ['fan_index:{}'.format(fan)]
        aggregator.assert_metric('snmp.sysExtFanStatus', metric_type=aggregator.GAUGE, tags=fan_tags, count=1)
    for psu in [1, 17]:
        psu_tags = common_tags + ['powersupply_index:{}'.format(psu)]
        aggregator.assert_metric('snmp.sysExtPowerSupplyStatus', metric_type=aggregator.GAUGE, tags=psu_tags, count=1)
    for proc in [11, 26]:
        proc_tags = common_tags + ['processor_index:{}'.format(proc)]
        aggregator.assert_metric('snmp.sysExtProcessorLoad', metric_type=aggregator.GAUGE, tags=proc_tags, count=1)
    for mem in [3, 20]:
        mem_tags = common_tags + ['memory_index:{}'.format(mem)]
        aggregator.assert_metric('snmp.sysExtMemorySize', metric_type=aggregator.GAUGE, tags=mem_tags, count=1)
        aggregator.assert_metric('snmp.sysExtMemoryUsed', metric_type=aggregator.GAUGE, tags=mem_tags, count=1)
        aggregator.assert_metric('snmp.sysExtMemoryFree', metric_type=aggregator.GAUGE, tags=mem_tags, count=1)

    aggregator.assert_metric(
        'snmp.wlsxSysExtPacketLossPercent', metric_type=aggregator.GAUGE, tags=common_tags, count=1
    )

    # OSPF metrics
    neighbor_metrics = [
        ('ospfNbrEvents', aggregator.RATE),
        ('ospfNbrState', aggregator.GAUGE),
        ('ospfNbrLsRetransQLen', aggregator.GAUGE),
    ]
    for metric, metric_type in neighbor_metrics:
        tags = ['neighbor_ip:192.29.116.26', 'neighbor_id:192.29.66.79'] + common_tags
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=metric_type, tags=tags, count=1)

    virtual_neighbor_metrics = [
        ('ospfVirtNbrState', aggregator.GAUGE),
        ('ospfVirtNbrEvents', aggregator.RATE),
        ('ospfVirtNbrLsRetransQLen', aggregator.GAUGE),
    ]
    for metric, metric_type in virtual_neighbor_metrics:
        for ip, nbr in [('74.210.82.1', '194.154.66.112'), ('122.226.86.1', '184.201.101.140')]:
            tags = ['neighbor_ip:{}'.format(ip), 'neighbor_id:{}'.format(nbr)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=metric_type, tags=tags, count=1)

    lls_metrics = ['ospfIfRetransInterval', 'ospfIfState', 'ospfIfLsaCount']
    for metric in lls_metrics:
        for ip, nbr in [('58.115.169.188', '192.29.66.79'), ('18.2.8.29', '118.246.193.247')]:
            tags = ['ospf_ip_addr:{}'.format(ip), 'neighbor_id:{}'.format(nbr)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    virtual_lls_metrics = ['ospfVirtIfRetransInterval', 'ospfVirtIfState', 'ospfVirtIfLsaCount']
    for metric in virtual_lls_metrics:
        for nbr in ['194.154.66.112', '184.201.101.140']:
            tags = ['neighbor_id:{}'.format(nbr)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_chatsworth(aggregator):
    run_profile_check('chatsworth')

    # Legacy global tags are applied to all metrics
    legacy_global_tags = [
        'legacy_pdu_macaddress:00:0E:D3:AA:CC:EE',
        'legacy_pdu_model:P10-1234-ABC',
        'legacy_pdu_name:legacy-name1',
        'legacy_pdu_version:1.2.3',
    ]
    common_tags = common.CHECK_TAGS + legacy_global_tags + ['snmp_profile:chatsworth_pdu']

    # Legacy metrics
    legacy_pdu_tags = common_tags
    legacy_pdu_gauge_metrics = [
        'snmp.pduRole',
        'snmp.outOfService',
    ]
    legacy_pdu_monotonic_count_metrics = []
    for line in range(1, 4):
        legacy_pdu_gauge_metrics.append('snmp.line{}curr'.format(line))
    for branch in range(1, 3):
        legacy_pdu_gauge_metrics.append('snmp.temperatureProbe{}'.format(branch))
        legacy_pdu_gauge_metrics.append('snmp.humidityProbe{}'.format(branch))
        for xyz in ['xy', 'yz', 'zx']:
            legacy_pdu_monotonic_count_metrics.append('snmp.energy{}{}s'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.voltage{}{}'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.power{}{}'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.powerFact{}{}'.format(xyz, branch))
            legacy_pdu_gauge_metrics.append('snmp.current{}{}'.format(xyz, branch))
    for branch in range(1, 25):
        legacy_pdu_monotonic_count_metrics.append('snmp.receptacleEnergyoutlet{}s'.format(branch))
        legacy_pdu_gauge_metrics.append('snmp.outlet{}Current'.format(branch))

    for metric in legacy_pdu_gauge_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, tags=legacy_pdu_tags, count=1)
    for metric in legacy_pdu_monotonic_count_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.MONOTONIC_COUNT, tags=legacy_pdu_tags, count=1)

    # New metrics
    pdu_tags = common_tags + [
        'pdu_cabinetid:cab1',
        'pdu_ipaddress:42.2.210.224',
        'pdu_macaddress:0x00249b3503f6',
        'pdu_model:model1',
        'pdu_name:name1',
        'pdu_version:v1.1',
    ]
    aggregator.assert_metric('snmp.cpiPduNumberBranches', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduNumberOutlets', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduOutOfService', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduUpgrade', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduChainRole', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)
    aggregator.assert_metric('snmp.cpiPduTotalPower', metric_type=aggregator.GAUGE, tags=pdu_tags, count=1)

    for lock in [1, 2]:
        lock_tags = common_tags + ['lock_id:{}'.format(lock)]
        aggregator.assert_metric('snmp.cpiPduEasStatus', metric_type=aggregator.GAUGE, tags=lock_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduDoorStatus', metric_type=aggregator.GAUGE, tags=lock_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduLockStatus', metric_type=aggregator.GAUGE, tags=lock_tags, count=1)

    for (sensor_name, sensor_index) in [('sensor1', 4), ('sensor2', 6)]:
        sensor_tags = common_tags + [
            'sensor_index:{}'.format(sensor_index),
            'sensor_name:{}'.format(sensor_name),
            'sensor_type:1',
        ]
        aggregator.assert_metric('snmp.cpiPduSensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    for line in [6, 18]:
        line_tags = common_tags + ['line_id:{}'.format(line)]
        aggregator.assert_metric('snmp.cpiPduLineCurrent', metric_type=aggregator.GAUGE, tags=line_tags, count=1)

    for branch in [1, 17]:
        branch_tags = common_tags + ['branch_id:{}'.format(branch)]
        aggregator.assert_metric('snmp.cpiPduBranchCurrent', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduBranchMaxCurrent', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduBranchVoltage', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduBranchPower', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric(
            'snmp.cpiPduBranchPowerFactor', metric_type=aggregator.GAUGE, tags=branch_tags, count=1
        )
        aggregator.assert_metric('snmp.cpiPduBranchStatus', metric_type=aggregator.GAUGE, tags=branch_tags, count=1)
        aggregator.assert_metric(
            'snmp.cpiPduBranchEnergy', metric_type=aggregator.MONOTONIC_COUNT, tags=branch_tags, count=1
        )

    for (outlet_id, outlet_branch, outlet_name) in [(7, 29, 'outlet1'), (16, 23, 'outlet2')]:
        outlet_tags = common_tags + [
            'outlet_id:{}'.format(outlet_id),
            'outlet_branchid:{}'.format(outlet_branch),
            'outlet_name:{}'.format(outlet_name),
        ]
        aggregator.assert_metric('snmp.cpiPduOutletCurrent', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduOutletVoltage', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduOutletPower', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric('snmp.cpiPduOutletStatus', metric_type=aggregator.GAUGE, tags=outlet_tags, count=1)
        aggregator.assert_metric(
            'snmp.cpiPduOutletEnergy', metric_type=aggregator.MONOTONIC_COUNT, tags=outlet_tags, count=1
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_metric_type=False)


def test_isilon(aggregator):
    run_profile_check('isilon')

    common_tags = common.CHECK_TAGS + [
        'snmp_profile:isilon',
        'cluster_name:testcluster1',
        'node_name:node1',
        'node_type:1',
    ]

    cluster_rates = [
        'clusterIfsInBytes',
        'clusterIfsOutBytes',
    ]

    node_rates = [
        'nodeIfsOutBytes',
        'nodeIfsInBytes',
    ]

    protocol_metrics = [
        'protocolOpsPerSecond',
        'latencyMin',
        'latencyMax',
        'latencyAverage',
    ]

    quota_metrics = ['quotaHardThreshold', 'quotaSoftThreshold', 'quotaUsage', 'quotaAdvisoryThreshold']

    quota_ids_types = [
        (422978632, 1),
        (153533730, 5),
        (3299369987, 4),
        (2149993012, 3),
        (1424325378, 1),
        (4245321451, 0),
        (2328145711, 1),
        (1198032230, 4),
        (1232918362, 1),
        (1383990869, 1),
    ]
    for metric in quota_metrics:
        for qid, qtype in quota_ids_types:
            tags = ['quota_id:{}'.format(qid), 'quota_type:{}'.format(qtype)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=tags, count=1)

    for metric in protocol_metrics:
        for num in range(1, 3):
            tags = ['protocol_name:testprotocol{}'.format(num)] + common_tags
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_metric('snmp.clusterHealth', metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in cluster_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=common_tags, count=1)

    aggregator.assert_metric('snmp.nodeHealth', metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in node_rates:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.RATE, tags=common_tags, count=1)

    for fan in [4, 6, 10, 11, 14, 21, 22, 23, 25, 30]:
        tags = ['fan_name:testfan', 'fan_number:{}'.format(fan)] + common_tags
        aggregator.assert_metric('snmp.fanSpeed', metric_type=aggregator.GAUGE, tags=tags, count=1)

    for status, bay in [('SMARTFAIL', 1), ('HEALTHY', 2), ('DEAD', 3)]:
        tags = common_tags + ['disk_status:{}'.format(status), 'disk_bay:{}'.format((bay))]
        aggregator.assert_metric('snmp.diskSizeBytes', metric_type=aggregator.RATE, tags=tags)

    aggregator.assert_metric('snmp.ifsUsedBytes', metric_type=aggregator.RATE, tags=common_tags, count=1)
    aggregator.assert_metric('snmp.ifsTotalBytes', metric_type=aggregator.RATE, tags=common_tags, count=1)


def test_apc_ups(aggregator):
    run_profile_check('apc_ups')
    profile_tags = [
        'snmp_profile:apc_ups',
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
    ]

    tags = common.CHECK_TAGS + profile_tags
    metrics = [
        'upsAdvBatteryNumOfBadBattPacks',
        'upsAdvBatteryReplaceIndicator',
        'upsAdvBatteryRunTimeRemaining',
        'upsAdvBatteryTemperature',
        'upsAdvBatteryCapacity',
        'upsHighPrecInputFrequency',
        'upsHighPrecInputLineVoltage',
        'upsHighPrecOutputCurrent',
        'upsAdvInputLineFailCause',
        'upsAdvOutputLoad',
        'upsBasicBatteryTimeOnBattery',
        'upsAdvTestDiagnosticsResults',
    ]

    for metric in metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        tags=['outlet_group_name:test_outlet'] + tags,
    )
    aggregator.assert_all_metrics_covered()
