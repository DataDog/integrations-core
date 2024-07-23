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


def test_e2e_profile_aruba_wireless_controller(dd_agent_check):
    profile = 'aruba-wireless-controller'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:aruba-wireless-controller',
        'snmp_host:aruba-wireless-controller.device.name',
        'device_hostname:aruba-wireless-controller.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'wlsx_model_name:their driving kept their kept',
        'wlsx_switch_license_serial_number:forward kept forward',
        'wlsx_switch_role:local',
        'wlsx_sys_ext_hw_version:Jaded zombies',
        'wlsx_sys_ext_sw_version:Jaded but acted zombies kept forward driving acted acted',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.haActiveAPs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.haStandbyAPs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.haTotalAPs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.wlsxNumOfUsers8021x', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.wlsxNumOfUsersCP', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.wlsxNumOfUsersMAC', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.wlsxNumOfUsersStateful8021x', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.wlsxNumOfUsersVPN', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.wlsxSysExtPacketLossPercent', metric_type=aggregator.GAUGE, tags=common_tags)

    tag_row = ['sys_x_storage_name:quaintly oxen their oxen quaintly driving but zombies', 'sys_x_storage_type:ram']
    aggregator.assert_metric('snmp.sysXStorageSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
    aggregator.assert_metric('snmp.sysXStorageUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_row = [
        'ap_current_channel:3',
        'ap_essid:quaintly but kept kept their acted',
        'ap_load_balancing:true',
        'ap_phy_type:dot11g',
        'ap_type:am',
    ]
    aggregator.assert_metric('snmp.apChannelNoise', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
    aggregator.assert_metric('snmp.apSignalToNoiseRatio', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    aggregator.assert_metric(
        'snmp.apBSSBwRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSFrameFragmentationRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSFrameLowSpeedRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSFrameNonUnicastRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSFrameReceiveErrorRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSFrameRetryRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSRxBytes', metric_type=aggregator.COUNT, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSRxPackets', metric_type=aggregator.COUNT, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSTxBytes', metric_type=aggregator.COUNT, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apBSSTxPackets', metric_type=aggregator.COUNT, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apChannelBwRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apChannelFrameFragmentationRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apChannelFrameLowSpeedRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apChannelFrameNonUnicastRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apChannelFrameReceiveErrorRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )
    aggregator.assert_metric(
        'snmp.apChannelFrameRetryRate', metric_type=aggregator.GAUGE, tags=common_tags + ['ap_stats_channel:4']
    )

    tags_row = [['ha_membership:MemberGroup1']]
    for tag_row in tags_row:
        aggregator.assert_metric('snmp.haAPHbtTunnels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.haActiveVapTunnels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.haStandbyVapTunnels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.haTotalVapTunnels', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tags_row = [
        [
            'wlan_sta_phy_type:wired',
            'wlan_sta_ht_mode:he40',
            'wlan_sta_access_point_essid:HomeWiFi',
            'wlan_sta_channel:6',
            'wlan_sta_vlan_id:1',
            'wlan_sta_is_authenticated:true',
            'wlan_sta_is_associated:false',
        ],
    ]
    for tag_row in tags_row:
        aggregator.assert_metric('snmp.wlanStaRSSI', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.wlanStaTransmitRate', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.wlanStaTransmitRateCode', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.wlanStaUpTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tags_row = [
        ['wlan_sta_channel_num:3'],
    ]
    for tag_row in tags_row:
        aggregator.assert_metric('snmp.wlanStaRxBytes64', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.wlanStaTxBytes64', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'aruba-wireless-controller Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'aruba-wireless-controller.device.name',
        'profile': 'aruba-wireless-controller',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14823.1.1.1',
        'vendor': 'aruba',
        'device_type': 'wlc',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
