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

    aggregator.assert_metric('snmp.hrCachedMemory', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.hrMemoryBuffers', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.used', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'dell_data_domain_power_module_description:kept acted kept acted Jaded',
            'dell_data_domain_power_module_status:ok',
        ],
        [
            'dell_data_domain_power_module_description:oxen acted but Jaded zombies',
            'dell_data_domain_power_module_status:faulty',
        ],
        [
            'dell_data_domain_power_module_description:their driving quaintly zombies their forward',
            'dell_data_domain_power_module_status:failed',
        ],
        [
            'dell_data_domain_power_module_description:their kept zombies but',
            'dell_data_domain_power_module_status:absent',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.data_domain.powerModule', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'dell_data_domain_temp_sensor_description:Jaded their quaintly',
            'dell_data_domain_temp_sensor_status:overheat_critical',
        ],
        ['dell_data_domain_temp_sensor_description:driving', 'dell_data_domain_temp_sensor_status:overheat_critical'],
        [
            'dell_data_domain_temp_sensor_description:oxen acted but zombies',
            'dell_data_domain_temp_sensor_status:failed',
        ],
        [
            'dell_data_domain_temp_sensor_description:their acted acted driving but their',
            'dell_data_domain_temp_sensor_status:overheat_critical',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.data_domain.tempSensorCurrentValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'dell_data_domain_fan_description:Jaded kept quaintly driving oxen driving oxen',
            'dell_data_domain_fan_level:unknown',
            'dell_data_domain_fan_status:notfound',
        ],
        [
            'dell_data_domain_fan_description:but forward kept acted their zombies acted',
            'dell_data_domain_fan_level:low',
            'dell_data_domain_fan_status:fail',
        ],
        [
            'dell_data_domain_fan_description:oxen forward but their zombies but but driving',
            'dell_data_domain_fan_level:low',
            'dell_data_domain_fan_status:notfound',
        ],
        [
            'dell_data_domain_fan_description:their zombies kept their driving',
            'dell_data_domain_fan_level:low',
            'dell_data_domain_fan_status:ok',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.data_domain.fanProperties', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'dell_data_domain_file_system_resource_name:driving their oxen forward Jaded forward but kept',
            'dell_data_domain_file_system_resource_tier:their acted Jaded quaintly their acted',
        ],
        [
            'dell_data_domain_file_system_resource_name:quaintly but oxen Jaded acted oxen kept',
            'dell_data_domain_file_system_resource_tier:quaintly but kept driving Jaded',
        ],
        [
            'dell_data_domain_file_system_resource_name:zombies kept driving quaintly forward',
            'dell_data_domain_file_system_resource_tier:forward forward acted their but kept kept but',
        ],
        [
            'dell_data_domain_file_system_resource_name:zombies quaintly',
            'dell_data_domain_file_system_resource_tier:zombies Jaded Jaded acted forward forward Jaded kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.data_domain.fileSystemPercentUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['dell_data_domain_system_stats_index:13'],
        ['dell_data_domain_system_stats_index:31'],
        ['dell_data_domain_system_stats_index:9'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.dell.data_domain.cifsOpsPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.cpuMaxPercentageBusy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskBusyPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskReadKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskWriteKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nfsIdlePercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nfsOpsPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nfsProcPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nfsReceivePercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nfsSendPercentage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nvramReadKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.nvramWriteKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.relOutKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.replInKBytesPerSecond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'dell_data_domain_disk_capacity:Jaded forward',
            'dell_data_domain_disk_firmware_version:driving kept',
            'dell_data_domain_disk_model:zombies quaintly acted their quaintly zombies',
            'dell_data_domain_disk_pack:pack4',
            'dell_data_domain_disk_prop_enclosure_id:10',
            'dell_data_domain_disk_prop_index:12',
            'dell_data_domain_disk_prop_state:absent',
            'dell_data_domain_disk_serial_number:oxen zombies zombies quaintly driving',
        ],
        [
            'dell_data_domain_disk_capacity:but their but their',
            'dell_data_domain_disk_firmware_version:oxen forward forward driving quaintly Jaded kept Jaded',
            'dell_data_domain_disk_model:but forward forward oxen kept acted acted',
            'dell_data_domain_disk_pack:notapplicable',
            'dell_data_domain_disk_prop_enclosure_id:28',
            'dell_data_domain_disk_prop_index:27',
            'dell_data_domain_disk_prop_state:unknown',
            'dell_data_domain_disk_serial_number:quaintly quaintly',
        ],
        [
            'dell_data_domain_disk_capacity:oxen zombies driving',
            'dell_data_domain_disk_firmware_version:kept their oxen but oxen Jaded driving acted',
            'dell_data_domain_disk_model:zombies quaintly oxen oxen their kept',
            'dell_data_domain_disk_pack:pack2',
            'dell_data_domain_disk_prop_enclosure_id:12',
            'dell_data_domain_disk_prop_index:6',
            'dell_data_domain_disk_prop_state:failed',
            'dell_data_domain_disk_serial_number:Jaded their but acted driving oxen acted',
        ],
        [
            'dell_data_domain_disk_capacity:their',
            'dell_data_domain_disk_firmware_version:Jaded their quaintly',
            'dell_data_domain_disk_model:Jaded their Jaded kept',
            'dell_data_domain_disk_pack:notapplicable',
            'dell_data_domain_disk_prop_enclosure_id:29',
            'dell_data_domain_disk_prop_index:15',
            'dell_data_domain_disk_prop_state:unknown',
            'dell_data_domain_disk_serial_number:zombies oxen quaintly forward driving forward kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskProperties', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['dell_data_domain_disk_perf_index:10', 'dell_data_domain_disk_perf_state:failed'],
        ['dell_data_domain_disk_perf_index:29', 'dell_data_domain_disk_perf_state:available'],
        ['dell_data_domain_disk_perf_index:29', 'dell_data_domain_disk_perf_state:failed'],
        ['dell_data_domain_disk_perf_index:31', 'dell_data_domain_disk_perf_state:available'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskBusy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskSectorsRead', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskSectorsWritten', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.data_domain.diskTotalKBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
