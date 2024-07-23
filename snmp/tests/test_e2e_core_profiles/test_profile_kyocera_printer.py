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


def test_e2e_profile_kyocera_printer(dd_agent_check):
    profile = 'kyocera-printer'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:kyocera-printer',
        'snmp_host:kyocera-printer.device.name',
        'device_hostname:kyocera-printer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + ['kcprt_general_model_name:kept but oxen Jaded', 'kcprt_serial_number:kept kept']

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['kcprt_alert_state_display:zombies acted zombies kept oxen'],
        ['kcprt_alert_state_display:zombies kept but acted acted'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.kcprtAlertStateCode', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'kcprt_memory_device_location:pc_card-a',
            'kcprt_memory_device_status:ready_read_write',
            'kcprt_memory_device_type:strage',
        ],
        [
            'kcprt_memory_device_location:resident_font',
            'kcprt_memory_device_status:not_accessible',
            'kcprt_memory_device_type:rom',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.kcprtMemoryDeviceTotalSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.kcprtMemoryDeviceUsedSize', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'kyocera-printer Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'kyocera-printer.device.name',
        'profile': 'kyocera-printer',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.1347.41',
        'vendor': 'kyocera',
        'device_type': 'printer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
