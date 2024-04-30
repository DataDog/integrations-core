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
    assert_extend_generic_tcp,
    assert_extend_generic_udp,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_apc_pdu(dd_agent_check):
    profile = 'apc-pdu'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:apc-pdu',
        'snmp_host:apc-pdu.device.name',
        'device_hostname:apc-pdu.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'powernet_r_pdu_ident_firmware_rev:kept zombies forward acted zombies but kept forward',
        'powernet_r_pdu_ident_hardware_rev:zombies forward their',
        'powernet_r_pdu_ident_model_number:zombies kept their kept zombies kept Jaded zombies ' 'but',
        'powernet_r_pdu_ident_name:oxen',
        'powernet_r_pdu_ident_serial_number:Jaded kept',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.powernet.rPDUPowerSupplyAlarm', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['powernet_r_pdu_load_status_index:0', 'powernet_r_pdu_load_status_load_state:phase_load_overload'],
        ['powernet_r_pdu_load_status_index:18', 'powernet_r_pdu_load_status_load_state:phase_load_overload'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powernet.rPDULoadStatusLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'powernet_r_pdu_outlet_status_index:14',
            'powernet_r_pdu_outlet_status_outlet_name:forward kept zombies oxen oxen driving their',
            'powernet_r_pdu_outlet_status_outlet_state:outlet_status_off',
        ],
        [
            'powernet_r_pdu_outlet_status_index:9',
            'powernet_r_pdu_outlet_status_outlet_name:forward kept zombies forward kept',
            'powernet_r_pdu_outlet_status_outlet_state:outlet_status_on',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powernet.rPDUOutletStatusLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'powernet_r_pdu_status_bank_index:13',
            'powernet_r_pdu_status_bank_number:8',
            'powernet_r_pdu_status_bank_state:bank_load_near_overload',
        ],
        [
            'powernet_r_pdu_status_bank_index:21',
            'powernet_r_pdu_status_bank_number:13',
            'powernet_r_pdu_status_bank_state:bank_load_normal',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powernet.rPDUStatusBank', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'powernet_r_pdu_status_phase_index:20',
            'powernet_r_pdu_status_phase_number:20',
            'powernet_r_pdu_status_phase_state:phase_load_overload',
        ],
        [
            'powernet_r_pdu_status_phase_index:26',
            'powernet_r_pdu_status_phase_number:28',
            'powernet_r_pdu_status_phase_state:phase_load_overload',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powernet.rPDUStatusPhase', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'powernet_r_pdu_status_outlet_index:20',
            'powernet_r_pdu_status_outlet_number:21',
            'powernet_r_pdu_status_outlet_state:outlet_load_normal',
        ],
        [
            'powernet_r_pdu_status_outlet_index:26',
            'powernet_r_pdu_status_outlet_number:28',
            'powernet_r_pdu_status_outlet_state:outlet_load_overload',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powernet.rPDUStatusOutlet', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'powernet_r_pdu2_sensor_temp_humidity_status_humidity_status:above_max',
            'powernet_r_pdu2_sensor_temp_humidity_status_name:their but acted quaintly zombies Jaded zombies',
            'powernet_r_pdu2_sensor_temp_humidity_status_temp_status:above_high',
            'powernet_r_pdu2_sensor_temp_humidity_status_type:not_installed',
        ],
        [
            'powernet_r_pdu2_sensor_temp_humidity_status_humidity_status:below_min',
            'powernet_r_pdu2_sensor_temp_humidity_status_name:but acted quaintly their forward driving Jaded',
            'powernet_r_pdu2_sensor_temp_humidity_status_temp_status:normal',
            'powernet_r_pdu2_sensor_temp_humidity_status_type:temperature_only',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.powernet.rPDU2SensorTempHumidityStatusRelativeHumidity',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.powernet.rPDU2SensorTempHumidityStatusTempC', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.powernet.rPDU2SensorTempHumidityStatusTempF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'apc-pdu Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'apc-pdu.device.name',
        'profile': 'apc-pdu',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.318.1.3.4.5',
        'vendor': 'apc',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
