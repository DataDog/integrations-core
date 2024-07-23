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


def test_e2e_profile_alcatel_lucent_ind(dd_agent_check):
    profile = 'alcatel-lucent-ind'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:alcatel-lucent-ind',
        'snmp_host:alcatel-lucent-ind.device.name',
        'device_hostname:alcatel-lucent-ind.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.alcatel.ind.healthDeviceTemperatureChas1MinAvg', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'ent_physical_class:battery',
            'ent_physical_name:name1',
            'ent_physical_serial_num:ALC12345XYZ67890',
            'ent_physical_model_name:ALC-7504',
            'chas_ent_phys_admin_status:power_on',
            'chas_ent_phys_led_status_backup_ps:green_blink',
            'chas_ent_phys_led_status_control:green_blink',
            'chas_ent_phys_led_status_fabric:not_applicable',
            'chas_ent_phys_led_status_fan1:not_applicable',
            'chas_ent_phys_led_status_fan2:not_applicable',
            'chas_ent_phys_led_status_fan3:amber_on',
            'chas_ent_phys_led_status_fan:not_applicable',
            'chas_ent_phys_led_status_internal_ps:off',
            'chas_ent_phys_led_status_ok1:off',
            'chas_ent_phys_led_status_ok2:not_applicable',
            'chas_ent_phys_led_status_primary_cmm:not_applicable',
            'chas_ent_phys_led_status_psu:off',
            'chas_ent_phys_led_status_secondary_cmm:amber_on',
            'chas_ent_phys_led_status_temperature:amber_blink',
            'chas_ent_phys_oper_status:not_present',
        ],
        [
            'ent_physical_class:backplane',
            'ent_physical_name:name2',
            'ent_physical_serial_num:ALC12345XYZ67891',
            'ent_physical_model_name:ALC-7505',
            'chas_ent_phys_admin_status:reset_all',
            'chas_ent_phys_led_status_backup_ps:not_applicable',
            'chas_ent_phys_led_status_control:off',
            'chas_ent_phys_led_status_fabric:amber_on',
            'chas_ent_phys_led_status_fan1:amber_on',
            'chas_ent_phys_led_status_fan2:green_on',
            'chas_ent_phys_led_status_fan3:amber_blink',
            'chas_ent_phys_led_status_fan:not_applicable',
            'chas_ent_phys_led_status_internal_ps:not_applicable',
            'chas_ent_phys_led_status_ok1:amber_blink',
            'chas_ent_phys_led_status_ok2:green_blink',
            'chas_ent_phys_led_status_primary_cmm:green_on',
            'chas_ent_phys_led_status_psu:green_blink',
            'chas_ent_phys_led_status_secondary_cmm:off',
            'chas_ent_phys_led_status_temperature:amber_blink',
            'chas_ent_phys_oper_status:testing',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.alcatel.ind.chasEntPhysical', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'alcatel-lucent-ind Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'alcatel-lucent-ind.device.name',
        'profile': 'alcatel-lucent-ind',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.6486.800.1.1.2.1.9.1.1',
        'vendor': 'alcatel-lucent',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
