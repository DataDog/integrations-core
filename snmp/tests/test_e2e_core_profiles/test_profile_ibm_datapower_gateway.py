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


def test_e2e_profile_ibm_datapower_gateway(dd_agent_check):
    profile = 'ibm-datapower-gateway'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:ibm-datapower-gateway',
        'snmp_host:ibm-datapower-gateway.device.name',
        'device_hostname:ibm-datapower-gateway.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.ibm.dpStatusConnectionsAcceptedoneDay', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusConnectionsAcceptedoneHour', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusConnectionsAcceptedoneMinute', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusConnectionsAcceptedtenMinutes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusConnectionsAcceptedtenSeconds', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorschassis1rpm', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorschassis2rpm', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorschassis3rpm', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorscpu1Temp', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorscpu1rpm', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorscpu2Temp', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorscpu2rpm', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusEnvironmentalSensorssystemTemp', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusFilesystemStatusFreeEncrypted', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusFilesystemStatusFreeInternal', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusFilesystemStatusFreeTemporary', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusFilesystemStatusTotalEncrypted', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusFilesystemStatusTotalInternal', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ibm.dpStatusFilesystemStatusTotalTemporary', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.ibm.dpStatusSystemUsageLoad', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummaryclosed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummaryclosewait', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummaryclosing', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummaryestablished', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummaryfinwait1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummaryfinwait2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummarylastack', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummarylisten', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummarysynreceived', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummarysynsent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ibm.dpStatusTCPSummarytimewait', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'ibm_dp_status_log_target_status_log_target:Jaded zombies their',
            'ibm_dp_status_log_target_status_status:active',
        ],
        [
            'ibm_dp_status_log_target_status_log_target:acted their zombies oxen oxen',
            'ibm_dp_status_log_target_status_status:suspended',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ibm.dpStatusLogTargetStatusEventsDropped', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusLogTargetStatusEventsPending', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusLogTargetStatusEventsProcessed', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'ibm_dp_status_network_interface_status_admin_status:up',
            'ibm_dp_status_network_interface_status_interface_type:ethernet',
            'ibm_dp_status_network_interface_status_ip:190.114.96.169',
            'ibm_dp_status_network_interface_status_ip_type:ipv4',
            'ibm_dp_status_network_interface_status_mac_address:11:11:11:11:11:11',
            'ibm_dp_status_network_interface_status_name:but but quaintly',
            'ibm_dp_status_network_interface_status_oper_status:dormant',
        ],
        [
            'ibm_dp_status_network_interface_status_admin_status:up',
            'ibm_dp_status_network_interface_status_interface_type:ethernet',
            'ibm_dp_status_network_interface_status_ip:93.22.18.75',
            'ibm_dp_status_network_interface_status_ip_type:dns',
            'ibm_dp_status_network_interface_status_mac_address:11:11:11:11:11:11',
            'ibm_dp_status_network_interface_status_name:but quaintly kept oxen forward but',
            'ibm_dp_status_network_interface_status_oper_status:unknown',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusRxDrops2', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusRxErrors2', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusRxHCBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusRxHCPackets',
            metric_type=aggregator.COUNT,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusTxDrops2', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusTxErrors2', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusTxHCBytes', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ibm.dpStatusNetworkInterfaceStatusTxHCPackets',
            metric_type=aggregator.COUNT,
            tags=common_tags + tag_row,
        )

    # --- TEST METADATA ---
    device = {
        'description': 'ibm-datapower-gateway Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'ibm-datapower-gateway.device.name',
        'profile': 'ibm-datapower-gateway',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14685.1.8',
        'vendor': 'ibm',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
