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


def test_e2e_profile_infrasensing_sensor_gateway_base_unit(dd_agent_check):
    config = create_e2e_core_test_config('infrasensing-sensor-gateway-base-unit')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:infrasensing-sensor-gateway-base-unit',
        'snmp_host:infrasensing-sensor-gateway-base-unit.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---


    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor1_display_name', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor1_sensor_type', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor1_status', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor1_threshold', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor1_value_integer', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor1_value_string', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor2_display_name', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor2_sensor_type', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor2_status', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor2_threshold', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor2_value_integer', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.infrasensing.servercheck.sensor2_value_string', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'infrasensing-sensor-gateway-base-unit Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'infrasensing-sensor-gateway-base-unit.device.name',
        'profile': 'infrasensing-sensor-gateway-base-unit',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.17095.999',
        'vendor': 'infrasensing',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
