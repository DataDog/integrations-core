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
    assert_extend_cisco,
    assert_extend_cisco_generic,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_cisco_access_point(dd_agent_check):
    profile = 'cisco-access-point'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-access-point',
        'snmp_host:cisco-access-point.device.name',
        'device_hostname:cisco-access-point.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_cisco(aggregator, common_tags)
    assert_extend_cisco_generic(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['if_name:eth0'],
        ['if_name:eth1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cDot11ActiveBridges', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cDot11ActiveRepeaters', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cDot11ActiveWirelessClients', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['if_name:eth11'],
        ['if_name:eth12'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cDot11AssStatsAssociated', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cDot11AssStatsAuthenticated', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cDot11AssStatsDeauthenticated', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cDot11AssStatsDisassociated', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cDot11AssStatsRoamedAway', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cDot11AssStatsRoamedIn', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-access-point Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-access-point.device.name',
        'profile': 'cisco-access-point',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.525',
        'vendor': 'cisco',
        'device_type': 'access_point',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
