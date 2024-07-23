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


def test_e2e_profile__hp_compaq_health(dd_agent_check):
    profile = '_hp-compaq-health'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:hp-compaq-health',
        'snmp_host:_hp-compaq-health.device.name',
        'device_hostname:_hp-compaq-health.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpqHeAsrCondition', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeAsrNetworkAccessStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeAsrPost', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeAsrRebootCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeAsrStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeCorrMemLogCondition', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeCorrMemLogStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeCorrMemTotalErrs', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeCritLogCondition', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeFltTolPwrSupplyStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHePowerMeterCurrReading', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeSysUtilEisaBusMin', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeSysUtilLifeTime', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeThermalCondition', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeThermalCpuFanStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeThermalSystemFanStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpqHeThermalTempStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['temperature_index:11'],
        ['temperature_index:13'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqHeTemperatureCelsius', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cpqHeTemperatureCondition', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['battery_index:24'],
        ['battery_index:27'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqHeSysBatteryCondition', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cpqHeSysBatteryStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem_board_index:15'],
        ['mem_board_index:7'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqHeResMem2ModuleCondition', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_num:22'],
        ['chassis_num:8'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqHeFltTolPowerSupplyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_num:22', 'power_supply_status:nvram_invalid'],
        ['chassis_num:8', 'power_supply_status:general_failure'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cpqHeFltTolPowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cpqHeFltTolPowerSupplyCapacityMaximum', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cpqHeFltTolPowerSupplyCapacityUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': '_hp-compaq-health Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_hp-compaq-health.device.name',
        'profile': 'hp-compaq-health',
        'status': 1,
        'sys_object_id': '1.2.3.1004',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
