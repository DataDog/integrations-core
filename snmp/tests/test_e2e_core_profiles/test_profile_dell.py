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
    assert_extend_generic_ip,
    assert_extend_generic_tcp,
    assert_extend_generic_udp,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_dell(dd_agent_check):
    profile = "dell"
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        "snmp_profile:dell",
        "snmp_host:dell.example",
        "device_hostname:dell.example",
        "device_namespace:default",
        "snmp_device:" + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_ip(aggregator, common_tags)
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)

    # --- TEST METADATA ---
    device = {
        "description": "Dell dummy device",
        "id": "default:" + ip_address,
        "id_tags": ["device_namespace:default", "snmp_device:" + ip_address],
        "ip_address": "" + ip_address,
        "name": "dell.example",
        "profile": "dell",
        "status": 1,
        "sys_object_id": "1.3.6.1.4.1.674.1",
        "tags": [
            "device_ip:" + ip_address,
            "device_id:default:" + ip_address,
            "device_namespace:default",
            "snmp_device:" + ip_address,
            "snmp_host:dell.example",
            "device_hostname:dell.example",
            "snmp_profile:dell",
        ],
        "vendor": "dell",
        'device_type': 'other',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
