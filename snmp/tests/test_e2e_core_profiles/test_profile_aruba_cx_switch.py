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
    assert_extend_generic_if,
    assert_extend_generic_ospf,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_aruba_cx_switch(dd_agent_check):
    profile = 'aruba-cx-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:aruba-cx-switch',
        'snmp_host:aruba-cx-switch.device.name',
        'device_hostname:aruba-cx-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['aruba_wired_temp_sensor_name:but', 'aruba_wired_temp_sensor_state:driving'],
        ['aruba_wired_temp_sensor_name:driving driving', 'aruba_wired_temp_sensor_state:quaintly but'],
        [
            'aruba_wired_temp_sensor_name:forward driving acted driving but',
            'aruba_wired_temp_sensor_state:acted quaintly their',
        ],
        ['aruba_wired_temp_sensor_name:kept their zombies but kept Jaded', 'aruba_wired_temp_sensor_state:quaintly'],
        ['aruba_wired_temp_sensor_name:kept zombies', 'aruba_wired_temp_sensor_state:Jaded their kept'],
        ['aruba_wired_temp_sensor_name:oxen', 'aruba_wired_temp_sensor_state:driving'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.arubaWiredTempSensorTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'aruba_wired_psu_airflow_direction:acted their',
            'aruba_wired_psu_name:oxen forward kept',
            'aruba_wired_psu_product_name:oxen',
            'aruba_wired_psu_serial_number:acted their',
            'aruba_wired_psu_state:Jaded',
        ],
        [
            'aruba_wired_psu_airflow_direction:oxen',
            'aruba_wired_psu_name:zombies',
            'aruba_wired_psu_product_name:but oxen but',
            'aruba_wired_psu_serial_number:forward',
            'aruba_wired_psu_state:acted',
        ],
        [
            'aruba_wired_psu_airflow_direction:oxen driving their',
            'aruba_wired_psu_name:forward kept',
            'aruba_wired_psu_product_name:forward driving',
            'aruba_wired_psu_serial_number:kept',
            'aruba_wired_psu_state:kept driving oxen',
        ],
        [
            'aruba_wired_psu_airflow_direction:their but',
            'aruba_wired_psu_name:forward kept',
            'aruba_wired_psu_product_name:but kept their',
            'aruba_wired_psu_serial_number:acted but Jaded',
            'aruba_wired_psu_state:zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.arubaWiredPSUInstantaneousPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.arubaWiredPSUNumberFailures', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'aruba_wired_fan_tray_name:acted Jaded',
            'aruba_wired_fan_tray_product_name:but zombies but kept acted',
            'aruba_wired_fan_tray_serial_number:forward',
            'aruba_wired_fan_tray_state:forward oxen',
        ],
        [
            'aruba_wired_fan_tray_name:driving driving',
            'aruba_wired_fan_tray_product_name:Jaded zombies',
            'aruba_wired_fan_tray_serial_number:forward',
            'aruba_wired_fan_tray_state:Jaded their Jaded',
        ],
        [
            'aruba_wired_fan_tray_name:quaintly driving',
            'aruba_wired_fan_tray_product_name:oxen Jaded',
            'aruba_wired_fan_tray_serial_number:Jaded but forward',
            'aruba_wired_fan_tray_state:kept',
        ],
        [
            'aruba_wired_fan_tray_name:their their',
            'aruba_wired_fan_tray_product_name:kept',
            'aruba_wired_fan_tray_serial_number:zombies quaintly',
            'aruba_wired_fan_tray_state:acted acted Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.arubaWiredFanTray', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'aruba_wired_fan_airflow_direction:Jaded their',
            'aruba_wired_fan_name:kept kept',
            'aruba_wired_fan_product_name:zombies',
            'aruba_wired_fan_serial_number:their',
            'aruba_wired_fan_state:driving zombies but',
        ],
        [
            'aruba_wired_fan_airflow_direction:acted kept',
            'aruba_wired_fan_name:kept quaintly acted',
            'aruba_wired_fan_product_name:forward quaintly',
            'aruba_wired_fan_serial_number:but',
            'aruba_wired_fan_state:oxen oxen but',
        ],
        [
            'aruba_wired_fan_airflow_direction:but but',
            'aruba_wired_fan_name:but',
            'aruba_wired_fan_product_name:zombies',
            'aruba_wired_fan_serial_number:kept acted kept',
            'aruba_wired_fan_state:forward',
        ],
        [
            'aruba_wired_fan_airflow_direction:kept acted driving',
            'aruba_wired_fan_name:kept',
            'aruba_wired_fan_product_name:driving quaintly but',
            'aruba_wired_fan_serial_number:forward their kept',
            'aruba_wired_fan_state:their',
        ],
        [
            'aruba_wired_fan_airflow_direction:oxen oxen',
            'aruba_wired_fan_name:oxen',
            'aruba_wired_fan_product_name:their zombies',
            'aruba_wired_fan_serial_number:forward',
            'aruba_wired_fan_state:their',
        ],
        [
            'aruba_wired_fan_airflow_direction:zombies',
            'aruba_wired_fan_name:zombies Jaded',
            'aruba_wired_fan_product_name:driving zombies',
            'aruba_wired_fan_serial_number:quaintly driving',
            'aruba_wired_fan_state:oxen quaintly',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.arubaWiredFanRPM', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'aruba-cx-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'aruba-cx-switch.device.name',
        'profile': 'aruba-cx-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.47196.4.1.1.1.999',
        'vendor': 'aruba',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
