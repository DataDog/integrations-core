# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__generic_ucd(dd_agent_check):
    config = create_e2e_core_test_config('_generic-ucd')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-ucd',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memAvailSwap', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memBuffer', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memCached', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memMinimumSwap', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memShared', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memTotalFree', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memTotalSwap', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuIdle', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawIdle', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawInterrupt', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawKernel', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawNice', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawSystem', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawUser', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuRawWait', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuSystem', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ssCpuUser', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['dsk_device:driving driving but kept oxen oxen', 'dsk_error_flag:no_error', 'dsk_path:oxen acted oxen their'],
        ['dsk_device:kept Jaded', 'dsk_error_flag:no_error', 'dsk_path:quaintly oxen acted oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dskAvail', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dskPercent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dskPercentNode', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dskTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.dskUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['disk_io_device:forward'],
        ['disk_io_device:their zombies'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.diskIOLA1', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskIOLA15', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskIOLA5', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskIONReadX', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskIONWrittenX', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskIOReads', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.diskIOWrites', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    aggregator.assert_all_metrics_covered()

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
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
