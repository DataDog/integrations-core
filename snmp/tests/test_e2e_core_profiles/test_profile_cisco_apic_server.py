# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config, assert_extend_cisco,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_cisco_apic_server(dd_agent_check):
    config = create_e2e_core_test_config('cisco-apic-server')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-apic-server',
        'snmp_host:cisco-apic-server.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_cisco(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
         ['cefc_power_redundancy_mode:combined', 'cefc_power_redundancy_oper_mode:combined', 'cefc_power_units:Jaded'],
         ['cefc_power_redundancy_mode:redundant', 'cefc_power_redundancy_oper_mode:redundant', 'cefc_power_units:quaintly forward Jaded forward oxen their'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFRUPowerSupplyGroup', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cefcTotalAvailableCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cefcTotalDrawnCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],
         ['cefc_fru_power_admin_status:power_cycle', 'cefc_fru_power_oper_status:off_admin'],
         ['cefc_fru_power_admin_status:power_cycle', 'cefc_fru_power_oper_status:off_connector_rating'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFRUCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cefcFRUPowerStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cefc_module_admin_status:enabled', 'cefc_module_oper_status:powered_down', 'cefc_module_reset_reason:system_reset', 'cefc_module_reset_reason_description:Jaded driving driving their driving kept Jaded acted', 'cefc_module_state_change_reason_descr:oxen acted zombies driving driving'],
         ['cefc_module_admin_status:reset', 'cefc_module_oper_status:powered_down', 'cefc_module_reset_reason:power_up', 'cefc_module_reset_reason_description:oxen oxen kept but but acted', 'cefc_module_state_change_reason_descr:forward forward acted Jaded'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcModule', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cefc_fan_tray_oper_status:down'],
         ['cefc_fan_tray_oper_status:up'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFanTrayStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cefcFan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cefcFanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cefcFanSpeedPercent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['ent_sensor_precision:3', 'ent_sensor_scale:pico', 'ent_sensor_status:nonoperational', 'ent_sensor_type:hertz'],
         ['ent_sensor_precision:3', 'ent_sensor_scale:yocto', 'ent_sensor_status:nonoperational', 'ent_sensor_type:hertz'],
         ['ent_sensor_precision:7', 'ent_sensor_scale:atto', 'ent_sensor_status:nonoperational', 'ent_sensor_type:special_enum'],
         ['ent_sensor_precision:8', 'ent_sensor_scale:milli', 'ent_sensor_status:unavailable', 'ent_sensor_type:rpm'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.entSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cisco_env_mon_voltage_state:not_functioning', 'cisco_env_mon_voltage_status_descr:zombies'],
         ['cisco_env_mon_voltage_state:warning', 'cisco_env_mon_voltage_status_descr:acted their'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonVoltageStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ciscoEnvMonVoltageStatusValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],
         ['cisco_env_mon_temperature_state:normal', 'cisco_env_mon_temperature_status_descr:oxen', 'cisco_env_mon_temperature_threshold:14'],
         ['cisco_env_mon_temperature_state:shutdown', 'cisco_env_mon_temperature_status_descr:but kept their oxen but kept', 'cisco_env_mon_temperature_threshold:14'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonTemperatureStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ciscoEnvMonTemperatureStatusValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cisco_env_mon_fan_state:not_functioning', 'cisco_env_mon_fan_status_descr:driving acted but'],
         ['cisco_env_mon_fan_state:not_present', 'cisco_env_mon_fan_status_descr:zombies but oxen Jaded zombies'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['cisco_env_mon_supply_source:dc', 'cisco_env_mon_supply_state:not_present', 'cisco_env_mon_supply_status_descr:their but quaintly'],
         ['cisco_env_mon_supply_source:external_power_supply', 'cisco_env_mon_supply_state:warning', 'cisco_env_mon_supply_status_descr:Jaded but oxen acted'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ciscoEnvMonSupplyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)



    # --- TEST METADATA ---
    device = {
        'description': 'cisco-apic-server Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-apic-server.device.name',
        'profile': 'cisco-apic-server',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.2238',
        'vendor': 'cisco',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
