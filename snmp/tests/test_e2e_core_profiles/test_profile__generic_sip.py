# (C) Datadog, Inc. 2024-present
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


def test_e2e_profile__generic_sip(dd_agent_check):
    config = create_e2e_core_test_config('_generic-sip')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-sip',
        'snmp_host:_generic-sip.device.name',
        'device_hostname:_generic-sip.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['applIndex:10'],
        ['applIndex:29'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sipCommonCfgServiceOperStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['applIndex:26'],
        ['applIndex:31'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sipCommonSummaryInRequests', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sipCommonSummaryInResponses', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sipCommonSummaryOutRequests', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sipCommonSummaryOutResponses', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sipCommonSummaryTotalTransactions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['applIndex:4', 'sipCommonStatusCodeMethod:15', 'sipCommonStatusCodeValue:102'],
        ['applIndex:9', 'sipCommonStatusCodeMethod:29', 'sipCommonStatusCodeValue:98'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sipCommonStatusCodeIns', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.sipCommonStatusCodeOuts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['applIndex:21'],
        ['applIndex:26'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.sipCommonTransCurrentactions', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': '_generic-sip Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-sip.device.name',
        'profile': 'generic-sip',
        'status': 1,
        'sys_object_id': '1.2.3.1010.123',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
