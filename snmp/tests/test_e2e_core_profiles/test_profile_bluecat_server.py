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


def test_e2e_profile_bluecat_server(dd_agent_check):
    profile = 'bluecat-server'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:bluecat-server',
        'snmp_host:bluecat-server.device.name',
        'device_hostname:bluecat-server.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'bcn_sys_id_product:1.3.6.1.4.1.13315.2.1',
        'bcn_sys_id_os_release:OS v1.2.3',
        'bcn_sys_id_platform:BCN Platform X',
    ]

    # --- TEST EXTENDED METRICS ---
    # Examples:
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'bcn_dhcpv4_subnet_high_threshold:36313',
            'bcn_dhcpv4_subnet_ip:53.202.135.190',
            'bcn_dhcpv4_subnet_low_threshold:20994',
            'bcn_dhcpv4_subnet_mask:173.237.3.46',
            'bcn_dhcpv4_subnet_size:29950',
        ],
        [
            'bcn_dhcpv4_subnet_high_threshold:6107',
            'bcn_dhcpv4_subnet_ip:171.172.73.225',
            'bcn_dhcpv4_subnet_low_threshold:9664',
            'bcn_dhcpv4_subnet_mask:88.247.127.217',
            'bcn_dhcpv4_subnet_size:64705',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.bcnDhcpv4SubnetFreeAddresses', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'bcn_dhcpv4_pool_start_ip:70.175.239.238',
            'bcn_dhcpv4_pool_end_ip:138.41.248.20',
            'bcn_dhcpv4_pool_size:55389',
            'bcn_dhcpv4_pool_subnet_ip:115.187.187.225',
        ],
        [
            'bcn_dhcpv4_pool_start_ip:186.152.75.142',
            'bcn_dhcpv4_pool_end_ip:58.239.195.226',
            'bcn_dhcpv4_pool_size:59812',
            'bcn_dhcpv4_pool_subnet_ip:16.140.203.163',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.bcnDhcpv4PoolFreeAddresses', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'bluecat-server Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'bluecat-server.device.name',
        'profile': 'bluecat-server',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.13315.2.1',
        'vendor': 'bluecat',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
