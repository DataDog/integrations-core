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


def test_e2e_profile_cisco_firepower(dd_agent_check):
    profile = 'cisco-firepower'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-firepower',
        'snmp_host:cisco-firepower.device.name',
        'device_hostname:cisco-firepower.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['cpu:34881'],
        ['cpu:7541'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem:11603'],
        ['mem:14559'],
        ['mem:20786'],
        ['mem:21724'],
        ['mem:41868'],
        ['mem:47424'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cfpr_sm_monitor_dn:Jaded oxen'],
        ['cfpr_sm_monitor_dn:but Jaded kept zombies but but Jaded'],
        ['cfpr_sm_monitor_dn:forward'],
        ['cfpr_sm_monitor_dn:their forward their driving oxen'],
        ['cfpr_sm_monitor_dn:their oxen quaintly Jaded oxen their acted kept driving'],
        ['cfpr_sm_monitor_dn:their zombies oxen oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cfprSmMonitorDataDiskAvailable', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cfprSmMonitorDataDiskTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cfpr_equipment_fan_dn:driving forward but Jaded zombies', 'cfpr_equipment_fan_oper_state:operable'],
        [
            'cfpr_equipment_fan_dn:forward kept quaintly Jaded zombies driving acted kept driving',
            'cfpr_equipment_fan_oper_state:accessibility_problem',
        ],
        ['cfpr_equipment_fan_dn:kept driving', 'cfpr_equipment_fan_oper_state:thermal_problem'],
        ['cfpr_equipment_fan_dn:their but driving but', 'cfpr_equipment_fan_oper_state:operable'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cfprEquipmentFan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cfpr_equipment_psu_dn:driving zombies their acted', 'cfpr_equipment_psu_power:ok'],
        [
            'cfpr_equipment_psu_dn:forward driving quaintly zombies their acted kept but forward',
            'cfpr_equipment_psu_power:offduty',
        ],
        ['cfpr_equipment_psu_dn:forward forward', 'cfpr_equipment_psu_power:oir_failed'],
        ['cfpr_equipment_psu_dn:zombies acted zombies', 'cfpr_equipment_psu_power:ok'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cfprEquipmentPsu', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-firepower Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-firepower.device.name',
        'profile': 'cisco-firepower',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.2404',
        'vendor': 'cisco',
        'device_type': 'firewall',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
