# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,

    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_citrix_netscaler_sdx(dd_agent_check):
    config = create_e2e_core_test_config('citrix-netscaler-sdx')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:citrix-netscaler-sdx',
        'snmp_host:citrix-netscaler-sdx.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + ['netscaler_sdx_system_bios_version:zombies',
 'netscaler_sdx_system_dns:driving driving Jaded their oxen',
 'netscaler_sdx_system_gateway:acted quaintly oxen',
 'netscaler_sdx_system_gateway_type:1',
 'netscaler_sdx_system_netmask:driving acted',
 'netscaler_sdx_system_netmask_type:0',
 'netscaler_sdx_system_network_interface:driving their zombies forward oxen',
 'netscaler_sdx_system_product:quaintly forward zombies oxen acted kept',
 'netscaler_sdx_system_svm_ip_address:quaintly',
 'netscaler_sdx_system_svm_ip_address_type:3',
 'netscaler_sdx_system_xen_ip_address:their driving oxen driving',
 'netscaler_sdx_system_xen_ip_address_type:3']

    # --- TEST EXTENDED METRICS ---


    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
         ['netscaler_sdx_hardware_resource_name:but kept forward zombies driving', 'netscaler_sdx_hardware_resource_status:Jaded oxen driving'],
         ['netscaler_sdx_hardware_resource_name:oxen acted kept', 'netscaler_sdx_hardware_resource_status:oxen acted but quaintly kept acted their their'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.hardwareResource', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['netscaler_sdx_software_resource_name:kept their their', 'netscaler_sdx_software_resource_status:driving forward but oxen driving forward'],
         ['netscaler_sdx_software_resource_name:oxen Jaded their but oxen quaintly driving driving kept', 'netscaler_sdx_software_resource_status:forward kept their'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.softwareResource', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['netscaler_sdx_sr_name:oxen oxen', 'netscaler_sdx_sr_bay_number:driving their quaintly', 'netscaler_sdx_sr_status:forward oxen acted kept quaintly oxen'],
         ['netscaler_sdx_sr_name:forward their quaintly zombies Jaded', 'netscaler_sdx_sr_bay_number:Jaded but forward zombies their quaintly', 'netscaler_sdx_sr_status:kept Jaded but acted'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.srSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.srUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.interfaceRxBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.interfaceRxErrors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.interfaceRxPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.interfaceTxBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.interfaceTxErrors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.interfaceTxPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.hmCurrentValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
         ['TODO'],

    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.nsHttpReq', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.nsNsCPUUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.nsNsMemoryUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.nsNsRx', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.netscaler.sdx.nsNsTx', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'citrix-netscaler-sdx Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'citrix-netscaler-sdx.device.name',
        'profile': 'citrix-netscaler-sdx',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5951.6',
        'vendor': 'citrix',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
