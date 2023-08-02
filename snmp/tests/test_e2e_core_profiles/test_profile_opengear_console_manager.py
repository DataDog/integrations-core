# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
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
    config = create_e2e_core_test_config('opengear-console-manager')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:opengear-console-manager',
        'snmp_host:opengear-console-manager.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_entity_sensor(aggregator, common_tags)
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
         ['og_serial_port_cts:off', 'og_serial_port_data_bits:30', 'og_serial_port_dcd:on', 'og_serial_port_dsr:on', 'og_serial_port_dtr:off', 'og_serial_port_flow_control:none', 'og_serial_port_index:0', 'og_serial_port_label:quaintly but oxen driving Jaded their', 'og_serial_port_log_level:connect', 'og_serial_port_mode:terminal', 'og_serial_port_parity:none', 'og_serial_port_rts:on', 'og_serial_port_speed:22', 'og_serial_port_stop_bits:one_and_a_half'],
         ['og_serial_port_cts:off', 'og_serial_port_data_bits:7', 'og_serial_port_dcd:off', 'og_serial_port_dsr:off', 'og_serial_port_dtr:on', 'og_serial_port_flow_control:software', 'og_serial_port_index:16', 'og_serial_port_label:acted', 'og_serial_port_log_level:connect', 'og_serial_port_mode:sdt', 'og_serial_port_parity:mark', 'og_serial_port_rts:on', 'og_serial_port_speed:30', 'og_serial_port_stop_bits:two'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ogSerialPortRxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ogSerialPortTxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    tag_rows = [
         ['og_cell_modem_connected:connected', 'og_cell_modem_enabled:disabled', 'og_cell_modem_index:20', 'og_cell_modem_model:kept quaintly acted', 'og_cell_modem_vendor:their Jaded driving but acted'],
         ['og_cell_modem_connected:disconnected', 'og_cell_modem_enabled:enabled', 'og_cell_modem_index:7', 'og_cell_modem_model:oxen their', 'og_cell_modem_vendor:oxen Jaded acted but acted'],

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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
