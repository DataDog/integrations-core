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


def test_e2e_profile_huawei_routers(dd_agent_check):
    profile = 'huawei-routers'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:huawei-routers',
        'snmp_host:huawei-routers.device.name',
        'device_hostname:huawei-routers.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'huawei_hw_bgp_peer_remote_addr:190.114.96.169',
            'huawei_hw_bgp_peer_state:openconfirm',
            'huawei_hw_bgp_peer_vrf_name:acted acted but Jaded but driving their',
            'huawei_hw_bgp_peer_un_avai_reason:configuration_lead_peer_down',
        ],
        [
            'huawei_hw_bgp_peer_remote_addr:93.22.18.75',
            'huawei_hw_bgp_peer_state:active',
            'huawei_hw_bgp_peer_vrf_name:oxen quaintly their their their quaintly zombies',
            'huawei_hw_bgp_peer_un_avai_reason:direct_connect_interface_down',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerFsmEstablishedCounter', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerFsmEstablishedTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerNegotiatedVersion', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerRemoteAs', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_bgp_peer_remote_addr:190.114.96.169',
            'huawei_hw_bgp_peer_vrf_name:acted acted but Jaded but driving their',
        ],
        [
            'huawei_hw_bgp_peer_remote_addr:93.22.18.75',
            'huawei_hw_bgp_peer_vrf_name:oxen quaintly their their their quaintly zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerPrefixActiveCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerPrefixAdvCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerPrefixRcvCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_bgp_peer_remote_addr:190.114.96.169',
            'huawei_hw_bgp_peer_vrf_name:acted acted but Jaded but driving their',
        ],
        [
            'huawei_hw_bgp_peer_remote_addr:93.22.18.75',
            'huawei_hw_bgp_peer_vrf_name:oxen quaintly their their their quaintly zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerInKeepAliveMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerInNotificationMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerInOpenMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerInRouteFreshMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerInTotalMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerInUpdateMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerOutKeepAliveMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerOutNotificationMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerOutOpenMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerOutRouteFreshMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerOutTotalMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.huawei.hwBgpPeerOutUpdateMsgCounter', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_dns_alias:but oxen Jaded driving oxen zombies acted Jaded zombies',
            'huawei_hw_dns_domain_name:acted driving driving',
            'huawei_hw_dns_ip_address:72.148.142.6',
        ],
        [
            'huawei_hw_dns_alias:quaintly driving oxen but',
            'huawei_hw_dns_domain_name:but quaintly their Jaded zombies driving but',
            'huawei_hw_dns_ip_address:219.179.143.179',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.huawei.hwDnsTtl', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['huawei_hw_server_addr:90.96.69.163'],
        ['huawei_hw_server_addr:89.239.196.92'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwDnsServerAddr', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_fw_net_event_description:Jaded quaintly forward oxen kept Jaded',
            'huawei_hw_fw_net_event_dst_ip_port:20',
            'huawei_hw_fw_net_event_interface:8',
            'huawei_hw_fw_net_event_src_ip_port:12',
            'huawei_hw_fw_net_event_src_vrf_name:kept their kept kept Jaded oxen',
            'huawei_hw_fw_net_event_src_ip_address:67.48.111.19',
            'huawei_hw_fw_net_event_dst_ip_address:224.129.49.238',
        ],
        [
            'huawei_hw_fw_net_event_description:but acted oxen forward kept',
            'huawei_hw_fw_net_event_dst_ip_port:25',
            'huawei_hw_fw_net_event_interface:5',
            'huawei_hw_fw_net_event_src_ip_port:1',
            'huawei_hw_fw_net_event_src_vrf_name:forward Jaded but',
            'huawei_hw_fw_net_event_src_ip_address:234.112.31.229',
            'huawei_hw_fw_net_event_dst_ip_address:179.228.184.47',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.huawei.hwFwNetEvents', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['huawei_hw_fw_connection_stat_description:acted forward'],
        ['huawei_hw_fw_connection_stat_description:their driving kept but their forward but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwFwConnectionStatCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_nat_addr_pool_end_addr:190.109.146.4',
            'huawei_hw_nat_addr_pool_start_addr:95.201.113.165',
        ],
        [
            'huawei_hw_nat_addr_pool_end_addr:174.219.250.193',
            'huawei_hw_nat_addr_pool_start_addr:163.37.155.112',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwNatAddrPoolRefTimes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'huawei_hw_nat_session_dst_global_addr:109.168.69.44',
            'huawei_hw_nat_session_dst_global_port:23',
            'huawei_hw_nat_session_dst_local_addr:82.64.18.230',
            'huawei_hw_nat_session_dst_local_port:9',
            'huawei_hw_nat_session_dst_vpn:forward oxen',
            'huawei_hw_nat_session_protocol:udp',
            'huawei_hw_nat_session_src_global_addr:10.90.199.104',
            'huawei_hw_nat_session_src_global_port:14',
            'huawei_hw_nat_session_src_local_addr:133.53.124.168',
            'huawei_hw_nat_session_src_local_port:14',
            'huawei_hw_nat_session_src_vpn:Jaded',
            'huawei_hw_nat_session_status:create_and_go',
        ],
        [
            'huawei_hw_nat_session_dst_global_addr:164.221.169.160',
            'huawei_hw_nat_session_dst_global_port:24',
            'huawei_hw_nat_session_dst_local_addr:63.215.82.48',
            'huawei_hw_nat_session_dst_local_port:13',
            'huawei_hw_nat_session_dst_vpn:Jaded their Jaded Jaded but',
            'huawei_hw_nat_session_protocol:tcp',
            'huawei_hw_nat_session_src_global_addr:130.210.203.49',
            'huawei_hw_nat_session_src_global_port:20',
            'huawei_hw_nat_session_src_local_addr:216.86.211.13',
            'huawei_hw_nat_session_src_local_port:14',
            'huawei_hw_nat_session_src_vpn:their oxen',
            'huawei_hw_nat_session_status:create_and_wait',
        ],
        [
            'huawei_hw_nat_session_dst_global_addr:209.105.21.80',
            'huawei_hw_nat_session_dst_global_port:13',
            'huawei_hw_nat_session_dst_local_addr:93.3.206.178',
            'huawei_hw_nat_session_dst_local_port:2',
            'huawei_hw_nat_session_dst_vpn:their kept oxen kept',
            'huawei_hw_nat_session_protocol:other',
            'huawei_hw_nat_session_src_global_addr:20.177.16.92',
            'huawei_hw_nat_session_src_global_port:19',
            'huawei_hw_nat_session_src_local_addr:228.7.205.79',
            'huawei_hw_nat_session_src_local_port:31',
            'huawei_hw_nat_session_src_vpn:quaintly',
        ],
        [
            'huawei_hw_nat_session_dst_global_addr:38.240.243.97',
            'huawei_hw_nat_session_dst_global_port:19',
            'huawei_hw_nat_session_dst_local_addr:24.185.202.70',
            'huawei_hw_nat_session_dst_local_port:20',
            'huawei_hw_nat_session_dst_vpn:forward but but quaintly kept',
            'huawei_hw_nat_session_protocol:other',
            'huawei_hw_nat_session_src_global_addr:145.253.155.67',
            'huawei_hw_nat_session_src_global_port:17',
            'huawei_hw_nat_session_src_local_addr:68.142.171.7',
            'huawei_hw_nat_session_src_local_port:2',
            'huawei_hw_nat_session_src_vpn:zombies but kept acted zombies',
            'huawei_hw_nat_session_status:not_ready',
        ],
        [
            'huawei_hw_nat_session_dst_global_addr:48.27.151.110',
            'huawei_hw_nat_session_dst_global_port:9',
            'huawei_hw_nat_session_dst_local_addr:230.37.219.95',
            'huawei_hw_nat_session_dst_local_port:1',
            'huawei_hw_nat_session_dst_vpn:driving but quaintly oxen',
            'huawei_hw_nat_session_protocol:udp',
            'huawei_hw_nat_session_src_global_addr:18.130.217.190',
            'huawei_hw_nat_session_src_global_port:6',
            'huawei_hw_nat_session_src_local_addr:136.42.67.250',
            'huawei_hw_nat_session_src_local_port:15',
            'huawei_hw_nat_session_src_vpn:forward',
            'huawei_hw_nat_session_status:active',
        ],
        [
            'huawei_hw_nat_session_dst_global_addr:60.46.237.61',
            'huawei_hw_nat_session_dst_global_port:14',
            'huawei_hw_nat_session_dst_local_addr:102.166.51.63',
            'huawei_hw_nat_session_dst_local_port:21',
            'huawei_hw_nat_session_dst_vpn:oxen kept acted',
            'huawei_hw_nat_session_protocol:udp',
            'huawei_hw_nat_session_src_global_addr:170.164.126.139',
            'huawei_hw_nat_session_src_global_port:1',
            'huawei_hw_nat_session_src_local_addr:210.44.210.127',
            'huawei_hw_nat_session_src_local_port:18',
            'huawei_hw_nat_session_src_vpn:their zombies Jaded acted but',
            'huawei_hw_nat_session_status:not_ready',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.huawei.hwNatSession', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'huawei-routers Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'huawei-routers.device.name',
        'profile': 'huawei-routers',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2011.2.224.279',
        'vendor': 'huawei',
        'device_type': 'router',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
