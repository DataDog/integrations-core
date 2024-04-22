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


def test_e2e_profile_zebra_printer(dd_agent_check):
    profile = 'zebra-printer'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:zebra-printer',
        'snmp_host:zebra-printer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'zbr_tracked_alerts_code:ribbon-in',
            'zbr_tracked_alerts_group:cutter',
            'zbr_tracked_alerts_severity:warning',
            'zbr_tracked_alerts_training_level:management',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.zbrTrackedAlerts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'zebra-printer Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'model': 'ZT410',
        'name': 'zebra-printer.device.name',
        'os_version': '6.7',
        'profile': 'zebra-printer',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.10642.1.1',
        'vendor': 'zebra',
        'version': 'P430i V2.00.00',
        'device_type': 'printer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
