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
    assert_extend_generic_ucd,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_avocent_acs(dd_agent_check):
    profile = 'avocent-acs'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:avocent-acs',
        'snmp_host:avocent-acs.device.name',
        'device_hostname:avocent-acs.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    assert_extend_generic_ucd(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.avocent.acsActiveSessionsNumberOfSession', metric_type=aggregator.GAUGE, tags=common_tags
    )
    tag_rows = [
        [
            'avocent_acs_serial_port_table_device_name:Jaded Jaded',
            'avocent_acs_serial_port_table_name:kept',
            'avocent_acs_serial_port_table_status:idle',
        ],
        [
            'avocent_acs_serial_port_table_device_name:oxen',
            'avocent_acs_serial_port_table_name:forward driving quaintly',
            'avocent_acs_serial_port_table_status:in_use',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.avocent.acsSerialPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'avocent-acs Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'avocent-acs.device.name',
        'profile': 'avocent-acs',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.10418.26.1.7',
        'vendor': 'avocent',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
