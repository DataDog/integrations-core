# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_bgp4,
    assert_extend_generic_host_resources,
    assert_extend_generic_if,
    assert_extend_generic_ip,
    assert_extend_generic_ospf,
    assert_extend_generic_tcp,
    assert_extend_generic_udp,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_juniper(dd_agent_check):
    profile = "juniper"
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        "snmp_profile:juniper",
        "snmp_host:jnxM40",
        "device_hostname:jnxM40",
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
    assert_extend_generic_host_resources(aggregator, common_tags)

    # --- TEST METADATA ---
    device = {
        "description": "Juniper Networks, Inc.",
        "id": "default:" + ip_address,
        "id_tags": ["device_namespace:default", "snmp_device:" + ip_address],
        "ip_address": "" + ip_address,
        "name": "jnxM40",
        'os_name': 'JUNOS',
        "profile": "juniper",
        "status": 1,
        "sys_object_id": "1.3.6.1.4.1.2636.1.1.1.2.1",
        "tags": [
            "device_ip:" + ip_address,
            "device_id:default:" + ip_address,
            "device_namespace:default",
            "snmp_device:" + ip_address,
            "snmp_host:jnxM40",
            "device_hostname:jnxM40",
            "snmp_profile:juniper",
        ],
        "vendor": "juniper-networks",
        "device_type": "other",
    }
    assert_device_metadata(aggregator, device)


def test_e2e_profile_juniper_variation(dd_agent_check):
    profile = "juniper-variation"
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        "snmp_profile:juniper",
        "snmp_host:jnxVariationM40",
        "device_hostname:jnxVariationM40",
        "device_namespace:default",
        "snmp_device:" + ip_address,
        "device_ip:" + ip_address,
        "device_id:default:" + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ip(aggregator, common_tags)
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_generic_bgp4(aggregator, common_tags)
    assert_extend_generic_host_resources(aggregator, common_tags)

    # --- TEST METADATA ---
    device = {
        "description": "Juniper Networks, Inc.",
        "id": "default:" + ip_address,
        "id_tags": ["device_namespace:default", "snmp_device:" + ip_address],
        "ip_address": "" + ip_address,
        "name": "jnxVariationM40",
        'os_name': 'JUNOS',
        "profile": "juniper",
        "status": 1,
        "sys_object_id": "1.3.6.1.4.1.2636.1.1.1.4.1",
        "tags": [
            "device_ip:" + ip_address,
            "device_id:default:" + ip_address,
            "device_namespace:default",
            "snmp_device:" + ip_address,
            "snmp_host:jnxVariationM40",
            "device_hostname:jnxVariationM40",
            "snmp_profile:juniper",
        ],
        "vendor": "juniper-networks",
        "device_type": "other",
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    # Checked locally (needs empty juniper-variation.yaml profile)
    # assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
