# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_mikrotik_router(dd_agent_check):
    config = create_e2e_core_test_config('mikrotik-router')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:mikrotik-router',
        'snmp_host:mikrotik-router.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.mikrotik.mtxrHlCpuTemperature', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.mikrotik.mtxrHlTemperature', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.mikrotik.mtxrHlVoltage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'mikrotik_mtxr_optical_index:10',
            'mikrotik_mtxr_optical_name:oxen acted',
            'mikrotik_mtxr_optical_rx_loss:true',
            'mikrotik_mtxr_optical_tx_fault:false',
        ],
        [
            'mikrotik_mtxr_optical_index:13',
            'mikrotik_mtxr_optical_name:kept',
            'mikrotik_mtxr_optical_rx_loss:true',
            'mikrotik_mtxr_optical_tx_fault:true',
        ],
        [
            'mikrotik_mtxr_optical_index:17',
            'mikrotik_mtxr_optical_name:quaintly their Jaded kept quaintly quaintly acted',
            'mikrotik_mtxr_optical_rx_loss:false',
            'mikrotik_mtxr_optical_tx_fault:true',
        ],
        [
            'mikrotik_mtxr_optical_index:8',
            'mikrotik_mtxr_optical_name:oxen acted',
            'mikrotik_mtxr_optical_rx_loss:true',
            'mikrotik_mtxr_optical_tx_fault:false',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrOpticalRxPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrOpticalSupplyVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrOpticalTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrOpticalTxBiasCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrOpticalTxPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrOpticalWavelength', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'mikrotik_mtxr_poe_interface_index:18',
            'mikrotik_mtxr_poe_name:Jaded driving Jaded their kept driving oxen Jaded',
            'mikrotik_mtxr_poe_status:overload',
        ],
        [
            'mikrotik_mtxr_poe_interface_index:24',
            'mikrotik_mtxr_poe_name:quaintly their acted',
            'mikrotik_mtxr_poe_status:disabled',
        ],
        [
            'mikrotik_mtxr_poe_interface_index:3',
            'mikrotik_mtxr_poe_name:Jaded driving kept Jaded driving acted oxen',
            'mikrotik_mtxr_poe_status:overload',
        ],
        [
            'mikrotik_mtxr_poe_interface_index:30',
            'mikrotik_mtxr_poe_name:Jaded acted zombies Jaded but driving but driving',
            'mikrotik_mtxr_poe_status:waiting_for_load',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrPOECurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.mikrotik.mtxrPOEPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.mikrotik.mtxrPOEVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['mem:24'],
        ['mem:27'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'mikrotik-router Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'mikrotik-router.device.name',
        'profile': 'mikrotik-router',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14988.1.999',
        'vendor': 'mikrotik',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
