# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_ups,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_tripplite_ups(dd_agent_check):
    config = create_e2e_core_test_config('tripplite-ups')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:tripplite-ups',
        'snmp_host:tripplite-ups.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + ['tl_ups_ident_id:25', 'tl_ups_ident_serial_num:Jaded but oxen',
 'tl_ups_location:forward quaintly their acted',
 'tl_ups_snmp_card_serial_num:zombies acted driving Jaded kept driving oxen']

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_ups(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.tlEnvHumidity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.tlEnvTemperatureC', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.tlEnvTemperatureF', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.tlUpsAlarmsPresent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.tlUpsBatteryAge', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.tlUpsTemperature', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.tlUpsTemperatureF', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
         ['tl_ups_input_voltage_index:16', 'tl_ups_input_voltage_type:phase_to_phase'],
         ['tl_ups_input_voltage_index:23', 'tl_ups_input_voltage_type:phase_to_neutral'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlUpsInputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['tl_ups_output_circuit_status:closed'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlUpsOutputCircuitLoadCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlUpsOutputCircuitPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlUpsOutputCircuitVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['tl_env_contact_config:normally_closed', 'tl_env_contact_name:but kept acted kept acted', 'tl_env_contact_status:normal'],
         ['tl_env_contact_config:normally_open', 'tl_env_contact_name:their their but Jaded quaintly', 'tl_env_contact_status:alarm'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlEnvContact', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['tl_ups_outlet_group_desc:oxen acted driving forward zombies but their', 'tl_ups_outlet_group_name:their quaintly their', 'ups_outlet_group_status_group_state:ups_outlet_group_status_off'],
         ['tl_ups_outlet_group_desc:oxen their zombies zombies acted', 'tl_ups_outlet_group_name:kept'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlUpsOutlet', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'tripplite-ups Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'tripplite-ups.device.name',
        'profile': 'tripplite-ups',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.850.1.4',
        'vendor': 'tripplite',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
