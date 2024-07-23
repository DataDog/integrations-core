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


def test_e2e_profile_cisco_load_balancer(dd_agent_check):
    profile = 'cisco-load-balancer'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-load-balancer',
        'snmp_host:cisco-load-balancer.device.name',
        'device_hostname:cisco-load-balancer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    # Examples:
    assert_extend_cisco(aggregator, common_tags)
    assert_extend_cisco_generic(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['slb_entity:11128'],
        ['slb_entity:52836'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.slbStatsCreatedConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsCreatedHCConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsDestroyedConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsDestroyedHCConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsEstablishedConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsEstablishedHCConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsReassignedConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.slbStatsReassignedHCConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['slb_entity:15396'],
        ['slb_entity:2812'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cslbxStatsAclDenyHCRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsAclDenyRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsBadSslFormatRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsCurrConnections', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsDroppedL4PolicyConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsDroppedL4PolicyHCConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsDroppedL7PolicyConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsDroppedL7PolicyHCConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsDroppedRedirectConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cslbxStatsFailedConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cslbxStatsFtpConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cslbxStatsHttpRedirectConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsIpChecksumErrorPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsL4PolicyConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsL4PolicyHCConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsL7ParserErrorRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsL7PolicyConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsL7PolicyHCConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsMaxParseLenRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsNoActiveServerRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsNoCfgPolicyHCRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsNoCfgPolicyRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsNoMatchPolicyHCRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsNoMatchPolicyRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsOutOfMemoryRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsTcpChecksumErrorPkts', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsTimedOutConnections', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsVerMismatchHCRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cslbxStatsVerMismatchRejects', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'cisco-load-balancer Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cisco-load-balancer.device.name',
        'profile': 'cisco-load-balancer',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.9.1.824',
        'vendor': 'cisco',
        'device_type': 'load_balancer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
