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
    assert_extend_generic_entity_sensor,
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_opengear_console_manager(dd_agent_check):
    profile = 'opengear-console-manager'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:opengear-console-manager',
        'snmp_host:opengear-console-manager.device.name',
        'device_hostname:opengear-console-manager.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_entity_sensor(aggregator, common_tags)
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'og_serial_port_cts:off',
            'og_serial_port_data_bits:6',
            'og_serial_port_dcd:on',
            'og_serial_port_dsr:off',
            'og_serial_port_dtr:off',
            'og_serial_port_flow_control:hardware',
            'og_serial_port_index:1',
            'og_serial_port_label:zombies Jaded forward driving quaintly forward their forward',
            'og_serial_port_log_level:input_only',
            'og_serial_port_mode:none',
            'og_serial_port_parity:space',
            'og_serial_port_rts:on',
            'og_serial_port_speed:14',
            'og_serial_port_stop_bits:one',
        ],
        [
            'og_serial_port_cts:on',
            'og_serial_port_data_bits:20',
            'og_serial_port_dcd:off',
            'og_serial_port_dsr:on',
            'og_serial_port_dtr:on',
            'og_serial_port_flow_control:software',
            'og_serial_port_index:30',
            'og_serial_port_label:but kept',
            'og_serial_port_log_level:input_only',
            'og_serial_port_mode:console',
            'og_serial_port_parity:none',
            'og_serial_port_rts:off',
            'og_serial_port_speed:13',
            'og_serial_port_stop_bits:one_and_a_half',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ogSerialPortRxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ogSerialPortTxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    tag_rows = [
        [
            'og_cell_modem_connected:disconnected',
            'og_cell_modem_enabled:disabled',
            'og_cell_modem_index:23',
            'og_cell_modem_model:driving but oxen acted',
            'og_cell_modem_vendor:kept acted acted kept kept',
        ],
        [
            'og_cell_modem_connected:disconnected',
            'og_cell_modem_enabled:enabled',
            'og_cell_modem_index:6',
            'og_cell_modem_model:quaintly zombies forward',
            'og_cell_modem_vendor:their their forward quaintly zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ogCellModemCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'opengear-console-manager Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'opengear-console-manager.device.name',
        'profile': 'opengear-console-manager',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.25049.1.11',
        'vendor': 'opengear',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
