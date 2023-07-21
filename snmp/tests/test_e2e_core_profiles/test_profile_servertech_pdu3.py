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


def test_e2e_profile_servertech_pdu3(dd_agent_check):
    config = create_e2e_core_test_config('servertech-pdu3')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:servertech-pdu3',
        'snmp_host:servertech-pdu3.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.sentry3.systemConfigModifiedCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.systemTotalPower', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.sentry3.towerActivePower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerApparentPower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerEnergy', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerInfeedCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerLineFrequency', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerVACapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.towerVACapacityUsed', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.sentry3.infeedCapacity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedCapacityUsed', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedEnergy', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedLoadValue', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedOutletCount', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedPhaseCurrent', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedPhaseVoltage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedPower', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.infeedVoltage', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.sentry3.outlet', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.sentry3.envMon', metric_type=aggregator.GAUGE, tags=common_tags)

    aggregator.assert_metric('snmp.sentry3.tempHumidSensorHumidValue', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.sentry3.tempHumidSensorTempValue', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'servertech-pdu3 Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'servertech-pdu3.device.name',
        'profile': 'servertech-pdu3',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.1718.3',
        'vendor': 'servertech',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
