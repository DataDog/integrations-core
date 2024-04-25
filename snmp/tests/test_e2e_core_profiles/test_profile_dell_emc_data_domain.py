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


def test_e2e_profile_dell_emc_data_domain(dd_agent_check):
    profile = 'dell-emc-data-domain'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-emc-data-domain',
        'snmp_host:dell-emc-data-domain.device.name',
        'device_hostname:dell-emc-data-domain.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.hrCachedMemory', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hrMemoryBuffers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.datadomain.fileSystemVirtualSpace', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['datadomain_power_module_description:kept acted kept acted Jaded', 'datadomain_power_module_status:ok'],
        ['datadomain_power_module_description:oxen acted but Jaded zombies', 'datadomain_power_module_status:faulty'],
        [
            'datadomain_power_module_description:their driving quaintly zombies their forward',
            'datadomain_power_module_status:failed',
        ],
        ['datadomain_power_module_description:their kept zombies but', 'datadomain_power_module_status:absent'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.datadomain.powerModule', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['datadomain_temp_sensor_description:Jaded their quaintly', 'datadomain_temp_sensor_status:overheat_critical'],
        ['datadomain_temp_sensor_description:driving', 'datadomain_temp_sensor_status:overheat_critical'],
        ['datadomain_temp_sensor_description:oxen acted but zombies', 'datadomain_temp_sensor_status:failed'],
        [
            'datadomain_temp_sensor_description:their acted acted driving but their',
            'datadomain_temp_sensor_status:overheat_critical',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.datadomain.tempSensorCurrentValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'datadomain_fan_description:Jaded kept quaintly driving oxen driving oxen',
            'datadomain_fan_level:unknown',
            'datadomain_fan_status:notfound',
        ],
        [
            'datadomain_fan_description:but forward kept acted their zombies acted',
            'datadomain_fan_level:low',
            'datadomain_fan_status:fail',
        ],
        [
            'datadomain_fan_description:oxen forward but their zombies but but driving',
            'datadomain_fan_level:low',
            'datadomain_fan_status:notfound',
        ],
        [
            'datadomain_fan_description:their zombies kept their driving',
            'datadomain_fan_level:low',
            'datadomain_fan_status:ok',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.datadomain.fanProperties', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'datadomain_file_system_resource_name:driving their oxen forward Jaded forward but kept',
            'datadomain_file_system_resource_tier:their acted Jaded quaintly their acted',
        ],
        [
            'datadomain_file_system_resource_name:quaintly but oxen Jaded acted oxen kept',
            'datadomain_file_system_resource_tier:quaintly but kept driving Jaded',
        ],
        [
            'datadomain_file_system_resource_name:zombies kept driving quaintly forward',
            'datadomain_file_system_resource_tier:forward forward acted their but kept kept but',
        ],
        [
            'datadomain_file_system_resource_name:zombies quaintly',
            'datadomain_file_system_resource_tier:zombies Jaded Jaded acted forward forward Jaded kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemPercentUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemSpaceAvail', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemSpaceCleanable', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemSpaceSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemSpaceUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['data_domain_file_system_compression_index:14'],
        ['data_domain_file_system_compression_index:25'],
        ['data_domain_file_system_compression_index:29'],
        ['data_domain_file_system_compression_index:8'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemCompressionEndTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemCompressionStartTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemGlobalCompressionFactor',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemLocalCompressionFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemPostCompressionSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemPreCompressionSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemReductionPercent1', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.fileSystemTotalCompressionFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['datadomain_system_stats_index:13'],
        ['datadomain_system_stats_index:31'],
        ['datadomain_system_stats_index:9'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.datadomain.cifsOpsPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.cpuMaxPercentageBusy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.diskBusyPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.diskReadKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.diskWriteKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nfsIdlePercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nfsOpsPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nfsProcPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nfsReceivePercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nfsSendPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nvramReadKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.nvramWriteKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.replOutKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.replInKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'datadomain_disk_capacity:Jaded forward',
            'datadomain_disk_firmware_version:driving kept',
            'datadomain_disk_model:zombies quaintly acted their quaintly zombies',
            'datadomain_disk_pack:pack4',
            'datadomain_disk_prop_enclosure_id:10',
            'datadomain_disk_prop_index:12',
            'datadomain_disk_prop_state:absent',
            'datadomain_disk_serial_number:oxen zombies zombies quaintly driving',
        ],
        [
            'datadomain_disk_capacity:but their but their',
            'datadomain_disk_firmware_version:oxen forward forward driving quaintly Jaded kept Jaded',
            'datadomain_disk_model:but forward forward oxen kept acted acted',
            'datadomain_disk_pack:notapplicable',
            'datadomain_disk_prop_enclosure_id:28',
            'datadomain_disk_prop_index:27',
            'datadomain_disk_prop_state:unknown',
            'datadomain_disk_serial_number:quaintly quaintly',
        ],
        [
            'datadomain_disk_capacity:oxen zombies driving',
            'datadomain_disk_firmware_version:kept their oxen but oxen Jaded driving acted',
            'datadomain_disk_model:zombies quaintly oxen oxen their kept',
            'datadomain_disk_pack:pack2',
            'datadomain_disk_prop_enclosure_id:12',
            'datadomain_disk_prop_index:6',
            'datadomain_disk_prop_state:failed',
            'datadomain_disk_serial_number:Jaded their but acted driving oxen acted',
        ],
        [
            'datadomain_disk_capacity:their',
            'datadomain_disk_firmware_version:Jaded their quaintly',
            'datadomain_disk_model:Jaded their Jaded kept',
            'datadomain_disk_pack:notapplicable',
            'datadomain_disk_prop_enclosure_id:29',
            'datadomain_disk_prop_index:15',
            'datadomain_disk_prop_state:unknown',
            'datadomain_disk_serial_number:zombies oxen quaintly forward driving forward kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.datadomain.diskProperties', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['datadomain_disk_perf_index:10', 'datadomain_disk_perf_state:failed'],
        ['datadomain_disk_perf_index:29', 'datadomain_disk_perf_state:available'],
        ['datadomain_disk_perf_index:29', 'datadomain_disk_perf_state:failed'],
        ['datadomain_disk_perf_index:31', 'datadomain_disk_perf_state:available'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.datadomain.diskBusy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.datadomain.diskSectorsRead', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.diskSectorsWritten', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.datadomain.diskTotalKBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

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
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
