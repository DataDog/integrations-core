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


def test_e2e_profile_vertiv_watchdog(dd_agent_check):
    profile = 'vertiv-watchdog'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:vertiv-watchdog',
        'snmp_host:vertiv-watchdog.device.name',
        'device_hostname:vertiv-watchdog.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'vertiv_product_friendly_name:forward zombies zombies',
        'vertiv_product_mac_address:acted but forward',
        'vertiv_product_title:zombies forward',
        'vertiv_product_version:acted oxen kept but driving but quaintly driving',
    ]

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'vertiv_internal_avail:partially_unavailable',
            'vertiv_internal_serial:acted but Jaded driving acted forward their forward Jaded',
        ],
        [
            'vertiv_internal_avail:unavailable',
            'vertiv_internal_serial:oxen quaintly but oxen Jaded acted forward oxen oxen',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.vertiv.internalDewPoint', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.vertiv.internalHumidity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.vertiv.internalTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'vertiv_temp_sensor_avail:available',
            'vertiv_temp_sensor_label:but',
            'vertiv_temp_sensor_serial:kept quaintly kept oxen quaintly but',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.vertiv.tempSensorTemp', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'vertiv-watchdog Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'vertiv-watchdog.device.name',
        'profile': 'vertiv-watchdog',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.21239.5.1',
        'vendor': 'vertiv',
        'device_type': 'sensor',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
