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
    assert_extend_generic_host_resources_base,
    assert_extend_generic_if,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_juniper_pulse_secure(dd_agent_check):
    profile = 'juniper-pulse-secure'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:juniper-pulse-secure',
        'snmp_host:juniper-pulse-secure.device.name',
        'device_hostname:juniper-pulse-secure.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'juniper_ive_esap_version:but Jaded acted quaintly forward oxen acted kept',
        'juniper_ive_product_name:kept their Jaded oxen but acted quaintly',
        'juniper_ive_product_version:kept kept acted driving oxen quaintly quaintly',
        'juniper_ive_ive_max_concurrent_users_license_capacity:1000',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.clusterConcurrentUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.diskFullPercent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveAppletHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveConcurrentUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveFileHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveNCHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveSAMHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveSSLConnections', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveSwapUtil', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveTemperature', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveTotalHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveVPNTunnels', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.iveWebHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.ivetermHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.logFullPercent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.meetingHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.signedInMailUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.juniper.ive.signedInWebUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'juniper-pulse-secure Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'juniper-pulse-secure.device.name',
        'profile': 'juniper-pulse-secure',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.12532.256.999',
        'vendor': 'juniper-networks',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
