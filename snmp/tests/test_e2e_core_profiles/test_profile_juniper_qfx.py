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
    assert_extend_generic_bgp4,
    assert_extend_generic_host_resources,
    assert_extend_generic_if,
    assert_extend_generic_ospf,
    assert_extend_juniper_cos,
    assert_extend_juniper_dcu,
    assert_extend_juniper_firewall,
    assert_extend_juniper_virtualchassis,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_juniper_qfx(dd_agent_check):
    profile = 'juniper-qfx'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:juniper-qfx',
        'snmp_host:juniper-qfx.device.name',
        'device_hostname:juniper-qfx.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_bgp4(aggregator, common_tags)
    assert_extend_generic_host_resources(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_juniper_cos(aggregator, common_tags)
    assert_extend_juniper_dcu(aggregator, common_tags)
    assert_extend_juniper_firewall(aggregator, common_tags)
    assert_extend_juniper_virtualchassis(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'juniper-qfx Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'juniper-qfx.device.name',
        'profile': 'juniper-qfx',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2636.1.1.1.2.82',
        'vendor': 'juniper-networks',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
