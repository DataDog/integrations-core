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
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_western_digital_mycloud_ex2_ultra(dd_agent_check):
    profile = 'western-digital-mycloud-ex2-ultra'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:western-digital-mycloud-ex2-ultra',
        'snmp_host:western-digital-mycloud-ex2-ultra.device.name',
        'device_hostname:western-digital-mycloud-ex2-ultra.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'wdmycloudex2_agent_ver:oxen quaintly zombies driving oxen their oxen',
        'wdmycloudex2_host_name:but oxen quaintly but Jaded',
        'wdmycloudex2_software_version:kept driving',
        'wdmycloudex2_ftp_server:disable',
        'wdmycloudex2_net_type:active_directory',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_host_resources_base(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'wdmycloudex2_volume_fs_type:acted quaintly',
            'wdmycloudex2_volume_name:driving',
            'wdmycloudex2_volume_num:23',
            'wdmycloudex2_volume_raid_level:forward acted Jaded but driving zombies',
        ],
        [
            'wdmycloudex2_volume_fs_type:driving but their their kept quaintly their acted quaintly',
            'wdmycloudex2_volume_name:quaintly but acted their their acted quaintly but',
            'wdmycloudex2_volume_num:3',
            'wdmycloudex2_volume_raid_level:quaintly acted quaintly their but but',
        ],
        [
            'wdmycloudex2_volume_fs_type:forward',
            'wdmycloudex2_volume_name:kept forward forward kept driving forward forward',
            'wdmycloudex2_volume_num:1',
            'wdmycloudex2_volume_raid_level:zombies driving quaintly oxen forward',
        ],
        [
            'wdmycloudex2_volume_fs_type:forward zombies oxen zombies their Jaded driving but but',
            'wdmycloudex2_volume_name:acted forward but but quaintly',
            'wdmycloudex2_volume_num:13',
            'wdmycloudex2_volume_raid_level:their quaintly their zombies driving',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.wdmycloudex2Volume', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'wdmycloudex2_disk_capacity:but kept kept zombies driving',
            'wdmycloudex2_disk_model:their',
            'wdmycloudex2_disk_num:9',
            'wdmycloudex2_disk_serial_number:oxen their their acted driving but Jaded oxen but',
            'wdmycloudex2_disk_vendor:driving quaintly',
        ],
        [
            'wdmycloudex2_disk_capacity:forward driving forward forward kept zombies',
            'wdmycloudex2_disk_model:forward acted',
            'wdmycloudex2_disk_num:22',
            'wdmycloudex2_disk_serial_number:forward their their driving forward',
            'wdmycloudex2_disk_vendor:oxen zombies',
        ],
        [
            'wdmycloudex2_disk_capacity:kept oxen',
            'wdmycloudex2_disk_model:Jaded oxen',
            'wdmycloudex2_disk_num:11',
            'wdmycloudex2_disk_serial_number:driving kept their zombies',
            'wdmycloudex2_disk_vendor:oxen Jaded quaintly driving acted',
        ],
        [
            'wdmycloudex2_disk_capacity:oxen kept forward their quaintly their Jaded',
            'wdmycloudex2_disk_model:forward zombies oxen forward oxen their quaintly',
            'wdmycloudex2_disk_num:20',
            'wdmycloudex2_disk_serial_number:oxen zombies forward but quaintly',
            'wdmycloudex2_disk_vendor:quaintly Jaded their oxen oxen forward but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.wdmycloudex2Disk', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'wdmycloudex2_ups_manufacturer:Jaded but acted kept quaintly Jaded',
            'wdmycloudex2_ups_mode:zombies oxen their acted acted but their driving',
            'wdmycloudex2_ups_num:30',
            'wdmycloudex2_ups_product:but kept oxen forward kept quaintly their their zombies',
            'wdmycloudex2_ups_status:acted their kept oxen their but',
        ],
        [
            'wdmycloudex2_ups_manufacturer:Jaded driving',
            'wdmycloudex2_ups_mode:their their zombies forward Jaded zombies quaintly',
            'wdmycloudex2_ups_num:4',
            'wdmycloudex2_ups_product:driving driving driving acted kept forward driving Jaded',
            'wdmycloudex2_ups_status:driving acted oxen forward',
        ],
        [
            'wdmycloudex2_ups_manufacturer:forward',
            'wdmycloudex2_ups_mode:Jaded kept kept kept their',
            'wdmycloudex2_ups_num:23',
            'wdmycloudex2_ups_product:zombies acted forward',
            'wdmycloudex2_ups_status:zombies oxen kept oxen kept forward',
        ],
        [
            'wdmycloudex2_ups_manufacturer:quaintly quaintly',
            'wdmycloudex2_ups_mode:Jaded oxen',
            'wdmycloudex2_ups_num:15',
            'wdmycloudex2_ups_product:their but quaintly kept but acted',
            'wdmycloudex2_ups_status:zombies Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.wdmycloudex2UPS', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'western-digital-mycloud-ex2-ultra Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'western-digital-mycloud-ex2-ultra.device.name',
        'profile': 'western-digital-mycloud-ex2-ultra',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5127.1.1.1.8',
        'vendor': 'western-digital',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
