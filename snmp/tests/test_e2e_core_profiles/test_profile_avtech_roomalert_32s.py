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


def test_e2e_profile_avtech_roomalert_32s(dd_agent_check):
    profile = 'avtech-roomalert-32s'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:avtech-roomalert-32s',
        'snmp_host:avtech-roomalert-32s.device.name',
        'device_hostname:avtech-roomalert-32s.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen1_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen2_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen3_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen4_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen5_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen6_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen7_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.digital_sen8_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_analog1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_analog2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_dew_point_c', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_dew_point_f', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_heat_index', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_heat_indexC', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_humidity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_relay1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_relay2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_tempc', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.32s.internal_tempf', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'avtech-roomalert-32s Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'avtech-roomalert-32s.device.name',
        'profile': 'avtech-roomalert-32s',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.20916.1.11',
        'vendor': 'avtech',
        'device_type': 'sensor',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
