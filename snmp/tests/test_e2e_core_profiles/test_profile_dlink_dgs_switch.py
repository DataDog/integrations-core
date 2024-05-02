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


def test_e2e_profile_dlink_dgs_switch(dd_agent_check):
    profile = 'dlink-dgs-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dlink-dgs-switch',
        'snmp_host:dlink-dgs-switch.device.name',
        'device_hostname:dlink-dgs-switch.device.name',
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
        ['cpu:15222', 'dlink_entity_ext_cpu_util_cpu_id:15222', 'dlink_entity_ext_cpu_util_unit_id:44757'],
        ['cpu:19563', 'dlink_entity_ext_cpu_util_cpu_id:19563', 'dlink_entity_ext_cpu_util_unit_id:14054'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['d_entity_ext_mem_util_type:dram', 'mem:16'],
        ['d_entity_ext_mem_util_type:dram', 'mem:20'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'd_entity_ext_env_temp_descr:Jaded acted forward kept',
            'd_entity_ext_env_temp_index:14',
            'd_entity_ext_env_temp_status:abnormal',
            'd_entity_ext_env_temp_unit_id:30507',
        ],
        [
            'd_entity_ext_env_temp_descr:Jaded zombies',
            'd_entity_ext_env_temp_index:21',
            'd_entity_ext_env_temp_status:abnormal',
            'd_entity_ext_env_temp_unit_id:46985',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dlink.dEntityExtEnvTempCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'd_entity_ext_env_fan_descr:acted oxen acted',
            'd_entity_ext_env_fan_index:9',
            'd_entity_ext_env_fan_status:fault',
            'd_entity_ext_env_fan_unit_id:20741',
        ],
        [
            'd_entity_ext_env_fan_descr:but their kept',
            'd_entity_ext_env_fan_index:19',
            'd_entity_ext_env_fan_status:fault',
            'd_entity_ext_env_fan_unit_id:8429',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dlink.dEntityExtEnvFan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'd_entity_ext_env_power_descr:forward Jaded quaintly',
            'd_entity_ext_env_power_index:6432',
            'd_entity_ext_env_power_status:empty',
            'd_entity_ext_env_power_unit_id:8349',
        ],
        [
            'd_entity_ext_env_power_descr:zombies quaintly kept',
            'd_entity_ext_env_power_index:25268',
            'd_entity_ext_env_power_status:failed',
            'd_entity_ext_env_power_unit_id:18359',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dlink.dEntityExtEnvPowerMaxPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dlink.dEntityExtEnvPowerUsedPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['d_entity_ext_env_air_flow_status:abnormal', 'd_entity_ext_env_air_flow_unit_id:1726'],
        ['d_entity_ext_env_air_flow_status:abnormal', 'd_entity_ext_env_air_flow_unit_id:63575'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dlink.dEntityExtEnvAirFlow', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['d_entity_ext_unit_index:16762', 'd_entity_ext_unit_status:ok'],
        ['d_entity_ext_unit_index:28484', 'd_entity_ext_unit_status:ok'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dlink.dEntityExtUnit', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'dlink-dgs-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'dlink-dgs-switch.device.name',
        'profile': 'dlink-dgs-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.171.10.137.1.1',
        'vendor': 'dlink',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
