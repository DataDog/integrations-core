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


def test_e2e_profile_hpe_nimble(dd_agent_check):
    profile = 'hpe-nimble'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:hpe-nimble',
        'snmp_host:hpe-nimble.device.name',
        'device_hostname:hpe-nimble.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.nimble.diskSnapBytesUsedHigh', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.diskSnapBytesUsedLow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.diskVolBytesUsedHigh', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.diskVolBytesUsedLow', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioNonseqReadHits', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioReadBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioReadTimeMicrosec', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioReads', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioSeqReadBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioSeqWriteBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioWriteBytes', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioWriteTimeMicrosec', metric_type=aggregator.COUNT, tags=common_tags)
    aggregator.assert_metric('snmp.nimble.ioWrites', metric_type=aggregator.COUNT, tags=common_tags)

    tag_rows = [
        ['nimble_vol_name:acted their their forward but', 'nimble_vol_online:false'],
        ['nimble_vol_name:driving Jaded', 'nimble_vol_online:true'],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.nimble.volIoReads', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volIoWrites', metric_type=aggregator.COUNT, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volReserveHigh', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volReserveLow', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volSizeHigh', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volSizeLow', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volUsageHigh', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.nimble.volUsageLow', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'hpe-nimble Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'hpe-nimble.device.name',
        'profile': 'hpe-nimble',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.37447.3.1',
        'vendor': 'hp',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
