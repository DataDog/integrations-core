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


def test_e2e_profile_dell_emc_data_domain(dd_agent_check):
    config = create_e2e_core_test_config('dell-emc-data-domain')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-emc-data-domain',
        'snmp_host:dell-emc-data-domain.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    # aggregator.assert_metric('snmp.fileSystemVirtualSpace', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hrCachedMemory', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hrMemoryBuffers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['data_domain_power_module_description:kept acted kept acted Jaded', 'data_domain_power_module_status:ok'],
        ['data_domain_power_module_description:oxen acted but Jaded zombies', 'data_domain_power_module_status:faulty'],
        [
            'data_domain_power_module_description:their driving quaintly zombies their forward',
            'data_domain_power_module_status:failed',
        ],
        ['data_domain_power_module_description:their kept zombies but', 'data_domain_power_module_status:absent'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.powerModule', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'data_domain_temp_sensor_description:Jaded their quaintly',
            'data_domain_temp_sensor_status:overheat_critical',
        ],
        ['data_domain_temp_sensor_description:driving', 'data_domain_temp_sensor_status:overheat_critical'],
        ['data_domain_temp_sensor_description:oxen acted but zombies', 'data_domain_temp_sensor_status:failed'],
        [
            'data_domain_temp_sensor_description:their acted acted driving but their',
            'data_domain_temp_sensor_status:overheat_critical',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.tempSensorCurrentValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'data_domain_fan_description:Jaded kept quaintly driving oxen driving oxen',
            'data_domain_fan_level:unknown',
            'data_domain_fan_status:notfound',
        ],
        [
            'data_domain_fan_description:but forward kept acted their zombies acted',
            'data_domain_fan_level:low',
            'data_domain_fan_status:fail',
        ],
        [
            'data_domain_fan_description:oxen forward but their zombies but but driving',
            'data_domain_fan_level:low',
            'data_domain_fan_status:notfound',
        ],
        [
            'data_domain_fan_description:their zombies kept their driving',
            'data_domain_fan_level:low',
            'data_domain_fan_status:ok',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fanProperties', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'data_domain_file_system_resource_name:driving their oxen forward Jaded forward but kept',
            'data_domain_file_system_resource_tier:their acted Jaded quaintly their acted',
        ],
        [
            'data_domain_file_system_resource_name:quaintly but oxen Jaded acted oxen kept',
            'data_domain_file_system_resource_tier:quaintly but kept driving Jaded',
        ],
        [
            'data_domain_file_system_resource_name:zombies kept driving quaintly forward',
            'data_domain_file_system_resource_tier:forward forward acted their but kept kept but',
        ],
        [
            'data_domain_file_system_resource_name:zombies quaintly',
            'data_domain_file_system_resource_tier:zombies Jaded Jaded acted forward forward Jaded kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fileSystemPercentUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        # These are not found

        # aggregator.assert_metric('snmp.fileSystemSpaceAvail', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        # aggregator.assert_metric(
        #     'snmp.fileSystemSpaceCleanable', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        # )
        # aggregator.assert_metric('snmp.fileSystemSpaceSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        # aggregator.assert_metric('snmp.fileSystemSpaceUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # These are not found either, as well as the tag_rows are empty for some reason,
    # though snmprec seems to be complete

    # tag_rows = [
    #     ['TODO'],
    # ]
    # for tag_row in tag_rows:
    #     aggregator.assert_metric(
    #         'snmp.fileSystemCompressionEndTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemCompressionStartTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemGlobalCompressionFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemLocalCompressionFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemPostCompressionSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemPreCompressionSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemReductionPercent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )
    #     aggregator.assert_metric(
    #         'snmp.fileSystemTotalCompressionFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
    #     )

    tag_rows = [
        ['data_domain_system_stats_index:13'],
        ['data_domain_system_stats_index:31'],
        ['data_domain_system_stats_index:9'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cifsOpsPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cpuMaxPercentageBusy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskBusyPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.diskReadKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.diskWriteKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.nfsIdlePercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nfsOpsPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nfsProcPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nfsReceivePercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nfsSendPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.nvramReadKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nvramWriteKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.relOutKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.replInKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'data_domain_disk_capacity:Jaded forward',
            'data_domain_disk_firmware_version:driving kept',
            'data_domain_disk_model:zombies quaintly acted their quaintly zombies',
            'data_domain_disk_pack:pack4',
            'data_domain_disk_prop_enclosure_id:10',
            'data_domain_disk_prop_index:12',
            'data_domain_disk_prop_state:absent',
            'data_domain_disk_serial_number:oxen zombies zombies quaintly driving',
        ],
        [
            'data_domain_disk_capacity:but their but their',
            'data_domain_disk_firmware_version:oxen forward forward driving quaintly Jaded kept Jaded',
            'data_domain_disk_model:but forward forward oxen kept acted acted',
            'data_domain_disk_pack:notapplicable',
            'data_domain_disk_prop_enclosure_id:28',
            'data_domain_disk_prop_index:27',
            'data_domain_disk_prop_state:unknown',
            'data_domain_disk_serial_number:quaintly quaintly',
        ],
        [
            'data_domain_disk_capacity:oxen zombies driving',
            'data_domain_disk_firmware_version:kept their oxen but oxen Jaded driving acted',
            'data_domain_disk_model:zombies quaintly oxen oxen their kept',
            'data_domain_disk_pack:pack2',
            'data_domain_disk_prop_enclosure_id:12',
            'data_domain_disk_prop_index:6',
            'data_domain_disk_prop_state:failed',
            'data_domain_disk_serial_number:Jaded their but acted driving oxen acted',
        ],
        [
            'data_domain_disk_capacity:their',
            'data_domain_disk_firmware_version:Jaded their quaintly',
            'data_domain_disk_model:Jaded their Jaded kept',
            'data_domain_disk_pack:notapplicable',
            'data_domain_disk_prop_enclosure_id:29',
            'data_domain_disk_prop_index:15',
            'data_domain_disk_prop_state:unknown',
            'data_domain_disk_serial_number:zombies oxen quaintly forward driving forward kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.diskProperties', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['data_domain_disk_perf_state:failed'],
        ['data_domain_disk_perf_state:available'],
    ]

    # diskTotalKBytes is not found with tag_rows, but when without tag_rows, diskSectorsWritten is not found, etc.
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.diskBusy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskSectorsWritten', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskSectorsRead', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskTotalKBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'dell-emc-data-domain Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'dell-emc-data-domain.device.name',
        'profile': 'dell-emc-data-domain',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.19746.3.1.37',
        'vendor': 'dell',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
