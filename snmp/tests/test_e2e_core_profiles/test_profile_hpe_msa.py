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
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_hpe_msa(dd_agent_check):
    profile = 'hpe-msa'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:hpe-msa',
        'snmp_host:hpe-msa.device.name',
        'device_hostname:hpe-msa.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'hpe_fibrechannel_cpq_si_product_name:forward driving forward but',
        'hpe_fibrechannel_cpq_si_sys_product_id:kept',
        'hpe_fibrechannel_cpq_si_sys_serial_num:kept Jaded driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'hpe_fibrechannel_conn_unit_sensor_characteristic:airflow',
            'hpe_fibrechannel_conn_unit_sensor_name:oxen zombies but driving kept driving',
            'hpe_fibrechannel_conn_unit_sensor_status:ok',
        ],
        [
            'hpe_fibrechannel_conn_unit_sensor_characteristic:other',
            'hpe_fibrechannel_conn_unit_sensor_name:Jaded their',
            'hpe_fibrechannel_conn_unit_sensor_status:ok',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.hpe.fibrechannel.connUnitSensor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'hpe_fibrechannel_conn_unit_port_module_type:gbic_not_installed',
            'hpe_fibrechannel_conn_unit_port_name:oxen oxen oxen kept kept forward',
            'hpe_fibrechannel_conn_unit_port_speed:25',
            'hpe_fibrechannel_conn_unit_port_state:unknown',
            'hpe_fibrechannel_conn_unit_port_status:notparticipating',
            'hpe_fibrechannel_conn_unit_port_transmitter_type:longwave_no_ofc',
            'hpe_fibrechannel_conn_unit_port_type:escon',
            'hpe_fibrechannel_conn_unit_port_wwn:quaintly',
        ],
        [
            'hpe_fibrechannel_conn_unit_port_module_type:small_form_factor',
            'hpe_fibrechannel_conn_unit_port_name:driving forward oxen but but',
            'hpe_fibrechannel_conn_unit_port_speed:14',
            'hpe_fibrechannel_conn_unit_port_state:diagnostics',
            'hpe_fibrechannel_conn_unit_port_status:bypass',
            'hpe_fibrechannel_conn_unit_port_transmitter_type:unused',
            'hpe_fibrechannel_conn_unit_port_type:domain-ctl',
            'hpe_fibrechannel_conn_unit_port_wwn:but kept',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.hpe.fibrechannel.connUnitPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'hpe-msa Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'hpe-msa.device.name',
        'os_name': 'Jaded forward oxen zombies Jaded',
        'os_version': 'quaintly oxen',
        'profile': 'hpe-msa',
        'serial_number': 'kept Jaded driving',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.11.2.51',
        'vendor': 'hp',
        'device_type': 'storage',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
