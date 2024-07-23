# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_all_profile_metrics_and_tags_covered,
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_hp_ilo(dd_agent_check):
    profile = 'hp-ilo'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:hp-ilo',
        'snmp_host:hp-ilo.device.name',
        'device_hostname:hp-ilo.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---

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

    cpqhlth_counts = ['cpqHeAsrRebootCount', 'cpqHeCorrMemTotalErrs']

    cpqhlth_gauges = ['cpqHeSysUtilEisaBusMin', 'cpqHePowerMeterCurrReading', 'cpqHeSysUtilLifeTime']

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

    assert_common_metrics(aggregator, common_tags)

    for metric in status_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    for metric in cpqhlth_counts:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)

    for metric in cpqhlth_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    for metric in cpqsm2_gauges:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    for index in temperature_sensors:
        tags = ['temperature_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeTemperatureCelsius', metric_type=aggregator.GAUGE, tags=tags)
        aggregator.assert_metric('snmp.cpqHeTemperatureCondition', metric_type=aggregator.GAUGE, tags=tags)

    for index in batteries:
        tags = ['battery_index:{}'.format(index)] + common_tags
        aggregator.assert_metric('snmp.cpqHeSysBatteryCondition', metric_type=aggregator.GAUGE, tags=tags)
        aggregator.assert_metric('snmp.cpqHeSysBatteryStatus', metric_type=aggregator.GAUGE, tags=tags)

    for location in card_locations:
        tags = ['nic_stats_location:{}'.format(location)] + common_tags
        for metric in network_card_counts:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)

    for interface in interfaces:
        tags = ['interface:{}'.format(interface)] + common_tags
        for metric in phys_adapter_counts:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags)
        for metric in phys_adapter_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

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
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)
        for metric in drive_gauges:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags)

    # --- TEST METADATA ---
    device = {
        'description': 'hp-ilo Device Description',
        'id': 'default:' + ip_address,
        'id_tags': [
            'device_namespace:default',
            'snmp_device:' + ip_address,
        ],
        'ip_address': ip_address,
        'os_name': 'RHEL',
        'os_version': '3.10.0-862.14.4.el7.ve.x86_64',
        'product_name': 'Integrated Lights-Out',
        'name': 'hp-ilo.device.name',
        'profile': 'hp-ilo',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.232.9.4.11',
        'version': 'A04-08/12/2018',
        'tags': [
            'device_id:default:' + ip_address,
            'device_ip:' + ip_address,
            'device_namespace:default',
            'snmp_device:' + ip_address,
            'snmp_host:hp-ilo.device.name',
            'device_hostname:hp-ilo.device.name',
            'snmp_profile:hp-ilo',
        ],
        'vendor': 'hp',
        'serial_number': 'dXPEdPBE5yKtjW9xx3',
        'device_type': 'server',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
