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


def test_e2e_profile__generic_ucd(dd_agent_check):
    profile = '_generic-ucd'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-ucd',
        'snmp_host:_generic-ucd.device.name',
        'device_hostname:_generic-ucd.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memAvailSwap', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memBuffer', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memCached', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memMinimumSwap', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memShared', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memTotalFree', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.memTotalSwap', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuIdle', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawIdle', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawInterrupt', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawKernel', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawNice', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawSystem', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawUser', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuRawWait', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuSystem', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ucd.ssCpuUser', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'ucd_dsk_device:driving driving but kept oxen oxen',
            'ucd_dsk_error_flag:no_error',
            'ucd_dsk_path:oxen acted oxen their',
        ],
        ['ucd_dsk_device:kept Jaded', 'ucd_dsk_error_flag:no_error', 'ucd_dsk_path:quaintly oxen acted oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ucd.dskAvail', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.dskPercent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.dskPercentNode', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.dskTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.dskUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['ucd_disk_io_device:forward'],
        ['ucd_disk_io_device:their zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.ucd.diskIOLA1', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.diskIOLA15', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.diskIOLA5', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.diskIONReadX', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.diskIONWrittenX', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.diskIOReads', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.ucd.diskIOWrites', metric_type=aggregator.COUNT, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-ucd Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-ucd.device.name',
        'profile': 'generic-ucd',
        'status': 1,
        'sys_object_id': '1.2.3.1001',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
