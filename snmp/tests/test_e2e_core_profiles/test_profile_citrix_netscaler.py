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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_citrix_netscaler(dd_agent_check):
    profile = 'citrix-netscaler'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:citrix-netscaler',
        'snmp_host:citrix-netscaler.device.name',
        'device_hostname:citrix-netscaler.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.curConfigGslbVservers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.curConfigLbVservers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.curConfigVservers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.netscaler.haTimeofLastStateTransition', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.netscaler.haTotStateTransitions', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpErrIncompleteHeaders', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpErrIncompleteRequests', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric(
        'snmp.netscaler.httpErrIncompleteResponses', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric('snmp.netscaler.httpErrServerBusy', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTot10Requests', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTot10Responses', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotGets', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotOthers', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotPosts', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotResponses', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotRxRequestBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotRxResponseBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotTxRequestBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.httpTotTxResponseBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.serverCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sslCurSessions', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sslSessionsPerSec', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sslTotSessions', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.svcCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.svcTotalClients', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.svcTotalServers', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.svcgroupCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.svcgroupmemCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.syssvcCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sysupsvcCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sysupsvcitmCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpCurClientConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.netscaler.tcpCurClientConnEstablished', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.netscaler.tcpCurServerConnEstablished', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.netscaler.tcpErrAnyPortFail', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpErrIpPortFail', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpErrRetransmit', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpTotRxPkts', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpTotTxPkts', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.totSpilloverCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.vsvrBindCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.vsvrSvcGrpBindCount', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'netscaler_vsvr_ip_address:210.102.241.146',
            'netscaler_vsvr_name:acted oxen driving their forward their kept Jaded',
            'netscaler_vsvr_port:12',
            'netscaler_vsvr_state:transition_to_out_of_service',
            'netscaler_vsvr_type:sslvpn_udp',
        ],
        [
            'netscaler_vsvr_ip_address:53.144.47.94',
            'netscaler_vsvr_name:oxen kept their driving',
            'netscaler_vsvr_port:8',
            'netscaler_vsvr_state:up',
            'netscaler_vsvr_type:rpc_client',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.vsvrCurClntConnections', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_sys_health_disk_name:forward acted oxen forward but acted forward'],
        ['netscaler_sys_health_disk_name:their Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sysHealthDiskAvail', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sysHealthDiskPerusage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sysHealthDiskSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sysHealthDiskUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_if_media:Jaded driving Jaded', 'netscaler_if_name:zombies'],
        ['netscaler_if_media:but driving acted zombies oxen zombies Jaded', 'netscaler_if_name:driving kept Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.ifRxAvgBandwidthUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.ifThroughput', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.ifTotRxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.ifTotRxMbits', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.ifTotTxBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.ifTotTxMbits', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.ifTxAvgBandwidthUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_vserver_full_name:acted driving kept zombies forward Jaded quaintly kept their',
            'netscaler_vsvr_service_full_name:oxen their their',
            'netscaler_vsvr_service_name:kept oxen oxen acted kept forward',
        ],
        [
            'netscaler_vserver_full_name:driving quaintly Jaded driving driving acted',
            'netscaler_vsvr_service_full_name:forward oxen kept acted kept their driving quaintly zombies',
            'netscaler_vsvr_service_name:driving forward driving oxen acted oxen oxen their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.servicePersistentHits', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrServiceHits', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_ns_cp_uname:driving'],
        ['netscaler_ns_cp_uname:kept forward their oxen forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.nsCPUusage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['netscaler_lbvsvr_lb_method:source_ip_source_port', 'netscaler_lbvsvr_persistance_type:cookie_insert'],
        ['netscaler_lbvsvr_lb_method:source_ip_source_port', 'netscaler_lbvsvr_persistance_type:source_ip'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.lbvsvrActiveConn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.lbvsvrAvgSvrTTFB', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.lbvsvrPersistenceTimeOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_svcgrp_svc_group_full_name:forward Jaded but their but but driving',
            'netscaler_svcgrp_svc_group_name:driving zombies zombies Jaded forward quaintly',
            'netscaler_svcgrp_svc_group_state:enabled',
            'netscaler_svcgrp_svc_group_type:rpcserver',
        ],
        [
            'netscaler_svcgrp_svc_group_full_name:forward their forward kept driving driving oxen',
            'netscaler_svcgrp_svc_group_name:but acted forward driving oxen acted',
            'netscaler_svcgrp_svc_group_state:disabled',
            'netscaler_svcgrp_svc_group_type:rpcserver',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.serviceGroup', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_ssl_cert_key_name:driving but acted zombies quaintly oxen their their'],
        ['netscaler_ssl_cert_key_name:quaintly driving forward zombies kept Jaded zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sslDaysToExpire', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_vsvr_active_active_state:backup', 'netscaler_vsvr_full_name:but quaintly'],
        ['netscaler_vsvr_active_active_state:not_applicable', 'netscaler_vsvr_full_name:their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.vsvrCurServicesDown', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrCurServicesUp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrCurSrvrConnections', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.netscaler.vsvrHealth', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.netscaler.vsvrRequestRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrRxBytesRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrSoThreshold', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrSynfloodRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotSpillOvers', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalClients', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalRequestBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalRequests', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalResponseBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalResponses', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalServers', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTotalServicesBound', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.vsvrTxBytesRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_svc_ip_address:42.229.1.138',
            'netscaler_svc_port:13',
            'netscaler_svc_service_full_name:zombies quaintly acted zombies kept driving driving Jaded',
            'netscaler_svc_service_name:quaintly driving quaintly their acted',
            'netscaler_svc_service_type:httpserver',
        ],
        [
            'netscaler_svc_ip_address:215.131.83.58',
            'netscaler_svc_port:19',
            'netscaler_svc_service_full_name:quaintly kept Jaded Jaded zombies quaintly but',
            'netscaler_svc_service_name:their oxen zombies kept oxen Jaded zombies forward forward',
            'netscaler_svc_service_type:http',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.svcActiveConn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcActiveTransactions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcAvgSvrTTFB', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcAvgTransactionTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcCurClntConnections', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcEstablishedConn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcRequestRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcRxBytesRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcSurgeCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTotalPktsRecvd', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTotalPktsSent', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTotalRequestBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTotalRequests', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTotalResponseBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTotalResponses', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.svcTxBytesRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_server_ip_address:220.157.222.120',
            'netscaler_server_name:acted forward acted but their oxen Jaded quaintly quaintly',
            'netscaler_server_state:unknown',
        ],
        [
            'netscaler_server_ip_address:18.109.172.33',
            'netscaler_server_name:quaintly kept kept but driving oxen',
            'netscaler_server_state:unknown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.server', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'citrix-netscaler Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'citrix-netscaler.device.name',
        'profile': 'citrix-netscaler',
        'serial_number': 'Jaded but acted acted',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5951.1',
        'vendor': 'citrix',
        'version': 'kept forward oxen but zombies forward Jaded',
        'device_type': 'load_balancer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
