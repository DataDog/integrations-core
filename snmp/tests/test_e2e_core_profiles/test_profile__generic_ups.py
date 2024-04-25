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


def test_e2e_profile__generic_ups(dd_agent_check):
    profile = '_generic-ups'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:abstract-generic-ups',
        'snmp_host:_generic-ups.device.name',
        'device_hostname:_generic-ups.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'ups_ident_manufacturer:quaintly forward driving Jaded',
        'ups_ident_model:but zombies acted kept forward zombies quaintly acted Jaded',
        'ups_ident_name:zombies zombies zombies acted acted forward',
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.upsAlarmsPresent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsBatteryCurrent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsBatteryTemperature', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsBatteryVoltage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsBypassFrequency', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsBypassNumLines', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsEstimatedChargeRemaining', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsEstimatedMinutesRemaining', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsInputLineBads', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.upsInputNumLines', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsOutputFrequency', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsOutputNumLines', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsSecondsOnBattery', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.upsTestStartTime', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['ups_output_line_index:2'],
        ['ups_output_line_index:20'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.upsOutputCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsOutputPercentLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsOutputPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsOutputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ups_input_line_index:24'],
        ['ups_input_line_index:29'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.upsInputCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsInputFrequency', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsInputTruePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsInputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ups_bypass_line_index:16'],
        ['ups_bypass_line_index:30'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.upsBypassCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsBypassPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.upsBypassVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ups_alarm_descr:1.3.6.1.3.142.254.54.128.104.168.23.51'],
        ['ups_alarm_descr:1.3.6.1.3.74.53.14.181.54.30.174.140'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.upsAlarmTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-ups Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-ups.device.name',
        'profile': 'abstract-generic-ups',
        'status': 1,
        'sys_object_id': '1.2.3.4.5.6.7.8.999',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
