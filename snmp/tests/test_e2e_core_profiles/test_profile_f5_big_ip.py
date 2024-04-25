# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..metrics import (
    IF_BANDWIDTH_USAGE,
    IF_COUNTS,
    IF_GAUGES,
    IF_RATES,
    IF_SCALAR_GAUGE,
    IP_COUNTS,
)
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_all_profile_metrics_and_tags_covered,
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_f5_big_ip(dd_agent_check):
    profile = 'f5-big-ip'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:f5-big-ip',
        'snmp_host:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'device_hostname:f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'device_vendor:f5',
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.ltmNodeAddrNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ltmPoolMemberNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ltmPoolNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ltmVirtualServNumber', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysClientsslStatCurConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysClientsslStatDecryptedBytesIn', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysClientsslStatDecryptedBytesOut', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysClientsslStatEncryptedBytesIn', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysClientsslStatEncryptedBytesOut', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysClientsslStatHandshakeFailures', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysGlobalHostOtherMemoryTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysGlobalHostOtherMemoryUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysGlobalHostSwapTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysGlobalHostSwapUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysGlobalTmmStatMemoryTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysGlobalTmmStatMemoryUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysStatMemoryTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysStatMemoryUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatAcceptfails', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatAccepts', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatCloseWait', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatConnects', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatConnfails', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatFinWait', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatOpen', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysTcpStatTimeWait', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sysUdpStatAcceptfails', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysUdpStatAccepts', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysUdpStatConnects', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysUdpStatConnfails', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.sysUdpStatOpen', metric_type=aggregator.GAUGE, tags=common_tags)

    tag_rows = [
        ['cpu:0'],
        ['cpu:1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sysMultiHostCpuUsageRatio', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['cpu:0'],
        ['cpu:1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.sysMultiHostCpuIdle', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysMultiHostCpuIowait', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysMultiHostCpuIrq', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysMultiHostCpuNice', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.sysMultiHostCpuSoftirq', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.sysMultiHostCpuSystem', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.sysMultiHostCpuUser', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['server:server1'],
        ['server:server2'],
        ['server:server3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmVirtualServConnLimit', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ltmVirtualServEnabled', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ltm_vs_status_avail_state:blue'],
        ['ltm_vs_status_avail_state:gray'],
        ['ltm_vs_status_avail_state:green', 'ltm_vs_status_enabled_state:enabled', 'ltm_vs_status_name:server1'],
        ['ltm_vs_status_avail_state:none', 'ltm_vs_status_enabled_state:none'],
        ['ltm_vs_status_avail_state:red', 'ltm_vs_status_enabled_state:disabledbyparent', 'ltm_vs_status_name:server3'],
        ['ltm_vs_status_avail_state:yellow', 'ltm_vs_status_enabled_state:disabled', 'ltm_vs_status_name:server2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ltmVsStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['server:server1'],
        ['server:server2'],
        ['server:server3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientBytesIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientBytesOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientPktsIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientPktsOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatCurrentConnsPerSec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatDurationRateExceeded', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatVsUsageRatio1m', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatVsUsageRatio5m', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatVsUsageRatio5s', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['server:server1'],
        ['server:server2'],
        ['server:server3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientEvictedConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientSlowKilled', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatClientTotConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatNoNodesErrors', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmVirtualServStatTotRequests', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['node:node1'],
        ['node:node2'],
        ['node:node3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ltmNodeAddrConnLimit', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ltmNodeAddrDynamicRatio', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrMonitorState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrMonitorStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ltmNodeAddrRatio', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ltmNodeAddrSessionStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['node:node1', 'monitor_state:unchecked', 'monitor_status:down_manual_resume'],
        ['node:node2', 'monitor_state:inband_down', 'monitor_status:inband_down'],
        ['node:node3', 'monitor_state:irule_down', 'monitor_status:forced_up'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ltmNodeAddr', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['node:node1'],
        ['node:node2'],
        ['node:node3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatCurSessions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatCurrentConnsPerSec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatDurationRateExceeded', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatServerBytesIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatServerBytesOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatServerCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatServerPktsIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatServerPktsOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['node:node1'],
        ['node:node2'],
        ['node:node3'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatServerTotConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmNodeAddrStatTotRequests', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['pool:pool1'],
        ['pool:pool2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmPoolActiveMemberCnt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolDynamicRatioSum', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ltmPoolMemberCnt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['pool:pool1'],
        ['pool:pool2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmPoolStatConnqAgeHead', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ltmPoolStatConnqDepth', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ltmPoolStatCurSessions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatServerBytesIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatServerBytesOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatServerCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatServerPktsIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatServerPktsOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['pool:pool1'],
        ['pool:pool2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmPoolStatConnqServiced', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatServerTotConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolStatTotRequests', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['node:node1', 'pool:pool1'],
        ['node:node2', 'pool:pool1'],
        ['node:node3', 'pool:pool2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmPoolMemberConnLimit', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberDynamicRatio', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberMonitorState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberMonitorStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.ltmPoolMemberRatio', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.ltmPoolMemberSessionStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['node:node1', 'pool:pool1', 'monitor_state:down'],
        ['node:node2', 'pool:pool1', 'monitor_state:down_manual_resume'],
        ['node:node3', 'pool:pool2', 'monitor_state:checking'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ltmPoolMember', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['node:node1', 'pool:pool1'],
        ['node:node2', 'pool:pool1'],
        ['node:node3', 'pool:pool2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatConnqAgeHead', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatConnqDepth', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatCurSessions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatCurrentConnsPerSec', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatDurationRateExceeded', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatServerBytesIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatServerBytesOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatServerCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatServerPktsIn', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatServerPktsOut', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['node:node1', 'pool:pool1'],
        ['node:node2', 'pool:pool1'],
        ['node:node3', 'pool:pool2'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatConnqServiced', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatServerTotConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ltmPoolMemberStatTotRequests', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    interfaces = [
        (32, 'mgmt', 'desc1'),
        (48, '1.0', 'desc2'),
        (80, '/Common/http-tunnel', 'desc3'),
        (96, '/Common/socks-tunnel', 'desc4'),
        (112, '/Common/internal', 'desc5'),
    ]
    interfaces_with_bandwidth_usage = {
        '1.0',
        'mgmt',
        '/Common/internal',
    }

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags, count=2)
    for index, interface, desc in interfaces:
        interface_tags = [
            'interface:{}'.format(interface),
            'interface_alias:{}'.format(desc),
            'interface_index:{}'.format(index),
        ] + common_tags
        for metric in IF_COUNTS:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=interface_tags, count=1
            )
        for metric in IF_RATES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=interface_tags, count=1
            )

        if interface in interfaces_with_bandwidth_usage:
            for metric in IF_BANDWIDTH_USAGE:
                aggregator.assert_metric(
                    'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=interface_tags, count=1
                )

        for metric in IF_GAUGES:
            aggregator.assert_metric(
                'snmp.{}'.format(metric),
                metric_type=aggregator.GAUGE,
                tags=interface_tags,
                count=2,
            )

    for version in ['ipv4', 'ipv6']:
        ip_tags = ['ipversion:{}'.format(version)] + common_tags
        for metric in IP_COUNTS:
            aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=ip_tags, count=1)

    aggregator.assert_metric('snmp.sysUpTimeInstance', count=2)
    aggregator.assert_metric('snmp.cpu.usage', count=4)
    aggregator.assert_metric('snmp.ifInSpeed', count=6)
    aggregator.assert_metric('snmp.ifOutSpeed', count=6)
    aggregator.assert_metric('snmp.memory.total', count=2)
    aggregator.assert_metric('snmp.memory.usage', count=2)
    aggregator.assert_metric('snmp.memory.used', count=2)

    # --- TEST METADATA ---
    device = {
        'description': 'BIG-IP Virtual Edition : Linux 3.10.0-862.14.4.el7.ve.x86_64 : BIG-IP software release 15.0.1, '
        'build 0.0.11',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'f5-big-ip-adc-good-byol-1-vm.c.datadog-integrations-lab.internal',
        'os_name': 'Linux',
        'os_version': '3.10.0-862.14.4.el7.ve.x86_64',
        'product_name': 'BIG-IP',
        'serial_number': '26ff4a4d-190e-12ac-d4257ed36ba6',
        'location': 'Network Closet 1',
        'model': 'Z100',
        'profile': 'f5-big-ip',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.3375.2.1.3.4.43',
        'vendor': 'f5',
        'version': '15.0.1',
        'device_type': 'load_balancer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
