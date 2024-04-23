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
    assert_extend_cisco_cpu_memory,
    assert_extend_generic_bgp4,
    assert_extend_generic_if,
    assert_extend_generic_ip,
    assert_extend_generic_ospf,
    assert_extend_generic_tcp,
    assert_extend_generic_udp,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__cisco_generic(dd_agent_check):
    profile = '_cisco-generic'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-generic',
        'snmp_host:_cisco-generic.device.name',
        'device_hostname:_cisco-generic.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_generic_bgp4(aggregator, common_tags)
    assert_extend_generic_ip(aggregator, common_tags)
    assert_extend_cisco_cpu_memory(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['mem:13'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fru:16'],
        ['fru:19'],
        ['fru:20'],
        ['fru:23'],
        ['fru:30'],
        ['fru:4'],
        ['fru:5'],
        ['fru:6'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFRUCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cefcFRUPowerAdminStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cefcFRUPowerOperStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['fru:4', 'power_admin_status:on', 'power_oper_status:off_cooling'],
        ['fru:5', 'power_admin_status:power_cycle', 'power_oper_status:off_env_other'],
        ['fru:6', 'power_admin_status:inline_auto', 'power_oper_status:off_env_power'],
        ['fru:16', 'power_admin_status:power_cycle', 'power_oper_status:off_cooling'],
        ['fru:19', 'power_admin_status:off', 'power_oper_status:off_denied'],
        ['fru:20', 'power_admin_status:inline_auto', 'power_oper_status:off_env_fan'],
        ['fru:23', 'power_admin_status:on', 'power_oper_status:on_but_fan_fail'],
        ['fru:30', 'power_admin_status:inline_on', 'power_oper_status:off_connector_rating'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFRUPowerStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cpu:712'],
        ['cpu:25166'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpmCPUMemoryFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpmCPUMemoryUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpmCPUTotal1minRev', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cpmCPUTotalMonIntervalValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['interface:le0'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cieIfResetCount', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    tag_rows = [
        ['temp_index:15', 'temp_state:not_functioning'],
        ['temp_index:20', 'temp_state:warning'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonTemperatureStatusValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['power_source:ac', 'power_status_descr:kept Jaded oxen Jaded their'],
        ['power_source:internal_redundant', 'power_status_descr:their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonSupplyState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cisco_env_mon_supply_state:critical', 'power_source:internal_redundant', 'power_status_descr:their'],
        ['cisco_env_mon_supply_state:shutdown', 'power_source:ac', 'power_status_descr:kept Jaded oxen Jaded their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ciscoEnvMonSupplyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['fan_status_index:11'],
        ['fan_status_index:16'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonFanState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fan_status_index:11', 'fan_state:not_functioning', 'fan_status_descr:oxen their but kept forward kept'],
        ['fan_status_index:16', 'fan_state:normal', 'fan_status_descr:acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    aggregator.assert_metric('snmp.cswStackPortOperStatus', metric_type=aggregator.GAUGE, tags=common_tags)

    tag_rows = [
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name1'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name2'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name3'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name4'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name5'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name6'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name7'],
        ['mac_addr:11:11:11:11:11:11', 'entity_name:name8'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cswSwitchState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name1', 'switch_state:progressing'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name2', 'switch_state:ready'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name3', 'switch_state:added'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name4', 'switch_state:ver_mismatch'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name5', 'switch_state:progressing'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name6', 'switch_state:sdm_mismatch'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name7', 'switch_state:provisioned'],
        ['mac_addr:11:11:11:11:11:11', 'entity_physical_name:name8', 'switch_state:ver_mismatch'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cswSwitchInfo', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

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
        ['fru:21', 'cefc_fan_tray_oper_status:warning', 'cefc_fan_tray_direction:front_to_back'],
        ['fru:23', 'cefc_fan_tray_oper_status:up', 'cefc_fan_tray_direction:front_to_back'],
        ['fru:25', 'cefc_fan_tray_oper_status:unknown', 'cefc_fan_tray_direction:front_to_back'],
        ['fru:27', 'cefc_fan_tray_oper_status:unknown', 'cefc_fan_tray_direction:unknown'],
        ['fru:29', 'cefc_fan_tray_oper_status:unknown', 'cefc_fan_tray_direction:back_to_front'],
        ['fru:30', 'cefc_fan_tray_oper_status:up', 'cefc_fan_tray_direction:back_to_front'],
        ['fru:7', 'cefc_fan_tray_oper_status:up', 'cefc_fan_tray_direction:back_to_front'],
        ['fru:9', 'cefc_fan_tray_oper_status:warning', 'cefc_fan_tray_direction:unknown'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFanTrayStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem_pool_name:but their kept quaintly driving'],
        ['mem_pool_name:zombies kept their oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoMemoryPoolFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ciscoMemoryPoolLargestFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ciscoMemoryPoolUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['connection_type:current_half_open'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cfwConnectionStatCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['hardware_desc:but acted quaintly their', 'hardware_type:8'],
        ['hardware_desc:zombies kept forward acted their forward', 'hardware_type:2'],
        ['hardware_desc:zombies oxen but', 'hardware_type:7'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cfwHardwareStatusValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['chassis_switch_id:17174'],
        ['chassis_switch_id:27415'],
        ['chassis_switch_id:41972'],
        ['chassis_switch_id:49126'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cvsChassisUpTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['rtt_index:26', 'rtt_state:inactive', 'rtt_type:tcp_connect'],
        ['rtt_index:30', 'rtt_state:orderly_stop', 'rtt_type:script'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.rttMonLatestRttOperCompletionTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.rttMonLatestRttOperSense', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['rtt_index:26', 'rtt_state:inactive', 'rtt_type:tcp_connect'],
        ['rtt_index:30', 'rtt_state:orderly_stop', 'rtt_type:script'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.rttMonCtrlOperTimeoutOccurred', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': '_cisco-generic Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_cisco-generic.device.name',
        'profile': 'cisco-generic',
        'status': 1,
        'sys_object_id': '1.2.3.1005',
        'vendor': 'cisco',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
