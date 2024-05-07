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


def test_e2e_profile_fortinet(dd_agent_check):
    profile = "fortinet"
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        "snmp_profile:fortinet",
        "snmp_host:fortinet.example",
        "device_hostname:fortinet.example",
        "device_namespace:default",
        "snmp_device:" + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METADATA ---
    device = {
        "description": "Fortinet dummy device",
        "id": "default:" + ip_address,
        "id_tags": ["device_namespace:default", "snmp_device:" + ip_address],
        "ip_address": "" + ip_address,
        "name": "fortinet.example",
        "profile": "fortinet",
        "status": 1,
        "sys_object_id": "1.3.6.1.4.1.12356.103.1",
        "tags": [
            "device_ip:" + ip_address,
            "device_id:default:" + ip_address,
            "device_namespace:default",
            "snmp_device:" + ip_address,
            "snmp_host:fortinet.example",
            "device_hostname:fortinet.example",
            "snmp_profile:fortinet",
        ],
        "vendor": "fortinet",
        'device_type': 'other',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
