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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_dell_os10(dd_agent_check):
    profile = 'dell-os10'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-os10',
        'snmp_host:dell-os10.device.name',
        'device_hostname:dell-os10.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.dell.os10ChassisTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
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
            'dell_os10_card_description:quaintly their forward their driving Jaded acted driving',
            'dell_os10_card_service_tag:oxen',
            'dell_os10_card_status:card_mis_match',
        ],
        [
            'dell_os10_card_description:quaintly zombies driving driving',
            'dell_os10_card_service_tag:but',
            'dell_os10_card_status:card_mis_match',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.os10CardTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['dell_os10_power_supply_index:26803', 'dell_os10_power_supply_oper_status:not_present'],
        ['dell_os10_power_supply_index:39196', 'dell_os10_power_supply_oper_status:down'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.os10PowerSupply', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['dell_os10_fan_tray_index:42382', 'dell_os10_fan_tray_oper_status:not_present'],
        ['dell_os10_fan_tray_index:48949', 'dell_os10_fan_tray_oper_status:testing'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.os10FanTray', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['dell_os10_fan_index:31113', 'dell_os10_fan_oper_status:lower_layer_down'],
        ['dell_os10_fan_index:42700', 'dell_os10_fan_oper_status:failed'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.os10Fan', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'dell_os10bgp4_v2_peer_admin_status:halted',
            'dell_os10bgp4_v2_peer_description:driving kept but but Jaded their kept their',
            'dell_os10bgp4_v2_peer_local_addr:forward acted zombies',
            'dell_os10bgp4_v2_peer_local_addr_type:ipv4',
            'dell_os10bgp4_v2_peer_local_as:6566',
            'dell_os10bgp4_v2_peer_local_identifier:0x00000000',
            'dell_os10bgp4_v2_peer_local_port:30492',
            'dell_os10bgp4_v2_peer_remote_addr:acted kept driving kept quaintly',
            'dell_os10bgp4_v2_peer_remote_addr_type:ipv4',
            'dell_os10bgp4_v2_peer_remote_as:58448',
            'dell_os10bgp4_v2_peer_remote_identifier:0x00000000',
            'dell_os10bgp4_v2_peer_remote_port:46732',
            'dell_os10bgp4_v2_peer_state:openconfirm',
        ],
        [
            'dell_os10bgp4_v2_peer_admin_status:running',
            'dell_os10bgp4_v2_peer_description:kept zombies',
            'dell_os10bgp4_v2_peer_local_addr:zombies driving quaintly but but but',
            'dell_os10bgp4_v2_peer_local_addr_type:ipv4z',
            'dell_os10bgp4_v2_peer_local_as:49005',
            'dell_os10bgp4_v2_peer_local_identifier:0x00000000',
            'dell_os10bgp4_v2_peer_local_port:47120',
            'dell_os10bgp4_v2_peer_remote_addr:acted Jaded quaintly acted their Jaded Jaded zombies zombies',
            'dell_os10bgp4_v2_peer_remote_addr_type:unknown',
            'dell_os10bgp4_v2_peer_remote_as:57330',
            'dell_os10bgp4_v2_peer_remote_identifier:0x00000000',
            'dell_os10bgp4_v2_peer_remote_port:25857',
            'dell_os10bgp4_v2_peer_state:established',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.os10bgp4V2Peer', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

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
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
