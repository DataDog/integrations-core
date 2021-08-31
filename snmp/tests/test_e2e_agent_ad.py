# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest
from tests.metrics import (
    IF_BANDWIDTH_USAGE,
    IF_COUNTS,
    IF_GAUGES,
    IF_RATES,
    IF_SCALAR_GAUGE,
    IP_COUNTS,
    IP_IF_COUNTS,
    IPX_COUNTS,
    TCP_COUNTS,
    TCP_GAUGES,
    UDP_COUNTS,
)

from . import common

pytestmark = pytest.mark.e2e


def _build_device_ip(container_ip, last_digit='1'):
    last_digit = str(last_digit)
    snmp_device = container_ip.split('.')
    snmp_device[len(snmp_device) - 1] = last_digit
    snmp_device = '.'.join(snmp_device)
    return snmp_device


@common.agent_autodiscovery_only
def test_e2e_agent_autodiscovery(dd_agent_check, container_ip, autodiscovery_ready):
    """
    Test Agent Autodiscovery

    The assertions match `snmp_listener` configuration in `datadog.yaml`.
    See `dd_environment` setup in `conftest.py`.
    """
    snmp_device = _build_device_ip(container_ip)
    subnet_prefix = ".".join(container_ip.split('.')[:3])
    aggregator = dd_agent_check({'init_config': {}, 'instances': []}, rate=True)

    # === network profile ===
    common_tags = [
        'snmp_profile:generic-router',
        'snmp_device:{}'.format(snmp_device),
        'autodiscovery_subnet:{}.0/29'.format(subnet_prefix),
        'tag1:val1',
        'tag2:val2',
    ]

    common.assert_common_metrics(aggregator, common_tags, is_e2e=True, loader='core')
    interfaces = [
        ('eth0', 'kept'),
        ('eth1', 'their forward oxen'),
    ]
    for interface, if_desc in interfaces:
        tags = ['interface:{}'.format(interface), 'interface_alias:{}'.format(if_desc)] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)
        for metric in IF_RATES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_BANDWIDTH_USAGE:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=1)
        for metric in IF_GAUGES:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=tags, count=2)
    for metric in TCP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)
    for metric in TCP_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)
    for metric in UDP_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=common_tags, count=1)
    for version in ['ipv4', 'ipv6']:
        tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS + IPX_COUNTS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)
        for metric in IP_IF_COUNTS:
            for interface in ['17', '21']:
                tags = ['ipversion:{}'.format(version), 'interface:{}'.format(interface)] + common_tags
                aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=tags, count=1)

    # ==== apc_ups profile ===
    common_tags = [
        'snmp_device:{}'.format(snmp_device),
        'autodiscovery_subnet:{}.0/28'.format(subnet_prefix),
        'snmp_profile:apc_ups',
        'model:APC Smart-UPS 600',
        'firmware_version:2.0.3-test',
        'serial_num:test_serial',
        'ups_name:testIdentName',
        'device_vendor:apc',
    ]
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

    common.assert_common_metrics(aggregator, common_tags, is_e2e=True)

    for metric in metrics:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)
    aggregator.assert_metric(
        'snmp.upsOutletGroupStatusGroupState',
        metric_type=aggregator.GAUGE,
        count=2,
        tags=['outlet_group_name:test_outlet'] + common_tags,
    )

    ups_basic_state_output_state_metrics = [
        'snmp.upsBasicStateOutputState.AVRTrimActive',
        'snmp.upsBasicStateOutputState.BatteriesDischarged',
        'snmp.upsBasicStateOutputState.LowBatteryOnBattery',
        'snmp.upsBasicStateOutputState.NoBatteriesAttached',
        'snmp.upsBasicStateOutputState.On',
        'snmp.upsBasicStateOutputState.OnLine',
        'snmp.upsBasicStateOutputState.ReplaceBattery',
    ]
    for metric in ups_basic_state_output_state_metrics:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE, count=2, tags=common_tags)

    # ==== test snmp v3 ===
    common_tags = [
        'snmp_device:{}'.format(snmp_device),
        'autodiscovery_subnet:{}.0/27'.format(subnet_prefix),
        'snmp_host:41ba948911b9',
        'snmp_profile:generic-router',
    ]

    common.assert_common_metrics(aggregator, common_tags, is_e2e=True)
    aggregator.assert_metric('snmp.sysUpTimeInstance', tags=common_tags)
    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)

    # test ignored IPs
    tags = [
        'snmp_device:{}'.format(_build_device_ip(container_ip, '2')),
        'autodiscovery_subnet:{}.0/27'.format(subnet_prefix),
        'snmp_host:41ba948911b9',
        'snmp_profile:generic-router',
    ]
    aggregator.assert_metric('snmp.devices_monitored', count=0, tags=tags)

    aggregator.assert_all_metrics_covered()
