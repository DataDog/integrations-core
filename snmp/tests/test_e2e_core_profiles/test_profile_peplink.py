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
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_peplink(dd_agent_check):
    profile = 'peplink'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:peplink',
        'snmp_host:peplink.device.name',
        'device_hostname:peplink.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'peplink_bal_firmware:driving their acted',
        'peplink_bal_serial_number:zombies their',
        'peplink_device_firmware_version:Jaded but but driving acted forward kept but',
        'peplink_device_model:driving acted their zombies but acted forward Jaded',
        'peplink_device_serial_number:their Jaded oxen but Jaded forward oxen driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.peplink.deviceTemperatureCelsius', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.peplink.deviceTemperatureFahrenheit', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['device_psu_id:17', 'device_psu_status:error'],
        ['device_psu_id:20', 'device_psu_status:on'],
        ['device_psu_id:23', 'device_psu_status:error'],
        ['device_psu_id:4', 'device_psu_status:on'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.peplink.devicePSUPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['device_fan_id:10', 'device_fan_status:error'],
        ['device_fan_id:13', 'device_fan_status:error'],
        ['device_fan_id:14', 'device_fan_status:on'],
        ['device_fan_id:5', 'device_fan_status:error'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.peplink.deviceFanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'device_power_source_id:21',
            'device_power_source_name:kept acted acted but acted zombies their',
            'device_power_source_status:connected',
        ],
        [
            'device_power_source_id:23',
            'device_power_source_name:quaintly kept',
            'device_power_source_status:no_cable_detected',
        ],
        ['device_power_source_id:26', 'device_power_source_name:quaintly', 'device_power_source_status:connected'],
        [
            'device_power_source_id:29',
            'device_power_source_name:acted kept zombies driving',
            'device_power_source_status:connected',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.peplink.devicePowerSource', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['link_conn_num:1', 'link_name:acted driving', 'link_status:kept but oxen acted driving kept'],
        ['link_conn_num:30', 'link_name:Jaded', 'link_status:kept kept their but but Jaded Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.peplink.linkDataTransferred', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.peplink.linkThroughputIn', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.peplink.linkThroughputOut', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['wan_usage_index:25'],
        ['wan_usage_index:9'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.peplink.wanUsageDataTransferred', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.peplink.wanUsageThroughputIn', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.peplink.wanUsageThroughputOut', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'peplink Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'peplink.device.name',
        'profile': 'peplink',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.23695',
        'vendor': 'peplink',
        'device_type': 'router',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
