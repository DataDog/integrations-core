# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_citrix_netscaler(dd_agent_check):
    config = create_e2e_core_test_config('citrix-netscaler')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:citrix-netscaler',
        'snmp_host:citrix-netscaler.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + [
        'netscaler_sys_build_version:their',
        'netscaler_sys_hardware_serial_number:but but acted',
        'netscaler_sys_hardware_version_desc:but',
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
    aggregator.assert_metric('snmp.netscaler.haCurState', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.haCurStatus', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.haPeerState', metric_type=aggregator.GAUGE, tags=common_tags)
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
    aggregator.assert_metric('snmp.netscaler.sysHighAvailabilityMode', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.syssvcCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sysupsvcCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.sysupsvcitmCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpCurClientConn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.netscaler.tcpCurClientEstablished', metric_type=aggregator.GAUGE, tags=common_tags)
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
            'netscaler_vsvr_name:Jaded quaintly driving kept',
            'netscaler_vsvr_port:1',
            'netscaler_vsvr_state:up',
            'netscaler_vsvr_type:ssl_bridge',
        ],
        [
            'netscaler_vsvr_name:their Jaded but forward their zombies Jaded acted but',
            'netscaler_vsvr_port:25',
            'netscaler_vsvr_state:unknown',
            'netscaler_vsvr_type:ha',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.vsvrCurClntConnections', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_sys_health_disk_name:oxen driving Jaded kept'],
        ['netscaler_sys_health_disk_name:quaintly'],
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
        ['netscaler_if_media:forward zombies', 'netscaler_if_name:their'],
        [
            'netscaler_if_media:quaintly Jaded quaintly kept quaintly but acted',
            'netscaler_if_name:but oxen driving Jaded acted zombies oxen kept kept',
        ],
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
            'netscaler_vserver_full_name:forward oxen driving',
            'netscaler_vsvr_service_full_name:forward quaintly zombies Jaded but',
            'netscaler_vsvr_service_name:their oxen acted but driving forward',
        ],
        [
            'netscaler_vserver_full_name:kept quaintly oxen their forward zombies acted kept oxen',
            'netscaler_vsvr_service_full_name:driving',
            'netscaler_vsvr_service_name:Jaded driving acted acted driving',
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
        ['netscaler_ns_cp_uname:Jaded driving quaintly'],
        ['netscaler_ns_cp_uname:acted forward their zombies but their oxen zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.nsCPUusage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['netscaler_lbvsvr_lb_method:asynchronous_mac', 'netscaler_lbvsvr_persistance_type:group_source_id'],
        ['netscaler_lbvsvr_lb_method:least_packets', 'netscaler_lbvsvr_persistance_type:source_i_pdestination_ip'],
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
            'netscaler_svcgrp_svc_group_full_name:oxen driving forward quaintly',
            'netscaler_svcgrp_svc_group_name:quaintly but kept oxen',
            'netscaler_svcgrp_svc_group_state:disabled',
            'netscaler_svcgrp_svc_group_type:nat',
        ],
        [
            'netscaler_svcgrp_svc_group_full_name:oxen oxen oxen kept forward Jaded',
            'netscaler_svcgrp_svc_group_name:Jaded',
            'netscaler_svcgrp_svc_group_state:disabled',
            'netscaler_svcgrp_svc_group_type:ha',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.serviceGroup', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_ssl_cert_key_name:Jaded but kept kept'],
        ['netscaler_ssl_cert_key_name:forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sslDaysToExpire', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['netscaler_vsvr_active_active_state:backup', 'netscaler_vsvr_full_name:Jaded kept acted but'],
        ['netscaler_vsvr_active_active_state:not_applicable', 'netscaler_vsvr_full_name:but'],
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
            'snmp.netscaler.vsvrSoThreshold', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
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

    tag_rows = [
        [
            'netscaler_svc_port:11',
            'netscaler_svc_service_full_name:forward quaintly oxen driving',
            'netscaler_svc_service_name:Jaded forward quaintly quaintly their',
            'netscaler_svc_service_type:monitor',
        ],
        [
            'netscaler_svc_port:20',
            'netscaler_svc_service_full_name:acted zombies',
            'netscaler_svc_service_name:driving their driving their acted but Jaded',
            'netscaler_svc_service_type:rip',
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

    tag_rows = [
        ['netscaler_server_name:kept forward driving oxen kept forward', 'netscaler_server_state:unknown'],
        ['netscaler_server_name:oxen zombies acted', 'netscaler_server_state:busy'],
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
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5951.1',
        'vendor': 'citrix',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
