# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_host_resources_base,
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_dell_os10(dd_agent_check):
    config = create_e2e_core_test_config('dell-os10')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-os10',
        'snmp_host:dell-os10.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.os10ChassisTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['hr_processor_frw_id:1.3.6.1.3.28.242.101.186.129'],
        ['hr_processor_frw_id:1.3.6.1.3.97.114.168'],
        ['hr_processor_frw_id:10'],
        ['hr_processor_frw_id:21'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'os10_card_description:quaintly their forward their driving Jaded acted driving',
            'os10_card_service_tag:oxen',
            'os10_card_status:down',
        ],
        [
            'os10_card_description:quaintly zombies driving driving',
            'os10_card_service_tag:but',
            'os10_card_status:down',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10CardTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['os10_power_supply_oper_status:down'],
        ['os10_power_supply_oper_status:not_present'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10PowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['os10_fan_tray_oper_status:not_present'],
        ['os10_fan_tray_oper_status:testing'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10FanTray', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['os10_fan_oper_status:failed'],
        ['os10_fan_oper_status:lower_layer_down'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10Fan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'os10bgp4_v2_peer_admin_status:halted',
            'os10bgp4_v2_peer_description:driving kept but but Jaded their kept their',
            'os10bgp4_v2_peer_local_addr:forward acted zombies',
            'os10bgp4_v2_peer_local_addr_type:ipv4',
            'os10bgp4_v2_peer_local_as:6566',
            'os10bgp4_v2_peer_local_identifier:0x00000000',
            'os10bgp4_v2_peer_local_port:30492',
            'os10bgp4_v2_peer_remote_addr:acted kept driving kept quaintly',
            'os10bgp4_v2_peer_remote_addr_type:ipv4',
            'os10bgp4_v2_peer_remote_as:58448',
            'os10bgp4_v2_peer_remote_identifier:0x00000000',
            'os10bgp4_v2_peer_remote_port:46732',
            'os10bgp4_v2_peer_state:openconfirm',
        ],
        [
            'os10bgp4_v2_peer_admin_status:running',
            'os10bgp4_v2_peer_description:kept zombies',
            'os10bgp4_v2_peer_local_addr:zombies driving quaintly but but but',
            'os10bgp4_v2_peer_local_addr_type:ipv4z',
            'os10bgp4_v2_peer_local_as:49005',
            'os10bgp4_v2_peer_local_identifier:0x00000000',
            'os10bgp4_v2_peer_local_port:47120',
            'os10bgp4_v2_peer_remote_addr:acted Jaded quaintly acted their Jaded Jaded zombies zombies',
            'os10bgp4_v2_peer_remote_addr_type:unknown',
            'os10bgp4_v2_peer_remote_as:57330',
            'os10bgp4_v2_peer_remote_identifier:0x00000000',
            'os10bgp4_v2_peer_remote_port:25857',
            'os10bgp4_v2_peer_state:established',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.os10bgp4V2Peer', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'dell-os10 Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'dell-os10.device.name',
        'profile': 'dell-os10',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.674.11000.5000.100.2.1.21',
        'vendor': 'dell',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
