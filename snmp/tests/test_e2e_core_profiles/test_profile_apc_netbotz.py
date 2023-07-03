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
    get_device_ip_from_config, assert_extend_generic_tcp, assert_extend_generic_udp,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_apc_netbotz(dd_agent_check):
    config = create_e2e_core_test_config('apc-netbotz')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:apc-netbotz',
        'snmp_host:apc-netbotz.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_tcp(aggregator, common_tags)
    assert_extend_generic_udp(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'enclosure_error_status:critical',
            'enclosure_id:kept zombies but',
            'enclosure_index:2552186985',
            'enclosure_label:driving oxen driving Jaded quaintly their',
            'enclosure_status:disconnected',
        ],
        [
            'enclosure_error_status:info',
            'enclosure_id:quaintly but forward oxen kept zombies kept Jaded',
            'enclosure_index:784316325',
            'enclosure_label:driving driving but oxen',
            'enclosure_status:normal',
        ],
        [
            'enclosure_error_status:warning',
            'enclosure_id:zombies kept',
            'enclosure_index:2821035649',
            'enclosure_label:but driving Jaded their oxen kept forward driving oxen',
            'enclosure_status:normal',
        ],
        [
            'enclosure_error_status:warning',
            'enclosure_id:zombies their driving',
            'enclosure_index:1923702394',
            'enclosure_label:zombies but zombies zombies quaintly acted kept acted Jaded',
            'enclosure_status:disconnected',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.enclosure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['din_port_id:but forward their their driving kept', 'din_port_index:3777091038', 'din_port_status:normal'],
        ['din_port_id:driving', 'din_port_index:2491939166', 'din_port_status:normal'],
        ['din_port_id:driving but Jaded forward forward', 'din_port_index:325729673', 'din_port_status:disconnected'],
        ['din_port_id:forward quaintly but acted', 'din_port_index:595713748', 'din_port_status:disconnected'],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dinPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'other_port_enc_id:acted driving their quaintly driving their their acted kept',
            'other_port_id:zombies oxen but acted but their their oxen kept',
            'other_port_index:1715658993',
            'other_port_label:Jaded their acted zombies zombies acted acted',
            'other_port_status:normal',
        ],
        [
            'other_port_enc_id:but oxen forward their driving but kept their',
            'other_port_id:zombies kept kept driving oxen acted',
            'other_port_index:4273502309',
            'other_port_label:acted their forward Jaded',
            'other_port_status:disconnected',
        ],
        [
            'other_port_enc_id:kept their but forward driving oxen',
            'other_port_id:acted Jaded kept but quaintly driving but but forward',
            'other_port_index:2172688620',
            'other_port_label:zombies Jaded kept but',
            'other_port_status:normal',
        ],
        [
            'other_port_enc_id:zombies but Jaded acted',
            'other_port_id:kept acted their',
            'other_port_index:4139037824',
            'other_port_label:quaintly driving acted oxen quaintly driving driving oxen',
            'other_port_status:normal',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.otherPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'temp_sensor_enc_id:Jaded',
            'temp_sensor_error_status:critical',
            'temp_sensor_id:driving but',
            'temp_sensor_index:142909627',
            'temp_sensor_label:driving but Jaded zombies Jaded oxen forward zombies',
        ],
        [
            'temp_sensor_enc_id:acted zombies acted driving driving forward forward kept',
            'temp_sensor_error_status:info',
            'temp_sensor_id:driving forward their oxen',
            'temp_sensor_index:2158895031',
            'temp_sensor_label:quaintly driving zombies acted their',
        ],
        [
            'temp_sensor_enc_id:but kept quaintly zombies driving driving forward',
            'temp_sensor_error_status:warning',
            'temp_sensor_id:Jaded oxen',
            'temp_sensor_index:1853276381',
            'temp_sensor_label:oxen but zombies their acted driving',
        ],
        [
            'temp_sensor_enc_id:driving',
            'temp_sensor_error_status:failure',
            'temp_sensor_id:driving driving their zombies zombies Jaded',
            'temp_sensor_index:854648332',
            'temp_sensor_label:quaintly oxen acted forward Jaded',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.tempSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.tempSensorValueIntF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'humi_sensor_enc_id:Jaded zombies acted acted acted driving but driving forward',
            'humi_sensor_error_status:failure',
            'humi_sensor_id:zombies driving Jaded zombies acted oxen zombies oxen their',
            'humi_sensor_index:3403535678',
            'humi_sensor_label:but but Jaded oxen',
        ],
        [
            'humi_sensor_enc_id:acted quaintly oxen forward quaintly oxen their acted driving',
            'humi_sensor_error_status:critical',
            'humi_sensor_id:zombies oxen',
            'humi_sensor_index:2263250232',
            'humi_sensor_label:quaintly Jaded their their oxen Jaded oxen',
        ],
        [
            'humi_sensor_enc_id:driving oxen forward oxen but forward',
            'humi_sensor_error_status:critical',
            'humi_sensor_id:kept forward forward',
            'humi_sensor_index:503266601',
            'humi_sensor_label:zombies zombies oxen their their driving but zombies',
        ],
        [
            'humi_sensor_enc_id:zombies but but zombies',
            'humi_sensor_error_status:warning',
            'humi_sensor_id:Jaded but quaintly forward their quaintly driving forward acted',
            'humi_sensor_index:438145068',
            'humi_sensor_label:forward their quaintly kept zombies their quaintly',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.humiSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'dew_point_sensor_enc_id:but Jaded Jaded forward but forward forward',
            'dew_point_sensor_id:acted forward driving quaintly driving their',
            'dew_point_sensor_index:938672154',
            'dew_point_sensor_label:their kept their forward Jaded',
        ],
        [
            'dew_point_sensor_enc_id:but acted their',
            'dew_point_sensor_id:their',
            'dew_point_sensor_index:1969591176',
            'dew_point_sensor_label:but zombies acted acted Jaded acted forward acted',
        ],
        [
            'dew_point_sensor_enc_id:forward Jaded kept acted quaintly kept kept kept forward',
            'dew_point_sensor_id:zombies',
            'dew_point_sensor_index:1873211023',
            'dew_point_sensor_label:acted oxen kept quaintly their quaintly their',
        ],
        [
            'dew_point_sensor_enc_id:kept forward oxen quaintly but',
            'dew_point_sensor_id:their kept Jaded zombies but but kept kept but',
            'dew_point_sensor_index:3575433492',
            'dew_point_sensor_label:oxen kept',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dewPointSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dewPointSensorValueIntF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'other_numeric_sensor_enc_id:acted but driving kept zombies driving forward oxen oxen',
            'other_numeric_sensor_error_status:warning',
            'other_numeric_sensor_id:quaintly zombies Jaded',
            'other_numeric_sensor_index:2560260351',
            'other_numeric_sensor_label:zombies oxen kept Jaded but kept',
            'other_numeric_sensor_units:oxen their kept quaintly Jaded their forward',
        ],
        [
            'other_numeric_sensor_enc_id:acted their driving their quaintly but',
            'other_numeric_sensor_error_status:error',
            'other_numeric_sensor_id:acted quaintly kept forward but',
            'other_numeric_sensor_index:3347942448',
            'other_numeric_sensor_label:but but forward Jaded forward driving Jaded',
            'other_numeric_sensor_units:quaintly',
        ],
        [
            'other_numeric_sensor_enc_id:forward quaintly',
            'other_numeric_sensor_error_status:info',
            'other_numeric_sensor_id:forward Jaded their zombies quaintly their forward oxen',
            'other_numeric_sensor_index:3895018051',
            'other_numeric_sensor_label:Jaded zombies oxen',
            'other_numeric_sensor_units:their',
        ],
        [
            'other_numeric_sensor_enc_id:their driving but oxen quaintly their oxen but kept',
            'other_numeric_sensor_error_status:normal',
            'other_numeric_sensor_id:kept kept',
            'other_numeric_sensor_index:4191770839',
            'other_numeric_sensor_label:but forward but',
            'other_numeric_sensor_units:driving their kept quaintly but',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.otherNumericSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'door_switch_sensor_enc_id:but forward',
            'door_switch_sensor_id:acted quaintly kept acted',
            'door_switch_sensor_index:2901118708',
            'door_switch_sensor_label:quaintly',
            'door_switch_sensor_value:open',
            'door_switch_sensor_value_str:oxen but acted oxen driving',
        ],
        [
            'door_switch_sensor_enc_id:driving but oxen but Jaded',
            'door_switch_sensor_id:acted',
            'door_switch_sensor_index:3577367572',
            'door_switch_sensor_label:oxen but but acted kept acted',
            'door_switch_sensor_value:closed',
            'door_switch_sensor_value_str:acted kept Jaded quaintly but zombies but acted their',
        ],
        [
            'door_switch_sensor_enc_id:kept driving oxen acted driving but',
            'door_switch_sensor_id:acted oxen Jaded driving forward acted their their quaintly',
            'door_switch_sensor_index:3995856408',
            'door_switch_sensor_label:oxen driving but Jaded zombies',
            'door_switch_sensor_value:open',
            'door_switch_sensor_value_str:kept Jaded quaintly their',
        ],
        [
            'door_switch_sensor_enc_id:kept kept kept kept zombies their but but kept',
            'door_switch_sensor_id:driving oxen zombies zombies quaintly zombies',
            'door_switch_sensor_index:943478410',
            'door_switch_sensor_label:but their',
            'door_switch_sensor_value:closed',
            'door_switch_sensor_value_str:forward kept kept driving Jaded zombies Jaded but',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.doorSwitchSensor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'other_state_sensor_enc_id:but zombies',
            'other_state_sensor_error_status:critical',
            'other_state_sensor_id:their oxen forward oxen',
            'other_state_sensor_label:their kept driving driving kept their acted',
            'other_state_sensor_value_str:but driving kept their acted Jaded',
        ],
        [
            'other_state_sensor_enc_id:driving but forward kept driving quaintly quaintly Jaded',
            'other_state_sensor_error_status:warning',
            'other_state_sensor_id:but quaintly acted acted zombies',
            'other_state_sensor_label:forward forward their driving acted',
            'other_state_sensor_value_str:driving acted but zombies their driving Jaded',
        ],
        [
            'other_state_sensor_enc_id:forward kept quaintly forward zombies',
            'other_state_sensor_error_status:error',
            'other_state_sensor_id:oxen kept driving',
            'other_state_sensor_label:zombies',
            'other_state_sensor_value_str:their their zombies forward their kept zombies forward forward',
        ],
        [
            'other_state_sensor_enc_id:kept',
            'other_state_sensor_error_status:normal',
            'other_state_sensor_id:zombies but',
            'other_state_sensor_label:their their zombies',
            'other_state_sensor_value_str:forward but zombies',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.otherStateSensor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'error_cond_enc_id:driving Jaded zombies acted kept acted their driving oxen',
            'error_cond_id:forward Jaded forward their but',
            'error_cond_index:3217337092',
            'error_cond_resolved:no',
            'error_cond_resolved_time_str:oxen zombies forward zombies',
            'error_cond_sensor_id:driving their oxen kept acted kept oxen but',
            'error_cond_severity:info',
            'error_cond_start_time_str:their kept their but',
            'error_cond_type_id:their acted oxen zombies Jaded zombies quaintly',
        ],
        [
            'error_cond_enc_id:quaintly quaintly acted their',
            'error_cond_id:their acted forward forward their',
            'error_cond_index:2828061222',
            'error_cond_resolved:none',
            'error_cond_resolved_time_str:driving forward but their oxen quaintly kept kept',
            'error_cond_sensor_id:but Jaded kept driving but',
            'error_cond_severity:critical',
            'error_cond_start_time_str:Jaded their driving quaintly quaintly zombies Jaded their',
            'error_cond_type_id:kept acted zombies their but their Jaded their',
        ],
        [
            'error_cond_enc_id:their oxen their kept oxen quaintly but',
            'error_cond_id:zombies oxen driving',
            'error_cond_index:813439363',
            'error_cond_resolved:none',
            'error_cond_resolved_time_str:kept acted driving Jaded their forward Jaded driving',
            'error_cond_sensor_id:driving',
            'error_cond_severity:normal',
            'error_cond_start_time_str:but',
            'error_cond_type_id:forward zombies kept',
        ],
        [
            'error_cond_enc_id:zombies zombies but their but their oxen',
            'error_cond_id:but acted acted their quaintly but',
            'error_cond_index:3504759843',
            'error_cond_resolved:yes',
            'error_cond_resolved_time_str:Jaded their quaintly Jaded',
            'error_cond_sensor_id:Jaded kept forward quaintly their driving',
            'error_cond_severity:info',
            'error_cond_start_time_str:their acted',
            'error_cond_type_id:zombies but their Jaded quaintly their Jaded forward zombies',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.errorCond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'apc-netbotz Device Description SN: 5A1827E00000',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'apc-netbotz.device.name',
        'profile': 'apc-netbotz',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5528.100.20.10.2000',
        'vendor': 'apc',
        'serial_number': '5A1827E00000',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
