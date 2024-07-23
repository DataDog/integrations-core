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


def test_e2e_profile_eaton_epdu(dd_agent_check):
    profile = 'eaton-epdu'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:eaton-epdu',
        'snmp_host:eaton-epdu.device.name',
        'device_hostname:eaton-epdu.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['eaton_epdu_input_feed_name:Jaded their forward', 'eaton_epdu_input_frequency_status:out_of_range'],
        ['eaton_epdu_input_feed_name:driving their zombies', 'eaton_epdu_input_frequency_status:out_of_range'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.inputFrequency', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_input_description:kept', 'eaton_epdu_input_voltage_th_status:high_critical'],
        ['eaton_epdu_input_description:oxen', 'eaton_epdu_input_voltage_th_status:high_critical'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.inputVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_input_current_th_status:good', 'eaton_epdu_input_description:kept'],
        ['eaton_epdu_input_current_th_status:high_warning', 'eaton_epdu_input_description:oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.inputCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.eaton.epdu.inputCurrentPercentLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_input_description:kept'],
        ['eaton_epdu_input_description:oxen'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.eaton.epdu.inputVA', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.eaton.epdu.inputWatts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'eaton_epdu_group_breaker_status:breaker_off',
            'eaton_epdu_group_name:forward zombies acted',
            'eaton_epdu_group_type:breaker2pole',
        ],
        [
            'eaton_epdu_group_breaker_status:breaker_on',
            'eaton_epdu_group_name:driving Jaded forward quaintly',
            'eaton_epdu_group_type:breaker1pole',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.eaton.epdu.group', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'eaton_epdu_group_name:driving Jaded forward quaintly',
            'eaton_epdu_group_type:breaker1pole',
            'eaton_epdu_group_voltage_th_status:high_warning',
        ],
        [
            'eaton_epdu_group_name:forward zombies acted',
            'eaton_epdu_group_type:breaker2pole',
            'eaton_epdu_group_voltage_th_status:high_warning',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.groupVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'eaton_epdu_group_current_th_status:high_warning',
            'eaton_epdu_group_name:driving Jaded forward quaintly',
            'eaton_epdu_group_type:breaker1pole',
        ],
        [
            'eaton_epdu_group_current_th_status:low_warning',
            'eaton_epdu_group_name:forward zombies acted',
            'eaton_epdu_group_type:breaker2pole',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.groupCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.eaton.epdu.groupCurrentPercentLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_group_name:driving Jaded forward quaintly', 'eaton_epdu_group_type:breaker1pole'],
        ['eaton_epdu_group_name:forward zombies acted', 'eaton_epdu_group_type:breaker2pole'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.eaton.epdu.groupVA', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.eaton.epdu.groupWatts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'eaton_epdu_group_control_status:on',
            'eaton_epdu_group_name:driving Jaded forward quaintly',
            'eaton_epdu_group_type:breaker1pole',
        ],
        [
            'eaton_epdu_group_control_status:on',
            'eaton_epdu_group_name:forward zombies acted',
            'eaton_epdu_group_type:breaker2pole',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.groupControl', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_outlet_name:forward but acted zombies', 'eaton_epdu_outlet_voltage_th_status:good'],
        ['eaton_epdu_outlet_name:zombies but acted their', 'eaton_epdu_outlet_voltage_th_status:low_critical'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.outletVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_outlet_current_th_status:high_critical', 'eaton_epdu_outlet_name:forward but acted zombies'],
        ['eaton_epdu_outlet_current_th_status:low_warning', 'eaton_epdu_outlet_name:zombies but acted their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.outletCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.eaton.epdu.outletCurrentPercentLoad', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['eaton_epdu_outlet_name:forward but acted zombies'],
        ['eaton_epdu_outlet_name:zombies but acted their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.eaton.epdu.outletVA', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.eaton.epdu.outletWatts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'eaton_epdu_temperature_name:driving but zombies oxen oxen',
            'eaton_epdu_temperature_probe_status:disconnected',
            'eaton_epdu_temperature_th_status:high_warning',
        ],
        [
            'eaton_epdu_temperature_name:zombies zombies their oxen',
            'eaton_epdu_temperature_probe_status:disconnected',
            'eaton_epdu_temperature_th_status:high_critical',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.temperatureValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'eaton_epdu_humidity_name:oxen their',
            'eaton_epdu_humidity_probe_status:connected',
            'eaton_epdu_humidity_th_status:low_warning',
        ],
        [
            'eaton_epdu_humidity_name:zombies oxen zombies Jaded',
            'eaton_epdu_humidity_probe_status:connected',
            'eaton_epdu_humidity_th_status:high_critical',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.eaton.epdu.humidityValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'eaton_epdu_contact_name:acted their oxen zombies',
            'eaton_epdu_contact_probe_status:connected',
            'eaton_epdu_contact_state:contact_closed',
        ],
        [
            'eaton_epdu_contact_name:their',
            'eaton_epdu_contact_probe_status:connected',
            'eaton_epdu_contact_state:contact_closed',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.eaton.epdu.contact', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'eaton-epdu Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'eaton-epdu.device.name',
        'profile': 'eaton-epdu',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.534.6.6.7',
        'vendor': 'eaton',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
