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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_alcatel_lucent_ent(dd_agent_check):
    profile = 'alcatel-lucent-ent'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:alcatel-lucent-ent',
        'snmp_host:alcatel-lucent-ent.device.name',
        'device_hostname:alcatel-lucent-ent.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['cpu:21', 'health_module_chassis_id:0'],
        ['cpu:27', 'health_module_chassis_id:1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['health_module_chassis_id:0', 'mem:21'],
        ['health_module_chassis_id:1', 'mem:27'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ent_physical_class:other',
            'ent_physical_name:name1',
            'ent_physical_serial_num:ALC12345XYZ67890',
            'ent_physical_model_name:ALC-7504',
            'chas_ent_phys_admin_status:standby',
            'chas_ent_phys_oper_status:unknown',
            'chas_ent_phys_led_status_backup_ps:green_on',
            'chas_ent_phys_led_status_control:amber_blink',
            'chas_ent_phys_led_status_fabric:amber_blink',
            'chas_ent_phys_led_status_fan:amber_blink',
            'chas_ent_phys_led_status_internal_ps:green_on',
            'chas_ent_phys_led_status_ok1:green_on',
            'chas_ent_phys_led_status_ok2:green_blink',
            'chas_ent_phys_led_status_primary_cmm:not_applicable',
            'chas_ent_phys_led_status_ps:off',
            'chas_ent_phys_led_status_secondary_cmm:green_blink',
            'chas_ent_phys_led_status_temperature:green_on',
        ],
        [
            'ent_physical_class:storage_drive',
            'ent_physical_name:name2',
            'ent_physical_serial_num:ALC12345XYZ67891',
            'ent_physical_model_name:ALC-7505',
            'chas_ent_phys_admin_status:unknown',
            'chas_ent_phys_oper_status:idle',
            'chas_ent_phys_led_status_backup_ps:green_on',
            'chas_ent_phys_led_status_control:green_on',
            'chas_ent_phys_led_status_fabric:amber_blink',
            'chas_ent_phys_led_status_fan:amber_on',
            'chas_ent_phys_led_status_internal_ps:green_on',
            'chas_ent_phys_led_status_ok1:not_applicable',
            'chas_ent_phys_led_status_ok2:green_on',
            'chas_ent_phys_led_status_primary_cmm:off',
            'chas_ent_phys_led_status_ps:amber_blink',
            'chas_ent_phys_led_status_secondary_cmm:amber_blink',
            'chas_ent_phys_led_status_temperature:green_on',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.alcatel.ent.chasEntPhysical', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'chas_ent_temp_status:not_present',
            'ent_physical_model_name:ALC-7504',
            'ent_physical_name:name1',
            'ent_physical_serial_num:ALC12345XYZ67890',
            'ent_physical_class:unknown',
        ],
        [
            'chas_ent_temp_status:unknown',
            'ent_physical_model_name:ALC-7505',
            'ent_physical_name:name2',
            'ent_physical_serial_num:ALC12345XYZ67891',
            'ent_physical_class:energy_object',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.alcatel.ent.chasEntTempCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['ala_chas_ent_phys_fan_status:running'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.alcatel.ent.alaChasEntPhysFanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ala_chas_bps_power_supply_name:Jaded',
            'ala_chas_bps_power_supply_oper_status:up',
            'ala_chas_bps_power_supply_serial_num:driving quaintly kept',
        ],
        [
            'ala_chas_bps_power_supply_name:acted their zombies forward oxen',
            'ala_chas_bps_power_supply_oper_status:unknown',
            'ala_chas_bps_power_supply_serial_num:acted forward zombies Jaded but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.alcatel.ent.alaChasBpsPowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'alcatel-lucent-ent Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'alcatel-lucent-ent.device.name',
        'profile': 'alcatel-lucent-ent',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.6486.801.1.1.2.1.9.4.2.4.2.1',
        'vendor': 'alcatel-lucent',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
