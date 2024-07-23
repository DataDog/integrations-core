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
    assert_extend_aruba_switch_cpu_memory,
    assert_extend_generic_if,
    assert_extend_generic_ospf,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_aruba_switch(dd_agent_check):
    profile = 'aruba-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:aruba-switch',
        'snmp_host:aruba-switch.device.name',
        'device_hostname:aruba-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'device_vendor:aruba',
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_aruba_switch_cpu_memory(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['mem:0'],
        ['mem:4'],
        ['mem:29'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    aggregator.assert_metric('snmp.wlsxSysExtPacketLossPercent', metric_type=aggregator.GAUGE, tags=common_tags)

    tag_rows = [
        ['fan_index:27'],
        ['fan_index:31'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sysExtFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fan_index:27', 'fan_status:inactive'],
        ['fan_index:31', 'fan_status:active'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.wlsxSysExtFan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['powersupply_index:22'],
        ['powersupply_index:26'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sysExtPowerSupplyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['processor_index:14'],
        ['processor_index:25'],
        ['processor_index:4'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sysExtProcessorLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['memory_index:0'],
        ['memory_index:4'],
        ['memory_index:29'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sysExtMemoryFree', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysExtMemorySize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysExtMemoryUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'ArubaOS (MODEL: Aruba7210), Version 8.6.0.4 (74969)',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'model': 'A7210',
        'name': 'aruba-switch.device.name',
        'os_name': 'ArubaOS',
        'os_version': '8.6.0.4',
        'product_name': 'Aruba7210',
        'profile': 'aruba-switch',
        'serial_number': 'CV0009200',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14823.1.1.36',
        'vendor': 'aruba',
        'version': '8.6.0.4',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
