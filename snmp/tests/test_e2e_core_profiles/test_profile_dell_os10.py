# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_host_resources_base,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_dell_os10(dd_agent_check):
    config = create_e2e_core_test_config('dell-os10')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-os10',
        'snmp_host:dell-os10.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.os10ChassisTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['TODO'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['TODO'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10CardTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['TODO'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10PowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['TODO'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10FanTray', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['TODO'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10Fan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['TODO'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10bgp4V2Peer', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'dell-os10 Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'dell-os10.device.name',
        'profile': 'dell-os10',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.674.11000.5000.100.2.1.21',
        'vendor': 'dell',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
