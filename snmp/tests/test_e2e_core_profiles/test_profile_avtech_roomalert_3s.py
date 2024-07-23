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


def test_e2e_profile_avtech_roomalert_3s(dd_agent_check):
    profile = 'avtech-roomalert-3s'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:avtech-roomalert-3s',
        'snmp_host:avtech-roomalert-3s.device.name',
        'device_hostname:avtech-roomalert-3s.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_1', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_2', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_3', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_4', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_5', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_6', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.digital_sen1_7', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_eight', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_five', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_four', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_one', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_seven', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_six', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_three', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.roomalert.3s.externalrelay1_element_two', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.roomalert.3s.internal_tempc', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.roomalert.3s.internal_tempf', metric_type=aggregator.GAUGE, tags=common_tags)

    # --- TEST METADATA ---
    device = {
        'description': 'avtech-roomalert-3s Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'avtech-roomalert-3s.device.name',
        'profile': 'avtech-roomalert-3s',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.20916.1.13.999',
        'vendor': 'avtech',
        'device_type': 'sensor',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
