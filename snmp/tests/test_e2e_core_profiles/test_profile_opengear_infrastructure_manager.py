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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_opengear_infrastructure_manager(dd_agent_check):
    profile = 'opengear-infrastructure-manager'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:opengear-infrastructure-manager',
        'snmp_host:opengear-infrastructure-manager.device.name',
        'device_hostname:opengear-infrastructure-manager.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'og_serial_port_status_cts:off',
            'og_serial_port_status_dcd:off',
            'og_serial_port_status_dsr:on',
            'og_serial_port_status_dtr:off',
            'og_serial_port_status_label:driving',
            'og_serial_port_status_port:10',
            'og_serial_port_status_rts:on',
            'og_serial_port_status_speed:7',
        ],
        [
            'og_serial_port_status_cts:off',
            'og_serial_port_status_dcd:on',
            'og_serial_port_status_dsr:off',
            'og_serial_port_status_dtr:on',
            'og_serial_port_status_label:their quaintly zombies Jaded oxen kept oxen their',
            'og_serial_port_status_port:6',
            'og_serial_port_status_rts:on',
            'og_serial_port_status_speed:29',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ogSerialPortStatusRxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ogSerialPortStatusTxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['og_rpc_status_name:driving driving'],
        ['og_rpc_status_name:their but but their forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ogRpcStatusAlertCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ogRpcStatusMaxTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['og_emd_status_name:driving Jaded kept kept'],
        ['og_emd_status_name:their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ogEmdStatusAlertCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ogEmdStatusHumidity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ogEmdStatusTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'opengear-infrastructure-manager Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'opengear-infrastructure-manager.device.name',
        'profile': 'opengear-infrastructure-manager',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.25049.1.61',
        'vendor': 'opengear',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
