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


def test_e2e_profile_cyberpower_pdu(dd_agent_check):
    profile = 'cyberpower-pdu'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cyberpower-pdu',
        'snmp_host:cyberpower-pdu.device.name',
        'device_hostname:cyberpower-pdu.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'e_pdu_ident_model_number:their oxen forward kept driving',
        'e_pdu_ident_name:zombies oxen their oxen Jaded driving driving kept acted',
        'e_pdu_ident_serial_number:but but zombies quaintly but',
        'envir_ident_location:Jaded quaintly their Jaded kept',
        'envir_ident_name:zombies oxen oxen quaintly acted',
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cyberpower.ePDUStatusInputFrequency', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cyberpower.ePDUStatusInputVoltage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cyberpower.envirHumidity', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cyberpower.envirTemperature', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.cyberpower.envirTemperatureCelsius', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['e_pdu_load_status_index:5', 'e_pdu_load_status_load_state:load_overload'],
        ['e_pdu_load_status_index:7', 'e_pdu_load_status_load_state:load_overload'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDULoadStatusActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDULoadStatusApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDULoadStatusLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDULoadStatusPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDULoadStatusVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['e_pdu_load_bank_config_alarm:near_over_current_alarm', 'e_pdu_load_bank_config_index:1'],
        ['e_pdu_load_bank_config_alarm:over_current_alarm', 'e_pdu_load_bank_config_index:10'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDULoadBankConfig', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'e_pdu_outlet_status_alarm:over_current_alarm',
            'e_pdu_outlet_status_index:11',
            'e_pdu_outlet_status_outlet_name:acted but quaintly their but zombies kept',
            'e_pdu_outlet_status_outlet_state:outlet_status_off',
        ],
        [
            'e_pdu_outlet_status_alarm:over_current_alarm',
            'e_pdu_outlet_status_index:18',
            'e_pdu_outlet_status_outlet_name:kept forward kept',
            'e_pdu_outlet_status_outlet_state:outlet_status_on',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDUOutletStatusActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDUOutletStatusLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['e_pdu_status_bank_index:6', 'e_pdu_status_bank_number:12', 'e_pdu_status_bank_state:bank_load_low'],
        ['e_pdu_status_bank_index:8', 'e_pdu_status_bank_number:9', 'e_pdu_status_bank_state:bank_load_low'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDUStatusBank', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['e_pdu_status_phase_index:10', 'e_pdu_status_phase_number:1', 'e_pdu_status_phase_state:phase_load_low'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDUStatusPhase', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'e_pdu_status_outlet_index:1',
            'e_pdu_status_outlet_number:31',
            'e_pdu_status_outlet_state:outlet_load_overload',
        ],
        [
            'e_pdu_status_outlet_index:16',
            'e_pdu_status_outlet_number:20',
            'e_pdu_status_outlet_state:outlet_load_normal',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDUStatusOutlet', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'e_pdu2_device_status_index:1',
            'e_pdu2_device_status_load_state:over_current_alarm',
            'e_pdu2_device_status_name:quaintly kept Jaded Jaded',
            'e_pdu2_device_status_power_supply1_status:alarm',
            'e_pdu2_device_status_power_supply2_status:normal',
            'e_pdu2_device_status_power_supply_alarm:alarm',
            'e_pdu2_device_status_role_type:standalone',
        ],
        [
            'e_pdu2_device_status_index:2',
            'e_pdu2_device_status_load_state:near_over_current_alarm',
            'e_pdu2_device_status_name:but but but zombies but Jaded zombies',
            'e_pdu2_device_status_power_supply1_status:alarm',
            'e_pdu2_device_status_power_supply2_status:normal',
            'e_pdu2_device_status_power_supply_alarm:alarm',
            'e_pdu2_device_status_role_type:host',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2DeviceStatusApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2DeviceStatusCurrentLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2DeviceStatusCurrentPeakLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2DeviceStatusPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['e_pdu2_phase_status_index:2', 'e_pdu2_phase_status_load_state:near_overload'],
        ['e_pdu2_phase_status_index:9', 'e_pdu2_phase_status_load_state:overload'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2PhaseStatusApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2PhaseStatusLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2PhaseStatusPeakLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2PhaseStatusPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2PhaseStatusPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2PhaseStatusVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['e_pdu2_bank_status_index:10', 'e_pdu2_bank_status_load_state:overload'],
        ['e_pdu2_bank_status_index:8', 'e_pdu2_bank_status_load_state:near_overload'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2BankStatusLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2BankStatusPeakLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'e_pdu2_outlet_switched_status_index:19',
            'e_pdu2_outlet_switched_status_name:their driving Jaded forward driving quaintly forward',
            'e_pdu2_outlet_switched_status_state:outlet_status_off',
        ],
        [
            'e_pdu2_outlet_switched_status_index:29',
            'e_pdu2_outlet_switched_status_name:driving driving oxen driving zombies driving their driving but',
            'e_pdu2_outlet_switched_status_state:outlet_status_off',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.cyberpower.ePDU2OutletSwitchedStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'cyberpower-pdu Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'cyberpower-pdu.device.name',
        'profile': 'cyberpower-pdu',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.3808.1.1.9999',
        'vendor': 'cyberpower',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
