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


def test_e2e_profile_raritan_dominion(dd_agent_check):
    config = create_e2e_core_test_config('raritan-dominion')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:raritan-dominion',
        'snmp_host:raritan-dominion.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['raritan_remotekvm_system_power_supply_power_on:true'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.raritan.remotekvm.systemPowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'raritan_remotekvm_port_data_name:kept kept oxen acted Jaded but',
            'raritan_remotekvm_port_data_status:inactive',
            'raritan_remotekvm_port_data_type:their oxen oxen acted',
        ],
        [
            'raritan_remotekvm_port_data_name:oxen oxen driving acted forward',
            'raritan_remotekvm_port_data_status:busy',
            'raritan_remotekvm_port_data_type:but Jaded their quaintly quaintly',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.raritan.remotekvm.portData', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'raritan-dominion Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'raritan-dominion.device.name',
        'profile': 'raritan-dominion',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.13742.3.2.10',
        'vendor': 'raritan',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
