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
    assert_extend_generic_entity_sensor,
    assert_extend_generic_if,
    assert_extend_generic_ospf,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_arista_switch(dd_agent_check):
    profile = 'arista-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:arista-switch',
        'snmp_host:arista-switch.device.name',
        'device_hostname:arista-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_entity_sensor(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ospf(aggregator, common_tags)
    assert_extend_generic_bgp4(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['interface_index:7', 'queue_index:31'],
        ['interface_index:23', 'queue_index:28'],
        ['interface_index:21', 'queue_index:16'],
        ['interface_index:20', 'queue_index:11'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.aristaIngressQueuePktsDropped', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['interface_index:8', 'queue_index:21'],
        ['interface_index:23', 'queue_index:1'],
        ['interface_index:13', 'queue_index:5'],
        ['interface_index:11', 'queue_index:17'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.aristaEgressQueuePktsDropped', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag = [
        'arista_bgp4_v2_peer_admin_status:halted',
        'arista_bgp4_v2_peer_description:acted driving their acted oxen their acted zombies quaintly',
        'arista_bgp4_v2_peer_local_addr:?7468656972',
        'arista_bgp4_v2_peer_local_addr_type:unknown',
        'arista_bgp4_v2_peer_local_identifier:1.2.3.4',
        'arista_bgp4_v2_peer_remote_identifier:1.2.3.4',
        'arista_bgp4_v2_peer_state:established',
    ]
    aggregator.assert_metric('snmp.aristaBgp4V2PeerLocalAs', metric_type=aggregator.GAUGE, tags=common_tags + tag)
    aggregator.assert_metric('snmp.aristaBgp4V2PeerLocalPort', metric_type=aggregator.GAUGE, tags=common_tags + tag)
    aggregator.assert_metric('snmp.aristaBgp4V2PeerRemoteAs', metric_type=aggregator.GAUGE, tags=common_tags + tag)
    aggregator.assert_metric('snmp.aristaBgp4V2PeerRemotePort', metric_type=aggregator.GAUGE, tags=common_tags + tag)

    aggregator.assert_metric(
        'snmp.aristaIfInOctetRate',
        metric_type=aggregator.GAUGE,
        tags=common_tags + ['arista_if_rate_interval:764721249'],
    )
    aggregator.assert_metric(
        'snmp.aristaIfInPktRate', metric_type=aggregator.GAUGE, tags=common_tags + ['arista_if_rate_interval:764721249']
    )
    aggregator.assert_metric(
        'snmp.aristaIfOutOctetRate',
        metric_type=aggregator.GAUGE,
        tags=common_tags + ['arista_if_rate_interval:764721249'],
    )
    aggregator.assert_metric(
        'snmp.aristaIfOutPktRate',
        metric_type=aggregator.GAUGE,
        tags=common_tags + ['arista_if_rate_interval:764721249'],
    )

    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'arista-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'arista-switch.device.name',
        'profile': 'arista-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.30065.1.3011.7010.427.48',
        'vendor': 'arista',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
