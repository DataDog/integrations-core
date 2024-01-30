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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_cisco_firepower_asa(dd_agent_check):
    profile = 'cisco-firepower-asa'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-firepower-asa',
        'snmp_host:cisco-firepower-asa.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.crasMaxSessionsSupportable', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasMaxUsersSupportable', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumDeclinedSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumSetupFailInsufResources', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.crasNumUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['cpu:34646'],
        ['cpu:7885'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-firepower-asa Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-firepower-asa.device.name',
        'profile': 'cisco-firepower-asa',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.1902',
        'vendor': 'cisco',
        'device_type': 'firewall',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
