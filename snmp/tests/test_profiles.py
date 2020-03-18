# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.snmp import SnmpCheck

from . import common

pytestmark = pytest.mark.usefixtures("dd_environment")


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
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    if_counts = [
        'ifHCInOctets',
        'ifInErrors',
        'ifHCOutOctets',
        'ifOutErrors',
        'ifHCInBroadcastPkts',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifOutDiscards',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCOutBroadcastPkts',
        'ifInDiscards',
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
    for metric in if_counts:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.MONOTONIC_COUNT,
                tags=['interface:{}'.format(interface)] + tags,
                count=1,
            )
    for metric in if_gauges:
        for interface in interfaces:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=['interface:{}'.format(interface)] + tags,
                count=1,
            )
    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_router(aggregator):
    run_profile_check('network')

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = [
        'ifInErrors',
        'ifInDiscards',
        'ifOutErrors',
        'ifOutDiscards',
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    ip_counts = [
        'ipSystemStatsHCInReceives',
        'ipSystemStatsHCInOctets',
        'ipSystemStatsInHdrErrors',
        'ipSystemStatsInNoRoutes',
        'ipSystemStatsInAddrErrors',
        'ipSystemStatsInUnknownProtos',
        'ipSystemStatsInTruncatedPkts',
        'ipSystemStatsHCInForwDatagrams',
        'ipSystemStatsReasmReqds',
        'ipSystemStatsReasmOKs',
        'ipSystemStatsReasmFails',
        'ipSystemStatsInDiscards',
        'ipSystemStatsHCInDelivers',
        'ipSystemStatsHCOutRequests',
        'ipSystemStatsOutNoRoutes',
        'ipSystemStatsHCOutForwDatagrams',
        'ipSystemStatsOutDiscards',
        'ipSystemStatsOutFragReqds',
        'ipSystemStatsOutFragOKs',
        'ipSystemStatsOutFragFails',
        'ipSystemStatsOutFragCreates',
        'ipSystemStatsHCOutTransmits',
        'ipSystemStatsHCOutOctets',
        'ipSystemStatsHCInMcastPkts',
        'ipSystemStatsHCInMcastOctets',
        'ipSystemStatsHCOutMcastPkts',
        'ipSystemStatsHCOutMcastOctets',
        'ipSystemStatsHCInBcastPkts',
        'ipSystemStatsHCOutBcastPkts',
    ]
    ip_if_counts = [
        'ipIfStatsHCInOctets',
        'ipIfStatsInHdrErrors',
        'ipIfStatsInNoRoutes',
        'ipIfStatsInAddrErrors',
        'ipIfStatsInUnknownProtos',
        'ipIfStatsInTruncatedPkts',
        'ipIfStatsHCInForwDatagrams',
        'ipIfStatsReasmReqds',
        'ipIfStatsReasmOKs',
        'ipIfStatsReasmFails',
        'ipIfStatsInDiscards',
        'ipIfStatsHCInDelivers',
        'ipIfStatsHCOutRequests',
        'ipIfStatsHCOutForwDatagrams',
        'ipIfStatsOutDiscards',
        'ipIfStatsOutFragReqds',
        'ipIfStatsOutFragOKs',
        'ipIfStatsOutFragFails',
        'ipIfStatsOutFragCreates',
        'ipIfStatsHCOutTransmits',
        'ipIfStatsHCOutOctets',
        'ipIfStatsHCInMcastPkts',
        'ipIfStatsHCInMcastOctets',
        'ipIfStatsHCOutMcastPkts',
        'ipIfStatsHCOutMcastOctets',
        'ipIfStatsHCInBcastPkts',
        'ipIfStatsHCOutBcastPkts',
    ]
    common_tags = common.CHECK_TAGS + ['snmp_profile:generic-router']
    for interface in ['eth0', 'eth1']:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in ip_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in ip_if_counts:
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

    if_counts = [
        'ifInErrors',
        'ifInDiscards',
        'ifOutErrors',
        'ifOutDiscards',
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    # We only get a subset of metrics
    ip_counts = [
        'ipSystemStatsHCInReceives',
        'ipSystemStatsInHdrErrors',
        'ipSystemStatsOutFragReqds',
        'ipSystemStatsOutFragFails',
        'ipSystemStatsHCOutTransmits',
        'ipSystemStatsReasmReqds',
        'ipSystemStatsHCInMcastPkts',
        'ipSystemStatsReasmFails',
        'ipSystemStatsHCOutMcastPkts',
    ]
    interfaces = ['1.0', 'mgmt', '/Common/internal', '/Common/http-tunnel', '/Common/socks-tunnel']
    common_tags = ['snmp_profile:router', 'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal']
    common_tags.extend(common.CHECK_TAGS)
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in ip_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


def test_3850(aggregator):
    run_profile_check('3850')

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = ['ifInErrors', 'ifInDiscards', 'ifOutErrors', 'ifOutDiscards']
    ifx_counts = [
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    # We're not covering all interfaces
    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 48)]
    common_tags = common.CHECK_TAGS + ['snmp_host:Cat-3850-4th-Floor.companyname.local', 'snmp_profile:cisco-3850']
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    interfaces = ["Gi1/0/{}".format(i) for i in range(1, 48)]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in ifx_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )
    sensors = [1006, 1007, 1008, 2006, 2007, 2008]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)
    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [1001, 1010, 2001, 2010]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [1000, 2000]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    cie_metrics = ["cieIfLastInTime", "cieIfLastOutTime", "cieIfInputQueueDrops", "cieIfOutputQueueDrops"]
    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in cie_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

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

    if_counts = [
        'adapterRxPackets',
        'adapterTxPackets',
        'adapterRxBytes',
        'adapterTxBytes',
        'adapterRxErrors',
        'adapterTxErrors',
        'adapterRxDropped',
        'adapterTxDropped',
        'adapterRxMulticast',
        'adapterCollisions',
    ]
    status_gauges = [
        'systemStateChassisStatus',
        'systemStatePowerUnitStatusRedundancy',
        'systemStatePowerSupplyStatusCombined',
        'systemStateAmperageStatusCombined',
        'systemStateCoolingUnitStatusRedundancy',
        'systemStateCoolingDeviceStatusCombined',
        'systemStateTemperatureStatusCombined',
        'systemStateMemoryDeviceStatusCombined',
        'systemStateChassisIntrusionStatusCombined',
        'systemStatePowerUnitStatusCombined',
        'systemStateCoolingUnitStatusCombined',
        'systemStateProcessorDeviceStatusCombined',
        'systemStateTemperatureStatisticsStatusCombined',
    ]
    disk_gauges = [
        'physicalDiskState',
        'physicalDiskCapacityInMB',
        'physicalDiskUsedSpaceInMB',
        'physicalDiskFreeSpaceInMB',
    ]
    interfaces = ['eth0', 'en1']
    common_tags = common.CHECK_TAGS + ['snmp_profile:idrac']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in status_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in disk_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_cisco_nexus(aggregator):
    run_profile_check('cisco_nexus')

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = ['ifInErrors', 'ifInDiscards', 'ifOutErrors', 'ifOutDiscards']
    ifx_counts = [
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    if_gauges = ['ifAdminStatus', 'ifOperStatus']

    interfaces = ["GigabitEthernet1/0/{}".format(i) for i in range(1, 9)]

    common_tags = common.CHECK_TAGS + ['snmp_host:Nexus-eu1.companyname.managed', 'snmp_profile:cisco-nexus']

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )
        for metric in if_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in ifx_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    sensors = [1, 9, 11, 12, 12, 14, 17, 26, 29, 31]
    for sensor in sensors:
        tags = ['sensor_id:{}'.format(sensor), 'sensor_type:8'] + common_tags
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=tags, count=1)

    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [6, 7, 15, 16, 19, 27, 30, 31]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [3173, 6692, 11571, 19529, 30674, 38253, 52063, 54474, 55946, 63960]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

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
    if_counts = [
        'adapterRxPackets',
        'adapterTxPackets',
        'adapterRxBytes',
        'adapterTxBytes',
        'adapterRxErrors',
        'adapterTxErrors',
        'adapterRxDropped',
        'adapterTxDropped',
        'adapterRxMulticast',
        'adapterCollisions',
    ]

    interfaces = ['eth0', 'en1']
    for interface in interfaces:
        tags = ['adapter:{}'.format(interface)] + common_tags
        for count in if_counts:
            aggregator.assert_metric(
                'snmp.{}'.format(count), metric_type=aggregator.MONOTONIC_COUNT, tags=tags, count=1
            )

    # IDRAC
    status_gauges = [
        'systemStateChassisStatus',
        'systemStatePowerUnitStatusRedundancy',
        'systemStatePowerSupplyStatusCombined',
        'systemStateAmperageStatusCombined',
        'systemStateCoolingUnitStatusRedundancy',
        'systemStateCoolingDeviceStatusCombined',
        'systemStateTemperatureStatusCombined',
        'systemStateMemoryDeviceStatusCombined',
        'systemStateChassisIntrusionStatusCombined',
        'systemStatePowerUnitStatusCombined',
        'systemStateCoolingUnitStatusCombined',
        'systemStateProcessorDeviceStatusCombined',
        'systemStateTemperatureStatisticsStatusCombined',
    ]
    disk_gauges = [
        'physicalDiskState',
        'physicalDiskCapacityInMB',
        'physicalDiskUsedSpaceInMB',
        'physicalDiskFreeSpaceInMB',
    ]

    indexes = ['26', '29']
    for index in indexes:
        tags = ['chassis_index:{}'.format(index)] + common_tags
        for gauge in status_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)
    powers = ['supply1', 'supply2']
    for power in powers:
        tags = ['supply_name:{}'.format(power)] + common_tags
        aggregator.assert_metric('snmp.enclosurePowerSupplyState', metric_type=aggregator.GAUGE, tags=tags, count=1)
    disks = ['disk1', 'disk2']
    for disk in disks:
        tags = ['disk_name:{}'.format(disk)] + common_tags
        for gauge in disk_gauges:
            aggregator.assert_metric('snmp.{}'.format(gauge), metric_type=aggregator.GAUGE, tags=tags, count=1)

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

    for metric in session:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)
    for metric in global_protect:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_cisco_asa_5525(aggregator):
    run_profile_check('cisco_asa_5525')

    common_tags = common.CHECK_TAGS + ['snmp_profile:cisco-asa-5525', 'snmp_host:kept']

    tcp_counts = [
        'tcpActiveOpens',
        'tcpPassiveOpens',
        'tcpAttemptFails',
        'tcpEstabResets',
        'tcpHCInSegs',
        'tcpHCOutSegs',
        'tcpRetransSegs',
        'tcpInErrs',
        'tcpOutRsts',
    ]
    tcp_gauges = ['tcpCurrEstab']
    udp_counts = ['udpHCInDatagrams', 'udpNoPorts', 'udpInErrors', 'udpHCOutDatagrams']
    if_counts = ['ifInErrors', 'ifInDiscards', 'ifOutErrors', 'ifOutDiscards']
    if_gauges = ['ifAdminStatus', 'ifOperStatus']
    ifx_counts = [
        'ifHCInOctets',
        'ifHCInUcastPkts',
        'ifHCInMulticastPkts',
        'ifHCInBroadcastPkts',
        'ifHCOutOctets',
        'ifHCOutUcastPkts',
        'ifHCOutMulticastPkts',
        'ifHCOutBroadcastPkts',
    ]
    for metric in tcp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    for metric in tcp_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=1)

    for metric in udp_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1
        )

    if_tags = ['interface:0x42010aa40033'] + common_tags
    for metric in if_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=if_tags, count=1
        )

    for metric in if_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags, count=1)

    hc_tags = ['interface:Jaded oxen acted acted'] + common_tags
    for metric in ifx_counts:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.MONOTONIC_COUNT, tags=hc_tags, count=1
        )

    aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.MONOTONIC_COUNT, tags=common_tags, count=1)

    fru_metrics = ["cefcFRUPowerAdminStatus", "cefcFRUPowerOperStatus", "cefcFRUCurrent"]
    frus = [3, 4, 5, 7, 16, 17, 24, 25]
    for fru in frus:
        tags = ['fru:{}'.format(fru)] + common_tags
        for metric in fru_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)

    cpus = [7746]
    cpu_metrics = ["cpmCPUTotalMonIntervalValue", "cpmCPUMemoryUsed", "cpmCPUMemoryFree"]
    for cpu in cpus:
        tags = ['cpu:{}'.format(cpu)] + common_tags
        for metric in cpu_metrics:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
    sensor_tags = ['sensor_id:31', 'sensor_type:9'] + common_tags
    aggregator.assert_metric('snmp.entPhySensorValue', metric_type=aggregator.GAUGE, tags=sensor_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=1)
    aggregator.assert_all_metrics_covered()


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
