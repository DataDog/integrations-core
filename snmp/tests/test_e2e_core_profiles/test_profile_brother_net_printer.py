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


def test_e2e_profile_brother_net_printer(dd_agent_check):
    profile = 'brother-net-printer'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:brother-net-printer',
        'snmp_host:brother-net-printer.device.name',
        'device_hostname:brother-net-printer.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + ['br_info_serial_number:acted oxen quaintly Jaded oxen kept']

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.brJamPlace', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.brToner1Low', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.brToner2Low', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.brToner3Low', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.brToner4Low', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['br_error_history_description:but Jaded driving'],
        ['br_error_history_description:kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.brErrorHistory', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'brother-net-printer Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'brother-net-printer.device.name',
        'profile': 'brother-net-printer',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2435.2.3.9.1',
        'vendor': 'brother',
        'device_type': 'printer',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
