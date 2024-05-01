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


def test_e2e_profile_synology_disk_station(dd_agent_check):
    profile = 'synology-disk-station'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:synology-disk-station',
        'snmp_host:synology-disk-station.device.name',
        'device_hostname:synology-disk-station.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'synology_model_name:quaintly quaintly their Jaded quaintly acted',
        'synology_serial_number:kept',
        'synology_version:forward kept Jaded quaintly',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hrCachedMemory', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hrMemoryBuffers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.synology.gpuMemoryUtilization', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.synology.gpuUtilization', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.synology.system.temperature', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'synology_disk_id:Jaded Jaded',
            'synology_disk_model:their forward quaintly Jaded Jaded',
            'synology_disk_status:normal',
            'synology_disk_type:kept',
        ],
        [
            'synology_disk_id:kept acted driving acted but forward oxen quaintly driving',
            'synology_disk_model:oxen',
            'synology_disk_status:crashed',
            'synology_disk_type:driving quaintly forward zombies but quaintly',
        ],
        [
            'synology_disk_id:kept their zombies forward',
            'synology_disk_model:forward Jaded acted driving quaintly acted Jaded zombies',
            'synology_disk_status:crashed',
            'synology_disk_type:Jaded their forward driving quaintly driving zombies',
        ],
        [
            'synology_disk_id:oxen but driving oxen quaintly their zombies forward',
            'synology_disk_model:their oxen acted quaintly driving quaintly',
            'synology_disk_status:crashed',
            'synology_disk_type:forward their their oxen kept',
        ],
        [
            'synology_disk_id:oxen oxen quaintly kept',
            'synology_disk_model:but quaintly',
            'synology_disk_status:crashed',
            'synology_disk_type:kept their their zombies kept oxen zombies kept but',
        ],
        [
            'synology_disk_id:quaintly forward driving Jaded kept quaintly',
            'synology_disk_model:forward but driving Jaded but oxen',
            'synology_disk_status:crashed',
            'synology_disk_type:but oxen zombies quaintly zombies kept Jaded acted',
        ],
        [
            'synology_disk_id:quaintly oxen their quaintly Jaded',
            'synology_disk_model:driving forward Jaded zombies Jaded zombies their kept oxen',
            'synology_disk_status:crashed',
            'synology_disk_type:oxen acted driving zombies Jaded',
        ],
        [
            'synology_disk_id:their',
            'synology_disk_model:kept Jaded oxen acted zombies oxen but their quaintly',
            'synology_disk_status:normal',
            'synology_disk_type:forward oxen quaintly but forward',
        ],
        [
            'synology_disk_id:their quaintly',
            'synology_disk_model:Jaded their Jaded',
            'synology_disk_status:crashed',
            'synology_disk_type:oxen forward kept quaintly Jaded',
        ],
        [
            'synology_disk_id:zombies',
            'synology_disk_model:acted kept',
            'synology_disk_status:normal',
            'synology_disk_type:their',
        ],
        [
            'synology_disk_id:zombies oxen kept Jaded Jaded acted but but acted',
            'synology_disk_model:driving Jaded oxen their Jaded zombies their driving but',
            'synology_disk_status:initialized',
            'synology_disk_type:zombies quaintly acted forward zombies zombies but quaintly quaintly',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.synology.diskTemperature', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['synology_raid_name:acted Jaded but zombies quaintly kept', 'synology_raid_status:migrating'],
        [
            'synology_raid_name:forward driving driving zombies Jaded quaintly Jaded forward forward',
            'synology_raid_status:deleting',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.synology.raidFreeSize', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.synology.raidTotalSize', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'synology_disk_smart_attr_id:1',
            'synology_disk_smart_attr_name:Jaded acted zombies zombies driving kept zombies driving Jaded',
            'synology_disk_smart_attr_status:forward kept their oxen but',
            'synology_disk_smart_info_dev_name:forward driving kept driving forward Jaded',
        ],
        [
            'synology_disk_smart_attr_id:10',
            'synology_disk_smart_attr_name:but kept oxen quaintly kept quaintly',
            'synology_disk_smart_attr_status:Jaded quaintly Jaded forward quaintly forward zombies',
            'synology_disk_smart_info_dev_name:forward acted acted their forward kept but driving acted',
        ],
        [
            'synology_disk_smart_attr_id:2',
            'synology_disk_smart_attr_name:Jaded acted but kept driving forward but but',
            'synology_disk_smart_attr_status:oxen oxen oxen their acted Jaded zombies oxen Jaded',
            'synology_disk_smart_info_dev_name:acted',
        ],
        [
            'synology_disk_smart_attr_id:24',
            'synology_disk_smart_attr_name:oxen kept acted Jaded zombies',
            'synology_disk_smart_attr_status:quaintly driving driving forward but forward acted driving driving',
            'synology_disk_smart_info_dev_name:Jaded oxen acted driving their forward acted',
        ],
        [
            'synology_disk_smart_attr_id:26',
            'synology_disk_smart_attr_name:zombies zombies kept quaintly their driving',
            'synology_disk_smart_attr_status:driving but their acted quaintly acted',
            'synology_disk_smart_info_dev_name:their',
        ],
        [
            'synology_disk_smart_attr_id:5',
            'synology_disk_smart_attr_name:driving forward zombies acted zombies driving',
            'synology_disk_smart_attr_status:Jaded quaintly kept but',
            'synology_disk_smart_info_dev_name:Jaded their driving zombies driving driving forward Jaded but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.synology.diskSMARTAttrCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.synology.diskSMARTAttrThreshold', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['synology_service_name:Jaded'],
        ['synology_service_name:Jaded acted zombies forward'],
        ['synology_service_name:Jaded but their forward kept forward'],
        ['synology_service_name:Jaded their acted acted kept zombies'],
        ['synology_service_name:acted'],
        ['synology_service_name:but Jaded kept zombies but forward oxen'],
        ['synology_service_name:but driving driving acted driving forward driving'],
        ['synology_service_name:but forward quaintly zombies Jaded driving driving driving'],
        ['synology_service_name:forward zombies acted zombies'],
        ['synology_service_name:quaintly'],
        ['synology_service_name:quaintly acted quaintly zombies forward zombies kept'],
        ['synology_service_name:their Jaded Jaded zombies their driving but quaintly'],
        ['synology_service_name:their kept Jaded quaintly Jaded Jaded Jaded oxen'],
        ['synology_service_name:their zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.synology.serviceUsers', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['synology_storage_io_device:Jaded'],
        ['synology_storage_io_device:acted'],
        ['synology_storage_io_device:quaintly their driving but kept'],
        ['synology_storage_io_device:their forward driving oxen Jaded but driving forward but'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.synology.storageIOLA', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.synology.storageIONReadX', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.synology.storageIONWrittenX', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.synology.storageIOReads', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.synology.storageIOWrites', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    tag_rows = [
        ['synology_space_io_device:Jaded'],
        ['synology_space_io_device:Jaded Jaded kept forward oxen zombies'],
        ['synology_space_io_device:Jaded driving'],
        ['synology_space_io_device:but their oxen zombies quaintly driving'],
        ['synology_space_io_device:driving'],
        ['synology_space_io_device:driving Jaded Jaded but acted driving'],
        ['synology_space_io_device:driving Jaded but quaintly quaintly'],
        ['synology_space_io_device:oxen acted zombies their oxen quaintly kept acted'],
        ['synology_space_io_device:quaintly but'],
        ['synology_space_io_device:quaintly kept Jaded but oxen but kept quaintly zombies'],
        ['synology_space_io_device:quaintly kept quaintly zombies'],
        ['synology_space_io_device:quaintly oxen their'],
        ['synology_space_io_device:their quaintly forward zombies acted zombies their acted acted'],
        ['synology_space_io_device:zombies acted oxen'],
        ['synology_space_io_device:zombies acted oxen but acted zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.synology.spaceIOLA', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.synology.spaceIONReadX', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.synology.spaceIONWrittenX', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.synology.spaceIOReads', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.synology.spaceIOWrites', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'synology-disk-station Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'synology-disk-station.device.name',
        'profile': 'synology-disk-station',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.6574.1',
        'vendor': 'synology',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
