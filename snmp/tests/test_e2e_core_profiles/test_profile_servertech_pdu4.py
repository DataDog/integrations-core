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


def test_e2e_profile_servertech_pdu4(dd_agent_check):
    profile = 'servertech-pdu4'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:servertech-pdu4',
        'snmp_host:servertech-pdu4.device.name',
        'device_hostname:servertech-pdu4.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'servertech_sentry4_st4_unit_asset_tag:oxen but kept',
            'servertech_sentry4_st4_unit_id:a',
            'servertech_sentry4_st4_unit_model:driving forward Jaded',
            'servertech_sentry4_st4_unit_name:acted forward Jaded kept',
            'servertech_sentry4_st4_unit_product_mfr_date:driving',
            'servertech_sentry4_st4_unit_product_sn:zombies oxen their',
            'servertech_sentry4_st4_unit_status:low_warning',
            'servertech_sentry4_st4_unit_type:link_pdu',
        ],
        [
            'servertech_sentry4_st4_unit_asset_tag:quaintly',
            'servertech_sentry4_st4_unit_id:a',
            'servertech_sentry4_st4_unit_model:Jaded their acted oxen',
            'servertech_sentry4_st4_unit_name:zombies quaintly kept forward',
            'servertech_sentry4_st4_unit_product_mfr_date:Jaded',
            'servertech_sentry4_st4_unit_product_sn:their',
            'servertech_sentry4_st4_unit_type:master_pdu',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4UnitMonitor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_input_cord_id:on',
            'servertech_sentry4_st4_input_cord_name:driving zombies forward their',
            'servertech_sentry4_st4_input_cord_inlet_type:Jaded their',
            'servertech_sentry4_st4_input_cord_nominal_voltage:15',
            'servertech_sentry4_st4_input_cord_nominal_voltage_min:22',
            'servertech_sentry4_st4_input_cord_nominal_voltage_max:8',
            'servertech_sentry4_st4_input_cord_current_capacity:30',
            'servertech_sentry4_st4_input_cord_current_capacity_max:19',
            'servertech_sentry4_st4_input_cord_power_capacity:12',
            'servertech_sentry4_st4_input_cord_line_count:3',
            'servertech_sentry4_st4_input_cord_phase_count:5',
            'servertech_sentry4_st4_input_cord_ocp_count:12',
            'servertech_sentry4_st4_input_cord_branch_count:7',
            'servertech_sentry4_st4_input_cord_outlet_count:13',
            'servertech_sentry4_st4_input_cord_active_power_status:over_limit',
            'servertech_sentry4_st4_input_cord_apparent_power_status:alarm',
            'servertech_sentry4_st4_input_cord_out_of_balance_status:conflict',
            'servertech_sentry4_st4_input_cord_power_factor_status:low_warning',
            'servertech_sentry4_st4_input_cord_state:off',
            'servertech_sentry4_st4_input_cord_status:over_limit',
        ],
        [
            'servertech_sentry4_st4_input_cord_id:on',
            'servertech_sentry4_st4_input_cord_name:forward oxen oxen',
            'servertech_sentry4_st4_input_cord_inlet_type:driving driving',
            'servertech_sentry4_st4_input_cord_nominal_voltage:13',
            'servertech_sentry4_st4_input_cord_nominal_voltage_min:20',
            'servertech_sentry4_st4_input_cord_nominal_voltage_max:20',
            'servertech_sentry4_st4_input_cord_current_capacity:13',
            'servertech_sentry4_st4_input_cord_current_capacity_max:11',
            'servertech_sentry4_st4_input_cord_power_capacity:3',
            'servertech_sentry4_st4_input_cord_line_count:0',
            'servertech_sentry4_st4_input_cord_phase_count:0',
            'servertech_sentry4_st4_input_cord_ocp_count:8',
            'servertech_sentry4_st4_input_cord_branch_count:9',
            'servertech_sentry4_st4_input_cord_outlet_count:2',
            'servertech_sentry4_st4_input_cord_active_power_status:pwr_error',
            'servertech_sentry4_st4_input_cord_apparent_power_status:lost',
            'servertech_sentry4_st4_input_cord_out_of_balance_status:over_limit',
            'servertech_sentry4_st4_input_cord_power_factor_status:not_found',
            'servertech_sentry4_st4_input_cord_state:off',
            'servertech_sentry4_st4_input_cord_status:high_alarm',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordApparentPower',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordEnergy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordFrequency', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordOutOfBalance', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4InputCordPowerUtilized',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_line_id:but',
            'servertech_sentry4_st4_line_label:their',
            'servertech_sentry4_st4_line_current_capacity:25',
            'servertech_sentry4_st4_line_current_status:normal',
            'servertech_sentry4_st4_line_state:unknown',
            'servertech_sentry4_st4_line_status:high_warning',
        ],
        [
            'servertech_sentry4_st4_line_id:but',
            'servertech_sentry4_st4_line_label:but Jaded forward kept kept',
            'servertech_sentry4_st4_line_current_capacity:11',
            'servertech_sentry4_st4_line_current_status:pwr_error',
            'servertech_sentry4_st4_line_state:unknown',
            'servertech_sentry4_st4_line_status:disabled',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4LineCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4LineCurrentUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_phase_id:but',
            'servertech_sentry4_st4_phase_label:forward Jaded forward',
            'servertech_sentry4_st4_phase_nominal_voltage:18',
            'servertech_sentry4_st4_phase_outlet_count:27',
            'servertech_sentry4_st4_phase_power_factor_status:read_error',
            'servertech_sentry4_st4_phase_reactance:capacitive',
            'servertech_sentry4_st4_phase_state:off',
            'servertech_sentry4_st4_phase_status:nvm_fail',
            'servertech_sentry4_st4_phase_voltage_status:fuse_blown',
        ],
        [
            'servertech_sentry4_st4_phase_id:but',
            'servertech_sentry4_st4_phase_label:their forward Jaded',
            'servertech_sentry4_st4_phase_nominal_voltage:29',
            'servertech_sentry4_st4_phase_outlet_count:19',
            'servertech_sentry4_st4_phase_power_factor_status:reading',
            'servertech_sentry4_st4_phase_reactance:inductive',
            'servertech_sentry4_st4_phase_state:off',
            'servertech_sentry4_st4_phase_status:high_warning',
            'servertech_sentry4_st4_phase_voltage_status:fuse_blown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseCurrentCrestFactor',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseEnergy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhasePowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4PhaseVoltageDeviation', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_ocp_status:profile_error',
            'servertech_sentry4_st4_ocp_branch_count:2',
            'servertech_sentry4_st4_ocp_current_capacity:22',
            'servertech_sentry4_st4_ocp_current_capacity_max:24',
            'servertech_sentry4_st4_ocp_id:oxen',
            'servertech_sentry4_st4_ocp_label:Jaded quaintly',
            'servertech_sentry4_st4_ocp_outlet_count:13',
            'servertech_sentry4_st4_ocp_type:breaker',
        ],
        [
            'servertech_sentry4_st4_ocp_status:lost',
            'servertech_sentry4_st4_ocp_branch_count:3',
            'servertech_sentry4_st4_ocp_current_capacity:9',
            'servertech_sentry4_st4_ocp_current_capacity_max:2',
            'servertech_sentry4_st4_ocp_id:oxen',
            'servertech_sentry4_st4_ocp_label:kept Jaded Jaded',
            'servertech_sentry4_st4_ocp_outlet_count:8',
            'servertech_sentry4_st4_ocp_type:breaker',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4OcpMonitor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_branch_id:kept',
            'servertech_sentry4_st4_branch_label:driving forward but',
            'servertech_sentry4_st4_branch_current_capacity:20',
            'servertech_sentry4_st4_branch_phase_id:but',
            'servertech_sentry4_st4_branch_ocp_id:oxen',
            'servertech_sentry4_st4_branch_outlet_count:15',
            'servertech_sentry4_st4_branch_current_status:over_limit',
            'servertech_sentry4_st4_branch_state:on',
            'servertech_sentry4_st4_branch_status:settle',
        ],
        [
            'servertech_sentry4_st4_branch_id:oxen',
            'servertech_sentry4_st4_branch_label:zombies zombies',
            'servertech_sentry4_st4_branch_current_capacity:12',
            'servertech_sentry4_st4_branch_phase_id:but',
            'servertech_sentry4_st4_branch_ocp_id:oxen',
            'servertech_sentry4_st4_branch_outlet_count:15',
            'servertech_sentry4_st4_branch_current_status:under_limit',
            'servertech_sentry4_st4_branch_state:off',
            'servertech_sentry4_st4_branch_status:normal',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4BranchCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4BranchCurrentUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_outlet_branch_id:but',
            'servertech_sentry4_st4_outlet_current_capacity:2',
            'servertech_sentry4_st4_outlet_id:oxen',
            'servertech_sentry4_st4_outlet_name:acted zombies',
            'servertech_sentry4_st4_outlet_ocp_id:kept',
            'servertech_sentry4_st4_outlet_phase_id:but',
            'servertech_sentry4_st4_outlet_post_on_delay:13',
            'servertech_sentry4_st4_outlet_power_capacity:31',
            'servertech_sentry4_st4_outlet_socket_type:Jaded',
            'servertech_sentry4_st4_outlet_wakeup_state:on',
        ],
        [
            'servertech_sentry4_st4_outlet_branch_id:kept',
            'servertech_sentry4_st4_outlet_current_capacity:6',
            'servertech_sentry4_st4_outlet_id:Jaded',
            'servertech_sentry4_st4_outlet_name:Jaded kept but quaintly acted',
            'servertech_sentry4_st4_outlet_ocp_id:kept',
            'servertech_sentry4_st4_outlet_phase_id:but',
            'servertech_sentry4_st4_outlet_post_on_delay:0',
            'servertech_sentry4_st4_outlet_power_capacity:16',
            'servertech_sentry4_st4_outlet_socket_type:oxen acted forward kept oxen',
            'servertech_sentry4_st4_outlet_wakeup_state:last',
        ],
        ['servertech_sentry4_st4_outlet_state:on', 'servertech_sentry4_st4_outlet_status:breaker_tripped'],
        ['servertech_sentry4_st4_outlet_state:on', 'servertech_sentry4_st4_outlet_status:lost'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4OutletMonitor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_temp_sensor_status:settle',
            'servertech_sentry4_st4_temp_sensor_id:as',
            'servertech_sentry4_st4_temp_sensor_name:driving but',
            'servertech_sentry4_st4_temp_sensor_value_min:5',
            'servertech_sentry4_st4_temp_sensor_value_max:0',
        ],
        [
            'servertech_sentry4_st4_temp_sensor_status:purged',
            'servertech_sentry4_st4_temp_sensor_id:as',
            'servertech_sentry4_st4_temp_sensor_name:forward driving but',
            'servertech_sentry4_st4_temp_sensor_value_min:24',
            'servertech_sentry4_st4_temp_sensor_value_max:6',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4TempSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry4_st4_humid_sensor_id:sd',
            'servertech_sentry4_st4_humid_sensor_name:their acted zombies their',
            'servertech_sentry4_st4_humid_sensor_status:not_found',
        ],
        [
            'servertech_sentry4_st4_humid_sensor_id:sd',
            'servertech_sentry4_st4_humid_sensor_name:zombies Jaded zombies',
            'servertech_sentry4_st4_humid_sensor_status:not_found',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry4.st4HumidSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'servertech-pdu4 Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'servertech-pdu4.device.name',
        'profile': 'servertech-pdu4',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.1718.4',
        'vendor': 'servertech',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
