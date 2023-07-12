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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_nasuni_filer(dd_agent_check):
    config = create_e2e_core_test_config('nasuni-filer')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:nasuni-filer',
        'snmp_host:nasuni-filer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + [
        'filer_bios_version:quaintly zombies zombies but',
        'filer_core_count:20',
        'filer_cpu_arch:their zombies',
        'filer_cpu_model:Jaded but their quaintly forward kept their',
        'filer_disk_count:1',
        'filer_identifier:but forward acted quaintly zombies',
        'filer_package_format:driving Jaded Jaded oxen zombies Jaded',
        'filer_phys_cpu_count:20',
        'filer_platform_name:their acted driving forward forward Jaded kept driving',
        'filer_platform_type:quaintly',
        'filer_serial_number:kept quaintly forward',
        'filer_support_service_connected:24',
        'filer_support_service_enabled:26',
        'filer_support_service_running:6',
        'filer_version:forward driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.accountLicensedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.accountPercentUsedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.accountUsedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerAmbientTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerCacheFree', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerCacheTotal', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerCacheUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerClientsIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerClientsOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerCloudIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerCloudOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerExhaustTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerInletTemp', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerMergeConflicts', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerMigrationIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerMigrationOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerMobileIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerMobileOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerNumAndroidLicenses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerNumIOSLicenses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerNumPowerSupplies', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerNumRaidArrays', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerNumRaidDisks', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerOpensForRead', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerOpensForWrite', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerPowerSupplyErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerPushesCompleted', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerRaidArrayErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerRaidDiskErrors', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerReadHits', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerReadMisses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalExports', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalFtpdirs', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalIscsiClients', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalIscsiTargets', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalMobileLicenses', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalPushed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalRead', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalShareClients', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalShareLocks', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalShares', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerTotalUnprotectedData', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerUIIn', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.filerUIOut', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.volumeCount', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'volume_table_description:forward driving their oxen forward their quaintly quaintly forward',
            'volume_table_protocol:their kept but zombies kept oxen kept',
            'volume_table_provider:Jaded',
            'volume_table_status:driving their acted kept but',
        ],
        [
            'volume_table_description:their oxen acted but their but but',
            'volume_table_protocol:forward quaintly but',
            'volume_table_provider:driving quaintly acted Jaded quaintly kept forward Jaded',
            'volume_table_status:driving oxen Jaded',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.volumeTableAccessibleData', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.volumeTableLastSnapshotDuration', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.volumeTableLastSnapshotVersion', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.volumeTableNumAVViolations', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.volumeTableNumExports', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.volumeTableNumFileAlerts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.volumeTableNumFtpdirs', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.volumeTableNumShares', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.volumeTableQuota', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.volumeTableUnprotectedData', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
