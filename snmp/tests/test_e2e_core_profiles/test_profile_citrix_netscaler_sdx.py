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


def test_e2e_profile_citrix_netscaler_sdx(dd_agent_check):
    profile = 'citrix-netscaler-sdx'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:citrix-netscaler-sdx',
        'snmp_host:citrix-netscaler-sdx.device.name',
        'device_hostname:citrix-netscaler-sdx.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'netscaler_sdx_system_bios_version:zombies',
        'netscaler_sdx_system_gateway:acted quaintly oxen',
        'netscaler_sdx_system_gateway_type:ipv4',
        'netscaler_sdx_system_netmask:driving acted',
        'netscaler_sdx_system_netmask_type:unknown',
        'netscaler_sdx_system_network_interface:driving their zombies forward oxen',
        'netscaler_sdx_system_product:quaintly forward zombies oxen acted kept',
        'netscaler_sdx_system_svm_ip_address:quaintly',
        'netscaler_sdx_system_svm_ip_address_type:ipv4z',
        'netscaler_sdx_system_xen_ip_address:their driving oxen driving',
        'netscaler_sdx_system_xen_ip_address_type:ipv4z',
    ]

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'netscaler_sdx_hardware_resource_name:but kept forward zombies driving',
            'netscaler_sdx_hardware_resource_status:Jaded oxen driving',
        ],
        [
            'netscaler_sdx_hardware_resource_name:oxen acted kept',
            'netscaler_sdx_hardware_resource_status:oxen acted but quaintly kept acted their their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sdx.hardwareResource', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_sdx_software_resource_name:kept their their',
            'netscaler_sdx_software_resource_status:driving forward but oxen driving forward',
        ],
        [
            'netscaler_sdx_software_resource_name:oxen Jaded their but oxen quaintly driving driving kept',
            'netscaler_sdx_software_resource_status:forward kept their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sdx.softwareResource', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_sdx_sr_bay_number:Jaded but forward zombies their quaintly',
            'netscaler_sdx_sr_name:forward their quaintly zombies Jaded',
            'netscaler_sdx_sr_status:kept Jaded but acted',
        ],
        [
            'netscaler_sdx_sr_bay_number:driving their quaintly',
            'netscaler_sdx_sr_name:oxen oxen',
            'netscaler_sdx_sr_status:forward oxen acted kept quaintly oxen',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netscaler.sdx.srSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.netscaler.sdx.srUtilized', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_sdx_interface_mapped_port:acted zombies oxen their quaintly Jaded oxen',
            'netscaler_sdx_interface_port:forward Jaded zombies zombies driving',
            'netscaler_sdx_interface_state:zombies',
        ],
        [
            'netscaler_sdx_interface_mapped_port:quaintly oxen but oxen quaintly acted',
            'netscaler_sdx_interface_port:driving acted acted',
            'netscaler_sdx_interface_state:acted zombies but their Jaded kept oxen zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sdx.interfaceRxBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.interfaceRxErrors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.interfaceRxPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.interfaceTxBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.interfaceTxErrors', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.interfaceTxPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_sdx_hm_name:acted acted their acted driving quaintly',
            'netscaler_sdx_hm_status:acted acted acted but their',
            'netscaler_sdx_hm_unit:quaintly forward kept zombies acted forward but forward quaintly',
        ],
        [
            'netscaler_sdx_hm_name:their forward kept their zombies quaintly',
            'netscaler_sdx_hm_status:quaintly driving driving their quaintly driving acted but zombies',
            'netscaler_sdx_hm_unit:but their oxen kept zombies',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sdx.hmCurrentValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netscaler_sdx_xen_ip_address:?4a6164656420666f7277617264207a6f6d62696573',
            'netscaler_sdx_xen_ip_address_type:ipv4',
            'netscaler_sdx_xen_uuid:driving driving but',
        ],
        [
            'netscaler_sdx_xen_ip_address:?7468656972204a6164656420666f7277617264',
            'netscaler_sdx_xen_ip_address_type:unknown',
            'netscaler_sdx_xen_uuid:forward their',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'netscaler_sdx_ns_description:Jaded forward quaintly oxen zombies',
            'netscaler_sdx_ns_gateway:?6b657074204a6164656420717561696e746c79206b65707420666f727761726420666f72776172642074686569722064726976696e67206f78656e',
            'netscaler_sdx_ns_gateway_type:ipv6z',
            'netscaler_sdx_ns_ha_ip_address:?7a6f6d6269657320746865697220627574207a6f6d62696573204a61646564207a6f6d62696573206b657074',
            'netscaler_sdx_ns_ha_ip_address_type:ipv4',
            'netscaler_sdx_ns_ha_master_state:forward forward oxen driving their zombies kept zombies but',
            'netscaler_sdx_ns_ha_sync:kept oxen but but oxen their',
            'netscaler_sdx_ns_hostname:driving zombies kept',
            'netscaler_sdx_ns_instance_state:zombies quaintly driving but Jaded Jaded forward kept',
            'netscaler_sdx_ns_ip_address:?717561696e746c792064726976696e67204a6164656420717561696e746c79206f78656e204a6164656420666f7277617264',
            'netscaler_sdx_ns_ip_address_type:ipv4',
            'netscaler_sdx_ns_name:driving driving kept their oxen zombies quaintly',
            'netscaler_sdx_ns_netmask:?62757420666f727761726420717561696e746c7920616374656420717561696e746c79206f78656e',
            'netscaler_sdx_ns_netmask_type:ipv6',
            'netscaler_sdx_ns_node_state:forward their forward',
            'netscaler_sdx_ns_profile_name:zombies acted driving zombies their forward',
            'netscaler_sdx_ns_throughput:their acted oxen',
            'netscaler_sdx_ns_version:Jaded quaintly acted zombies driving',
            'netscaler_sdx_ns_vm_description:oxen quaintly',
            'netscaler_sdx_ns_vm_state:their their driving zombies acted driving but acted',
        ],
        [
            'netscaler_sdx_ns_description:quaintly zombies driving quaintly but Jaded but quaintly quaintly',
            'netscaler_sdx_ns_gateway:?627574204a6164656420666f727761726420627574204a61646564206b657074207a6f6d62696573207a6f6d62696573207468656972',
            'netscaler_sdx_ns_gateway_type:ipv6',
            'netscaler_sdx_ns_ha_ip_address:?717561696e746c79207468656972204a61646564204a61646564207a6f6d62696573207a6f6d6269657320666f7277617264207468656972207468656972',
            'netscaler_sdx_ns_ha_ip_address_type:ipv6',
            'netscaler_sdx_ns_ha_master_state:their their',
            'netscaler_sdx_ns_ha_sync:driving driving driving Jaded',
            'netscaler_sdx_ns_hostname:driving forward acted Jaded Jaded',
            'netscaler_sdx_ns_instance_state:driving kept oxen Jaded driving but but',
            'netscaler_sdx_ns_ip_address:?4a6164656420717561696e746c7920616374656420666f7277617264',
            'netscaler_sdx_ns_ip_address_type:dns',
            'netscaler_sdx_ns_name:forward',
            'netscaler_sdx_ns_netmask:?717561696e746c7920666f7277617264206163746564206163746564204a616465642064726976696e67',
            'netscaler_sdx_ns_netmask_type:dns',
            'netscaler_sdx_ns_node_state:oxen',
            'netscaler_sdx_ns_profile_name:but their oxen their but oxen driving Jaded kept',
            'netscaler_sdx_ns_throughput:their acted zombies quaintly Jaded but their Jaded',
            'netscaler_sdx_ns_version:acted',
            'netscaler_sdx_ns_vm_description:quaintly forward forward Jaded acted zombies',
            'netscaler_sdx_ns_vm_state:but oxen',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netscaler.sdx.nsHttpReq', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.nsNsCPUUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netscaler.sdx.nsNsMemoryUsage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
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
        'serial_number': 'driving oxen oxen Jaded quaintly but',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5951.6',
        'vendor': 'citrix',
        'version': 'their acted Jaded',
        'device_type': 'load_balancer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
