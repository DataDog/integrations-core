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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__generic_bgp4(dd_agent_check):
    profile = '_generic-bgp4'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-bgp4',
        'snmp_host:_generic-bgp4.device.name',
        'device_hostname:_generic-bgp4.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['admin_status:start', 'neighbor:52.12.240.251', 'peer_state:established', 'remote_as:31'],
        ['admin_status:start', 'neighbor:72.128.247.81', 'peer_state:active', 'remote_as:27'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.bgpPeerAdminStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.bgpPeerConnectRetryInterval', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.bgpPeerFsmEstablishedTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.bgpPeerFsmEstablishedTransitions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.bgpPeerHoldTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.bgpPeerHoldTimeConfigured', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.bgpPeerInTotalMessages', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.bgpPeerInUpdates', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.bgpPeerKeepAlive', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.bgpPeerKeepAliveConfigured', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.bgpPeerMinASOriginationInterval', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.bgpPeerNegotiatedVersion', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.bgpPeerOutTotalMessages', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.bgpPeerOutUpdates', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.bgpPeerRemoteAs', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.bgpPeerState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.peerConnectionByState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-bgp4 Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-bgp4.device.name',
        'profile': 'generic-bgp4',
        'status': 1,
        'sys_object_id': '1.2.3.1007',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
