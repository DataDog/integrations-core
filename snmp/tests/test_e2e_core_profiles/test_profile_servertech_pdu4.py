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
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_servertech_pdu4(dd_agent_check):
    config = create_e2e_core_test_config('servertech-pdu4')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:servertech-pdu4',
        'snmp_host:servertech-pdu4.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'sentry4_unit_asset_tag:oxen but kept',
            'sentry4_unit_id:a',
            'sentry4_unit_model:driving forward Jaded',
            'sentry4_unit_name:acted forward Jaded kept',
            'sentry4_unit_product_mfr_date:driving',
            'sentry4_unit_product_sn:zombies oxen their',
            'sentry4_unit_type:link',
        ],
        [
            'sentry4_unit_asset_tag:quaintly',
            'sentry4_unit_id:a',
            'sentry4_unit_model:Jaded their acted oxen',
            'sentry4_unit_name:zombies quaintly kept forward',
            'sentry4_unit_product_mfr_date:Jaded',
            'sentry4_unit_product_sn:their',
            'sentry4_unit_type:primary',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sentry4.UnitMonitor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'sentry4_input_cord_active_power_status:over_limit',
            'sentry4_input_cord_apparent_power_status:alarm',
            'sentry4_input_cord_out_of_balance_status:conflict',
            'sentry4_input_cord_power_factor_status:low_warning',
            'sentry4_input_cord_state:off',
            'sentry4_input_cord_status:over_limit',
        ],
        [
            'sentry4_input_cord_active_power_status:pwr_error',
            'sentry4_input_cord_apparent_power_status:lost',
            'sentry4_input_cord_out_of_balance_status:over_limit',
            'sentry4_input_cord_power_factor_status:not_found',
            'sentry4_input_cord_state:off',
            'sentry4_input_cord_status:high_alarm',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sentry4.InputCordActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.InputCordApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.InputCordEnergy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.InputCordFrequency', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.InputCordOutOfBalance', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.InputCordPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.InputCordPowerUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['sentry4_line_current_status:normal', 'sentry4_line_state:unknown', 'sentry4_line_status:high_warning'],
        ['sentry4_line_current_status:pwr_error', 'sentry4_line_state:unknown', 'sentry4_line_status:disabled'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sentry4.LineCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.sentry4.LineCurrentUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'sentry4_phase_power_factor_status:read_error',
            'sentry4_phase_reactance:capacitive',
            'sentry4_phase_state:off',
            'sentry4_phase_status:nvm_fail',
            'sentry4_phase_voltage_status:fuse_blown',
        ],
        [
            'sentry4_phase_power_factor_status:reading',
            'sentry4_phase_reactance:inductive',
            'sentry4_phase_state:off',
            'sentry4_phase_status:high_warning',
            'sentry4_phase_voltage_status:fuse_blown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sentry4.PhaseActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sentry4.PhaseApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.sentry4.PhaseCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.sentry4.PhaseCurrentCrestFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.sentry4.PhaseEnergy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.sentry4.PhasePowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.sentry4.PhaseVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.sentry4.PhaseVoltageDeviation', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'sentry4_ocp_branch_count:2',
            'sentry4_ocp_current_capacity:22',
            'sentry4_ocp_current_capacity_max:24',
            'sentry4_ocp_id:oxen',
            'sentry4_ocp_label:Jaded quaintly',
            'sentry4_ocp_outlet_count:13',
            'sentry4_ocp_type:breaker',
        ],
        [
            'sentry4_ocp_branch_count:3',
            'sentry4_ocp_current_capacity:9',
            'sentry4_ocp_current_capacity_max:2',
            'sentry4_ocp_id:oxen',
            'sentry4_ocp_label:kept Jaded Jaded',
            'sentry4_ocp_outlet_count:8',
            'sentry4_ocp_type:breaker',
        ],
        ['sentry4_ocp_status:lost'],
        ['sentry4_ocp_status:profile_error'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sentry4.OcpMonitor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['sentry4_branch_current_status:over_limit', 'sentry4_branch_state:on', 'sentry4_branch_status:settle'],
        ['sentry4_branch_current_status:under_limit', 'sentry4_branch_state:off', 'sentry4_branch_status:normal'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sentry4.BranchCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.sentry4.BranchCurrentUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'sentry4_outlet_branch_id:but',
            'sentry4_outlet_current_capacity:2',
            'sentry4_outlet_id:oxen',
            'sentry4_outlet_name:acted zombies',
            'sentry4_outlet_ocp_id:kept',
            'sentry4_outlet_phase_id:but',
            'sentry4_outlet_post_on_delay:13',
            'sentry4_outlet_power_capacity:31',
            'sentry4_outlet_socket_type:Jaded',
            'sentry4_outlet_wakeup_state:on',
        ],
        [
            'sentry4_outlet_branch_id:kept',
            'sentry4_outlet_current_capacity:6',
            'sentry4_outlet_id:Jaded',
            'sentry4_outlet_name:Jaded kept but quaintly acted',
            'sentry4_outlet_ocp_id:kept',
            'sentry4_outlet_phase_id:but',
            'sentry4_outlet_post_on_delay:0',
            'sentry4_outlet_power_capacity:16',
            'sentry4_outlet_socket_type:oxen acted forward kept oxen',
            'sentry4_outlet_wakeup_state:last',
        ],
        ['sentry4_outlet_state:on', 'sentry4_outlet_status:breaker_tripped'],
        ['sentry4_outlet_state:on', 'sentry4_outlet_status:lost'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sentry4.OutletMonitor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['sentry4_temp_sensor_status:purged'],
        ['sentry4_temp_sensor_status:settle'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sentry4.TempSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'sentry4_humid_sensor_id:sd',
            'sentry4_humid_sensor_name:their acted zombies their',
            'sentry4_humid_sensor_status:not_found',
        ],
        ['sentry4_humid_sensor_status:not_found'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sentry4.HumidSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
