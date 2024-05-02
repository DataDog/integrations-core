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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_nasuni_filer(dd_agent_check):
    profile = 'nasuni-filer'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:nasuni-filer',
        'snmp_host:nasuni-filer.device.name',
        'device_hostname:nasuni-filer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'filer_bios_version:quaintly zombies zombies but',
        'filer_cpu_arch:their zombies',
        'filer_cpu_model:Jaded but their quaintly forward kept their',
        'filer_identifier:but forward acted quaintly zombies',
        'filer_package_format:driving Jaded Jaded oxen zombies Jaded',
        'filer_platform_name:their acted driving forward forward Jaded kept driving',
        'filer_platform_type:quaintly',
        'filer_serial_number:kept quaintly forward',
        'filer_version:forward driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.nasuni.accountLicensedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.accountPercentUsedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.accountUsedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerAmbientTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerCacheFree', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerCacheTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerCacheUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerClientsIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerClientsOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerCloudIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerCloudOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerCoreCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerDiskCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerExhaustTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerInletTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerMergeConflicts', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerMigrationIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerMigrationOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerMobileIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerMobileOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerNumAndroidLicenses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerNumIOSLicenses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerNumPowerSupplies', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerNumRaidArrays', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerNumRaidDisks', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerOpensForRead', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerOpensForWrite', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerPhysCpuCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerPowerSupplyErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerPushesCompleted', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerRaidArrayErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerRaidDiskErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerReadHits', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerReadMisses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalExports', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalFtpdirs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalIscsiClients', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalIscsiTargets', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalMobileLicenses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalPushed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalRead', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalShareClients', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalShareLocks', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalShares', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerTotalUnprotectedData', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerUIIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.filerUIOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nasuni.volumeCount', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'volume_table_description:forward driving their oxen forward their quaintly quaintly forward',
            'volume_table_protocol:their kept but zombies kept oxen kept',
            'volume_table_provider:Jaded',
            'volume_table_status:driving their acted kept but',
            'volume_table_is_active:true',
            'volume_table_is_shared:true',
            'volume_table_is_read_only:true',
            'volume_table_is_pinned:true',
            'volume_table_is_remote:true',
            'volume_table_av_enabled:true',
            'volume_table_remote_access_enabled:true',
        ],
        [
            'volume_table_description:their oxen acted but their but but',
            'volume_table_protocol:forward quaintly but',
            'volume_table_provider:driving quaintly acted Jaded quaintly kept forward Jaded',
            'volume_table_status:driving oxen Jaded',
            'volume_table_is_active:false',
            'volume_table_is_shared:false',
            'volume_table_is_read_only:false',
            'volume_table_is_pinned:false',
            'volume_table_is_remote:false',
            'volume_table_av_enabled:false',
            'volume_table_remote_access_enabled:false',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableAccessibleData', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableLastSnapshotDuration', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableLastSnapshotVersion', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableNumAVViolations', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableNumExports', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableNumFileAlerts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableNumFtpdirs', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableNumShares', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableQuota', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.nasuni.volumeTableUnprotectedData', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'nasuni-filer Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'nasuni-filer.device.name',
        'profile': 'nasuni-filer',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.42040.1.1.0',
        'vendor': 'nasuni',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
