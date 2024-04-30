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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_barracuda_cloudgen(dd_agent_check):
    profile = 'barracuda-cloudgen'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:barracuda-cloudgen',
        'snmp_host:barracuda-cloudgen.device.name',
        'device_hostname:barracuda-cloudgen.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    # Examples:
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.phion.vpnUsers', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['box_service_name:Jaded oxen their driving acted acted oxen', 'box_service_state:started'],
        ['box_service_name:zombies Jaded', 'box_service_state:blocked'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.phion.boxServices', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['connector_name:oxen their forward'],
        ['connector_name:zombies their oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class1Drop', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class1Pakets', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class1Total', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class2Drop', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class2Pakets', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class2Total', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class3Drop', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class3Pakets', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.class3Total', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.noDelayDrop', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.noDelayPakets', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.noDelayTotal', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.rate', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.phion.trafficShape.sessions', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['hw_sensor_name:driving Jaded forward but', 'hw_sensor_type:fan'],
        ['hw_sensor_name:oxen acted quaintly', 'hw_sensor_type:voltage'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.phion.hwSensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['vpn_name:Jaded driving driving oxen zombies quaintly forward but', 'vpn_state:down-disabled'],
        ['vpn_name:quaintly zombies kept driving oxen acted zombies acted kept', 'vpn_state:down-disabled'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.phion.vpnTunnels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['bgp_neighbor_address:Jaded driving oxen oxen kept Jaded kept'],
        ['bgp_neighbor_address:zombies driving quaintly but forward kept zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.phion.bgpNeighbors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ospf_neighbor_address:forward quaintly driving their',
            'ospf_neighbor_id:quaintly quaintly zombies Jaded',
            'ospf_neighbor_interface:but driving oxen acted their',
            'ospf_neighbor_status:their zombies acted oxen driving oxen Jaded oxen their',
        ],
        [
            'ospf_neighbor_address:oxen driving quaintly kept their forward but zombies oxen',
            'ospf_neighbor_id:driving oxen their oxen but acted',
            'ospf_neighbor_interface:Jaded',
            'ospf_neighbor_status:kept kept forward but quaintly quaintly oxen oxen',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.phion.ospfNeighbors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['rip_neighbor_address:acted but', 'rip_neighbor_state:oxen zombies kept forward'],
        [
            'rip_neighbor_address:quaintly forward oxen but kept kept driving but kept',
            'rip_neighbor_state:but forward zombies Jaded forward quaintly acted oxen their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.phion.ripNeighbors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'barracuda-cloudgen Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'barracuda-cloudgen.device.name',
        'profile': 'barracuda-cloudgen',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.10704.1.99999',
        'vendor': 'barracuda',
        'device_type': 'firewall',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
