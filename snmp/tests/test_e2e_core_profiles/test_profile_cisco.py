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
    assert_extend_cisco_cpu_memory,
    assert_extend_cisco_generic,
    assert_extend_generic_bgp4,
    assert_extend_generic_if,
    assert_extend_generic_ip,
    assert_extend_generic_ospf,
    assert_extend_generic_tcp,
    assert_extend_generic_udp,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_cisco(dd_agent_check):
    profile = 'cisco'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        "snmp_profile:cisco",
        "snmp_host:cisco3620",
        "device_hostname:cisco3620",
        "device_namespace:default",
        "snmp_device:" + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ip(aggregator, common_tags)
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_generic_bgp4(aggregator, common_tags)
    assert_extend_cisco_cpu_memory(aggregator, common_tags)
    assert_extend_cisco_generic(aggregator, common_tags)

    # --- TEST METADATA ---
    device = {
        "description": "Cisco IOS XR Software, Copyright (c) 2013-2020 by Cisco Systems, Inc.",
        "id": "default:" + ip_address,
        "id_tags": ["device_namespace:default", "snmp_device:" + ip_address],
        "ip_address": "" + ip_address,
        "name": "cisco3620",
        "os_name": "IOSXR",
        "profile": "cisco",
        "status": 1,
        "sys_object_id": "1.3.6.1.4.1.9.1.122",
        "tags": [
            "device_ip:" + ip_address,
            "device_id:default:" + ip_address,
            "device_namespace:default",
            "snmp_device:" + ip_address,
            "snmp_host:cisco3620",
            "device_hostname:cisco3620",
            "snmp_profile:cisco",
        ],
        "vendor": "cisco",
        'device_type': 'other',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
