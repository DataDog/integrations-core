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


def test_e2e_profile_a10_thunder(dd_agent_check):
    profile = 'a10-thunder'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:a10-thunder',
        'snmp_host:a10-thunder.device.name',
        'device_hostname:a10-thunder.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'ax_sys_a_fle_x_engine_version:their quaintly acted Jaded driving their ' 'forward',
        'ax_sys_firmware_version:oxen their quaintly kept quaintly zombies',
        'ax_sys_serial_number:their zombies zombies acted kept their quaintly',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.axAppGlobalBufferConfigLimit', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalBufferCurrentUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalCurrentConnections', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalL7Requests', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalNewConnections', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalNewIPNatConnections', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalNewL4Connections', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalNewL7Connections', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.axAppGlobalTotalSSLConnections', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.axConnReuseStatTotalActivePersist', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axConnReuseStatTotalEstablished', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axConnReuseStatTotalOpenPersist', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axConnReuseStatTotalTerminated', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axGlobalAppPacketDrop', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axGlobalTotalAppPacketDrop', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axGlobalTotalL4Session', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axGlobalTotalThroughput', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axPowerSupplyVoltageTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatConnCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatConnFree', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatConnSMPAllocated', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatConnSMPFree', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatFreeCurrentConns', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.axSessionGlobalStatNonTcpUdpIPSession', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.axSessionGlobalStatOther', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatReverseNATTCP', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatReverseNATUDP', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatTCPEstablished', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatTCPHalfOpen', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatTCPSynHalfOpen', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSessionGlobalStatUDP', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSysDiskFreeSpace', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSysDiskTotalSpace', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.axSysHwPhySystemTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['ax_fan_name:driving Jaded oxen driving zombies oxen forward their', 'ax_fan_status:ok_med_high'],
        ['ax_fan_name:driving zombies', 'ax_fan_status:ok_med_high'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.axFanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ax_power_supply_voltage_description:kept forward oxen forward', 'ax_power_supply_voltage_status:unknown'],
        [
            'ax_power_supply_voltage_description:zombies but Jaded quaintly their their forward',
            'ax_power_supply_voltage_status:normal',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.axPowerSupplyVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ax_power_supply_name:driving but but acted but', 'ax_power_supply_status:off'],
        ['ax_power_supply_name:oxen Jaded quaintly', 'ax_power_supply_status:on'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.axSysPowerSupplyStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['ax_app_global_system_resource_name:kept acted their zombies driving driving but'],
        ['ax_app_global_system_resource_name:their zombies oxen kept but oxen their zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.axAppGlobalAllowedCurrentValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axAppGlobalAllowedMaxValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ax_server_enabled_state:enabled',
            'ax_server_monitor_state:disabled',
            'ax_server_name:but quaintly quaintly driving forward',
        ],
        [
            'ax_server_enabled_state:enabled',
            'ax_server_monitor_state:down',
            'ax_server_name:acted acted Jaded kept acted',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.axServer', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ax_server_stat_name:oxen but oxen driving', 'ax_server_stat_server_status:up'],
        [
            'ax_server_stat_name:zombies Jaded zombies kept oxen oxen zombies Jaded driving',
            'ax_server_stat_server_status:down',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.axServerStatServerCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axServerStatServerTotalCurrL7Reqs', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ax_service_group_display_status:all_up',
            'ax_service_group_name:driving quaintly zombies zombies forward forward',
            'ax_service_group_type:tcp',
        ],
        [
            'ax_service_group_display_status:partial_up',
            'ax_service_group_lb_algorithm:service_least_connection',
            'ax_service_group_name:driving zombies acted driving their',
            'ax_service_group_type:udp',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.axServiceGroup', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ax_virtual_server_display_status:functional_up',
            'ax_virtual_server_enabled:enabled',
            'ax_virtual_server_ha_group:driving their Jaded',
            'ax_virtual_server_name:forward',
        ],
        [
            'ax_virtual_server_display_status:partial_up',
            'ax_virtual_server_enabled:disabled',
            'ax_virtual_server_ha_group:but acted kept zombies forward kept quaintly oxen zombies',
            'ax_virtual_server_name:oxen but quaintly forward driving their driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.axVirtualServer', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'ax_virtual_server_stat_address:Jaded zombies',
            'ax_virtual_server_stat_display_status:up',
            'ax_virtual_server_stat_name:Jaded oxen Jaded acted forward their oxen',
            'ax_virtual_server_stat_status:down',
        ],
        [
            'ax_virtual_server_stat_address:driving driving their oxen forward acted',
            'ax_virtual_server_stat_display_status:disabled',
            'ax_virtual_server_stat_name:but driving quaintly kept zombies but',
            'ax_virtual_server_stat_status:up',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.axVirtualServerStatBytesIn', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatBytesOut', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatPersistConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatPktsIn', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatPktsOut', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatTotConns', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatTotalCurrL7Reqs', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatTotalL7Reqs', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.axVirtualServerStatTotalSuccL7Reqs', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ax_virtual_server_port_stat_address:zombies Jaded forward zombies acted forward quaintly forward',
            'ax_virtual_server_port_stat_name:quaintly forward Jaded',
            'ax_virtual_server_stat_port_display_status:all_up',
            'ax_virtual_server_stat_port_num:18',
            'ax_virtual_server_stat_port_status:down',
        ],
        [
            'ax_virtual_server_port_stat_address:zombies driving driving kept zombies Jaded quaintly but',
            'ax_virtual_server_port_stat_name:oxen Jaded',
            'ax_virtual_server_stat_port_display_status:all_up',
            'ax_virtual_server_stat_port_num:19',
            'ax_virtual_server_stat_port_status:up',
            'ax_virtual_server_stat_port_type:http',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.axVirtualServerPortStatCurConns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'Thunder Series Unified Application Service Gateway TH5630, ACOS 4.1.0-P5, '
        '(Comment: This profile is partially generated from MIB)',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'a10-thunder.device.name',
        'profile': 'a10-thunder',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.22610.1.3.28',
        'vendor': 'a10',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
