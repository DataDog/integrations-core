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


def test_e2e_profile_fireeye(dd_agent_check):
    profile = 'fireeye'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:fireeye',
        'snmp_host:fireeye.device.name',
        'device_hostname:fireeye.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'fe_hardware_model:but but their driving acted forward forward their zombies',
        'fe_serial_number:zombies driving quaintly Jaded their zombies driving but ' 'Jaded',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.feAnalyzedAttachmentCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feAnalyzedEmailCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feAnalyzedUrlCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feDeferredEmailCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.feHoldQueueEmailCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.feInfectedAttachmentCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feInfectedEmailCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feInfectedUrlCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feTotalAttachmentCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feTotalEmailCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feTotalMaliciousObjectCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feTotalObjectAnalyzedCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feTotalUrlCount', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.feeQuarantineUsage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.feCachedMemory', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.feMemoryBuffers', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['hr_processor_frw_id:1.3.6.1.3.68.143.66.213.126.236.187.81'],
        ['hr_processor_frw_id:1.3.6.1.3.68.26.47'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['fe_physical_disk_is_healthy:false', 'fe_physical_disk_name:forward kept'],
        [
            'fe_physical_disk_is_healthy:false',
            'fe_physical_disk_name:oxen kept oxen their kept acted Jaded Jaded Jaded',
        ],
        ['fe_physical_disk_is_healthy:false', 'fe_physical_disk_name:quaintly but their oxen'],
        ['fe_physical_disk_is_healthy:true', 'fe_physical_disk_name:driving acted zombies but driving'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.fePhysicalDisk', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'fireeye Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'fireeye.device.name',
        'profile': 'fireeye',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.25597.1',
        'vendor': 'fireeye',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
