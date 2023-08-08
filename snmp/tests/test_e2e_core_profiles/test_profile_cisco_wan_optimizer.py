# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_host_resources_base,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_cisco_wan_optimizer(dd_agent_check):
    config = create_e2e_core_test_config('cisco-wan-optimizer')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-wan-optimizer',
        'snmp_host:cisco-wan-optimizer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cceAlarmCriticalCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cceAlarmMajorCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cceAlarmMinorCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsActiveADConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsActiveOptConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsActiveOptTCPOnlyConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsActiveOptTCPPlusConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsActiveOptTCPPrepConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsActivePTConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsLoadStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsPendingConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsReservedConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsResetConn', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsTotalNormalClosedConn', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.cwoTfoStatsTotalOptConn', metric_type=aggregator.COUNT, tags=common_tags)

    tag_rows = [
        ['fan_status_index:11'],
        ['fan_status_index:16'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fan_status_index:11', 'fan_state:notFunctioning', 'fan_status_descr:oxen their but kept forward kept'],
        ['fan_status_index:16', 'fan_state:normal', 'fan_status_descr:acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fru:21'],
        ['fru:23'],
        ['fru:25'],
        ['fru:27'],
        ['fru:29'],
        ['fru:30'],
        ['fru:7'],
        ['fru:9'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFanTrayOperStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fru:21', 'cefc_fan_tray_oper_status:warning', 'cefc_fan_tray_direction:frontToBack'],
        ['fru:23', 'cefc_fan_tray_oper_status:up', 'cefc_fan_tray_direction:frontToBack'],
        ['fru:25', 'cefc_fan_tray_oper_status:unknown', 'cefc_fan_tray_direction:frontToBack'],
        ['fru:27', 'cefc_fan_tray_oper_status:unknown', 'cefc_fan_tray_direction:unknown'],
        ['fru:29', 'cefc_fan_tray_oper_status:unknown', 'cefc_fan_tray_direction:backToFront'],
        ['fru:30', 'cefc_fan_tray_oper_status:up', 'cefc_fan_tray_direction:backToFront'],
        ['fru:7', 'cefc_fan_tray_oper_status:up', 'cefc_fan_tray_direction:backToFront'],
        ['fru:9', 'cefc_fan_tray_oper_status:warning', 'cefc_fan_tray_direction:unknown'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFanTrayStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-wan-optimizer Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-wan-optimizer.device.name',
        'profile': 'cisco-wan-optimizer',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.1354',
        'vendor': 'cisco',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
