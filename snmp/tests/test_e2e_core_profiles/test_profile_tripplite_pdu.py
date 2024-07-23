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


def test_e2e_profile_tripplite_pdu(dd_agent_check):
    profile = 'tripplite-pdu'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:tripplite-pdu',
        'snmp_host:tripplite-pdu.device.name',
        'device_hostname:tripplite-pdu.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.tlpAlarmsPresent', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'tlp_device_location:Jaded forward driving zombies kept zombies their quaintly forward',
            'tlp_device_manufacturer:kept oxen acted driving driving',
            'tlp_device_model:kept',
            'tlp_device_name:quaintly Jaded driving forward acted but oxen',
            'tlp_device_region:quaintly Jaded their driving driving Jaded but zombies Jaded',
            'tlp_device_status:info',
        ],
        [
            'tlp_device_location:oxen zombies oxen oxen kept driving driving oxen oxen',
            'tlp_device_manufacturer:forward oxen but',
            'tlp_device_model:kept acted Jaded forward their but',
            'tlp_device_name:but kept driving forward kept',
            'tlp_device_region:their but acted',
            'tlp_device_status:status',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlpDevice', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['tlp_device_ident_date_installed:kept oxen', 'tlp_device_ident_serial_num:Jaded zombies forward Jaded'],
        [
            'tlp_device_ident_date_installed:zombies acted acted',
            'tlp_device_ident_serial_num:zombies driving oxen acted',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlpDeviceIdent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'tlp_device_index:25401',
            'tlp_pdu_device_main_load_state:unknown',
            'tlp_pdu_device_output_current_precision:hundredths',
        ],
        [
            'tlp_device_index:26178',
            'tlp_pdu_device_main_load_state:on',
            'tlp_pdu_device_output_current_precision:hundredths',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.tlpPduDeviceOutputPowerTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.tlpPduDevicePhaseImbalance', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.tlpPduDeviceTemperatureC', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.tlpPduDeviceTemperatureF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'tlp_device_index:29077',
            'tlp_pdu_output_index:28750',
            'tlp_pdu_output_phase:phase1',
            'tlp_pdu_output_phase_type:phase_to_phase',
        ],
        [
            'tlp_device_index:63592',
            'tlp_pdu_output_index:45556',
            'tlp_pdu_output_phase:phase3',
            'tlp_pdu_output_phase_type:phase_to_phase',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlpPduOutputCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlpPduOutputFrequency', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlpPduOutputSource', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlpPduOutputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['tlp_pdu_outlet_description:forward', 'tlp_pdu_outlet_name:acted Jaded but Jaded but acted forward'],
        ['tlp_pdu_outlet_description:their Jaded their acted forward forward', 'tlp_pdu_outlet_name:but zombies Jaded'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlpPduOutletCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlpPduOutletPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlpPduOutletState', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tlpPduOutletVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['tlp_device_index:29320', 'tlp_pdu_breaker_index:60736', 'tlp_pdu_breaker_status:closed'],
        ['tlp_device_index:8829', 'tlp_pdu_breaker_index:52595', 'tlp_pdu_breaker_status:closed'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlpPduBreaker', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'tlp_alarm_acknowledged:acknowledged',
            'tlp_alarm_descr:1.3.6.1.3.143.120.207',
            'tlp_alarm_detail:quaintly but oxen Jaded oxen acted quaintly acted',
            'tlp_alarm_id:26514',
            'tlp_alarm_state:inactive',
            'tlp_alarm_time:384377879',
        ],
        [
            'tlp_alarm_acknowledged:not_acknowledged',
            'tlp_alarm_descr:1.3.6.1.3.191',
            'tlp_alarm_detail:forward zombies but Jaded acted oxen zombies zombies',
            'tlp_alarm_id:17623',
            'tlp_alarm_state:inactive',
            'tlp_alarm_time:265254086',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tlpAlarm', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'tripplite-pdu Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'tripplite-pdu.device.name',
        'profile': 'tripplite-pdu',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.850.1.1.1',
        'vendor': 'tripplite',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
