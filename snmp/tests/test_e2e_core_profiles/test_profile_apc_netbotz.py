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


def test_e2e_profile_apc_netbotz(dd_agent_check):
    profile = 'apc-netbotz'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:apc-netbotz',
        'snmp_host:apc-netbotz.device.name',
        'device_hostname:apc-netbotz.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'netbotz_enclosure_error_status:critical',
            'netbotz_enclosure_id:kept zombies but',
            'netbotz_enclosure_index:2552186985',
            'netbotz_enclosure_label:driving oxen driving Jaded quaintly their',
            'netbotz_enclosure_status:disconnected',
        ],
        [
            'netbotz_enclosure_error_status:info',
            'netbotz_enclosure_id:quaintly but forward oxen kept zombies kept Jaded',
            'netbotz_enclosure_index:784316325',
            'netbotz_enclosure_label:driving driving but oxen',
            'netbotz_enclosure_status:normal',
        ],
        [
            'netbotz_enclosure_error_status:warning',
            'netbotz_enclosure_id:zombies kept',
            'netbotz_enclosure_index:2821035649',
            'netbotz_enclosure_label:but driving Jaded their oxen kept forward driving oxen',
            'netbotz_enclosure_status:normal',
        ],
        [
            'netbotz_enclosure_error_status:warning',
            'netbotz_enclosure_id:zombies their driving',
            'netbotz_enclosure_index:1923702394',
            'netbotz_enclosure_label:zombies but zombies zombies quaintly acted kept acted Jaded',
            'netbotz_enclosure_status:disconnected',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netbotz.enclosure', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'netbotz_din_port_id:but forward their their driving kept',
            'netbotz_din_port_index:3777091038',
            'netbotz_din_port_status:normal',
        ],
        ['netbotz_din_port_id:driving', 'netbotz_din_port_index:2491939166', 'netbotz_din_port_status:normal'],
        [
            'netbotz_din_port_id:driving but Jaded forward forward',
            'netbotz_din_port_index:325729673',
            'netbotz_din_port_status:disconnected',
        ],
        [
            'netbotz_din_port_id:forward quaintly but acted',
            'netbotz_din_port_index:595713748',
            'netbotz_din_port_status:disconnected',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netbotz.dinPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'netbotz_other_port_enc_id:acted driving their quaintly driving their their acted kept',
            'netbotz_other_port_id:zombies oxen but acted but their their oxen kept',
            'netbotz_other_port_index:1715658993',
            'netbotz_other_port_label:Jaded their acted zombies zombies acted acted',
            'netbotz_other_port_status:normal',
        ],
        [
            'netbotz_other_port_enc_id:but oxen forward their driving but kept their',
            'netbotz_other_port_id:zombies kept kept driving oxen acted',
            'netbotz_other_port_index:4273502309',
            'netbotz_other_port_label:acted their forward Jaded',
            'netbotz_other_port_status:disconnected',
        ],
        [
            'netbotz_other_port_enc_id:kept their but forward driving oxen',
            'netbotz_other_port_id:acted Jaded kept but quaintly driving but but forward',
            'netbotz_other_port_index:2172688620',
            'netbotz_other_port_label:zombies Jaded kept but',
            'netbotz_other_port_status:normal',
        ],
        [
            'netbotz_other_port_enc_id:zombies but Jaded acted',
            'netbotz_other_port_id:kept acted their',
            'netbotz_other_port_index:4139037824',
            'netbotz_other_port_label:quaintly driving acted oxen quaintly driving driving oxen',
            'netbotz_other_port_status:normal',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netbotz.otherPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'netbotz_temp_sensor_enc_id:Jaded',
            'netbotz_temp_sensor_error_status:critical',
            'netbotz_temp_sensor_id:driving but',
            'netbotz_temp_sensor_index:142909627',
            'netbotz_temp_sensor_label:driving but Jaded zombies Jaded oxen forward zombies',
        ],
        [
            'netbotz_temp_sensor_enc_id:acted zombies acted driving driving forward forward kept',
            'netbotz_temp_sensor_error_status:info',
            'netbotz_temp_sensor_id:driving forward their oxen',
            'netbotz_temp_sensor_index:2158895031',
            'netbotz_temp_sensor_label:quaintly driving zombies acted their',
        ],
        [
            'netbotz_temp_sensor_enc_id:but kept quaintly zombies driving driving forward',
            'netbotz_temp_sensor_error_status:warning',
            'netbotz_temp_sensor_id:Jaded oxen',
            'netbotz_temp_sensor_index:1853276381',
            'netbotz_temp_sensor_label:oxen but zombies their acted driving',
        ],
        [
            'netbotz_temp_sensor_enc_id:driving',
            'netbotz_temp_sensor_error_status:failure',
            'netbotz_temp_sensor_id:driving driving their zombies zombies Jaded',
            'netbotz_temp_sensor_index:854648332',
            'netbotz_temp_sensor_label:quaintly oxen acted forward Jaded',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netbotz.tempSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netbotz.tempSensorValueIntF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netbotz_humi_sensor_enc_id:Jaded zombies acted acted acted driving but driving forward',
            'netbotz_humi_sensor_error_status:failure',
            'netbotz_humi_sensor_id:zombies driving Jaded zombies acted oxen zombies oxen their',
            'netbotz_humi_sensor_index:3403535678',
            'netbotz_humi_sensor_label:but but Jaded oxen',
        ],
        [
            'netbotz_humi_sensor_enc_id:acted quaintly oxen forward quaintly oxen their acted driving',
            'netbotz_humi_sensor_error_status:critical',
            'netbotz_humi_sensor_id:zombies oxen',
            'netbotz_humi_sensor_index:2263250232',
            'netbotz_humi_sensor_label:quaintly Jaded their their oxen Jaded oxen',
        ],
        [
            'netbotz_humi_sensor_enc_id:driving oxen forward oxen but forward',
            'netbotz_humi_sensor_error_status:critical',
            'netbotz_humi_sensor_id:kept forward forward',
            'netbotz_humi_sensor_index:503266601',
            'netbotz_humi_sensor_label:zombies zombies oxen their their driving but zombies',
        ],
        [
            'netbotz_humi_sensor_enc_id:zombies but but zombies',
            'netbotz_humi_sensor_error_status:warning',
            'netbotz_humi_sensor_id:Jaded but quaintly forward their quaintly driving forward acted',
            'netbotz_humi_sensor_index:438145068',
            'netbotz_humi_sensor_label:forward their quaintly kept zombies their quaintly',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netbotz.humiSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netbotz_dew_point_sensor_enc_id:but Jaded Jaded forward but forward forward',
            'netbotz_dew_point_sensor_id:acted forward driving quaintly driving their',
            'netbotz_dew_point_sensor_index:938672154',
            'netbotz_dew_point_sensor_label:their kept their forward Jaded',
        ],
        [
            'netbotz_dew_point_sensor_enc_id:but acted their',
            'netbotz_dew_point_sensor_id:their',
            'netbotz_dew_point_sensor_index:1969591176',
            'netbotz_dew_point_sensor_label:but zombies acted acted Jaded acted forward acted',
        ],
        [
            'netbotz_dew_point_sensor_enc_id:forward Jaded kept acted quaintly kept kept kept forward',
            'netbotz_dew_point_sensor_id:zombies',
            'netbotz_dew_point_sensor_index:1873211023',
            'netbotz_dew_point_sensor_label:acted oxen kept quaintly their quaintly their',
        ],
        [
            'netbotz_dew_point_sensor_enc_id:kept forward oxen quaintly but',
            'netbotz_dew_point_sensor_id:their kept Jaded zombies but but kept kept but',
            'netbotz_dew_point_sensor_index:3575433492',
            'netbotz_dew_point_sensor_label:oxen kept',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netbotz.dewPointSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.netbotz.dewPointSensorValueIntF', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netbotz_other_numeric_sensor_enc_id:acted but driving kept zombies driving forward oxen oxen',
            'netbotz_other_numeric_sensor_error_status:warning',
            'netbotz_other_numeric_sensor_id:quaintly zombies Jaded',
            'netbotz_other_numeric_sensor_index:2560260351',
            'netbotz_other_numeric_sensor_label:zombies oxen kept Jaded but kept',
            'netbotz_other_numeric_sensor_units:oxen their kept quaintly Jaded their forward',
        ],
        [
            'netbotz_other_numeric_sensor_enc_id:acted their driving their quaintly but',
            'netbotz_other_numeric_sensor_error_status:error',
            'netbotz_other_numeric_sensor_id:acted quaintly kept forward but',
            'netbotz_other_numeric_sensor_index:3347942448',
            'netbotz_other_numeric_sensor_label:but but forward Jaded forward driving Jaded',
            'netbotz_other_numeric_sensor_units:quaintly',
        ],
        [
            'netbotz_other_numeric_sensor_enc_id:forward quaintly',
            'netbotz_other_numeric_sensor_error_status:info',
            'netbotz_other_numeric_sensor_id:forward Jaded their zombies quaintly their forward oxen',
            'netbotz_other_numeric_sensor_index:3895018051',
            'netbotz_other_numeric_sensor_label:Jaded zombies oxen',
            'netbotz_other_numeric_sensor_units:their',
        ],
        [
            'netbotz_other_numeric_sensor_enc_id:their driving but oxen quaintly their oxen but kept',
            'netbotz_other_numeric_sensor_error_status:normal',
            'netbotz_other_numeric_sensor_id:kept kept',
            'netbotz_other_numeric_sensor_index:4191770839',
            'netbotz_other_numeric_sensor_label:but forward but',
            'netbotz_other_numeric_sensor_units:driving their kept quaintly but',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netbotz.otherNumericSensorValueInt', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netbotz_door_switch_sensor_enc_id:but forward',
            'netbotz_door_switch_sensor_id:acted quaintly kept acted',
            'netbotz_door_switch_sensor_index:2901118708',
            'netbotz_door_switch_sensor_label:quaintly',
            'netbotz_door_switch_sensor_value:open',
            'netbotz_door_switch_sensor_value_str:oxen but acted oxen driving',
        ],
        [
            'netbotz_door_switch_sensor_enc_id:driving but oxen but Jaded',
            'netbotz_door_switch_sensor_id:acted',
            'netbotz_door_switch_sensor_index:3577367572',
            'netbotz_door_switch_sensor_label:oxen but but acted kept acted',
            'netbotz_door_switch_sensor_value:closed',
            'netbotz_door_switch_sensor_value_str:acted kept Jaded quaintly but zombies but acted their',
        ],
        [
            'netbotz_door_switch_sensor_enc_id:kept driving oxen acted driving but',
            'netbotz_door_switch_sensor_id:acted oxen Jaded driving forward acted their their quaintly',
            'netbotz_door_switch_sensor_index:3995856408',
            'netbotz_door_switch_sensor_label:oxen driving but Jaded zombies',
            'netbotz_door_switch_sensor_value:open',
            'netbotz_door_switch_sensor_value_str:kept Jaded quaintly their',
        ],
        [
            'netbotz_door_switch_sensor_enc_id:kept kept kept kept zombies their but but kept',
            'netbotz_door_switch_sensor_id:driving oxen zombies zombies quaintly zombies',
            'netbotz_door_switch_sensor_index:943478410',
            'netbotz_door_switch_sensor_label:but their',
            'netbotz_door_switch_sensor_value:closed',
            'netbotz_door_switch_sensor_value_str:forward kept kept driving Jaded zombies Jaded but',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netbotz.doorSwitchSensor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netbotz_other_state_sensor_enc_id:but zombies',
            'netbotz_other_state_sensor_error_status:critical',
            'netbotz_other_state_sensor_id:their oxen forward oxen',
            'netbotz_other_state_sensor_label:their kept driving driving kept their acted',
            'netbotz_other_state_sensor_value_str:but driving kept their acted Jaded',
        ],
        [
            'netbotz_other_state_sensor_enc_id:driving but forward kept driving quaintly quaintly Jaded',
            'netbotz_other_state_sensor_error_status:warning',
            'netbotz_other_state_sensor_id:but quaintly acted acted zombies',
            'netbotz_other_state_sensor_label:forward forward their driving acted',
            'netbotz_other_state_sensor_value_str:driving acted but zombies their driving Jaded',
        ],
        [
            'netbotz_other_state_sensor_enc_id:forward kept quaintly forward zombies',
            'netbotz_other_state_sensor_error_status:error',
            'netbotz_other_state_sensor_id:oxen kept driving',
            'netbotz_other_state_sensor_label:zombies',
            'netbotz_other_state_sensor_value_str:their their zombies forward their kept zombies forward forward',
        ],
        [
            'netbotz_other_state_sensor_enc_id:kept',
            'netbotz_other_state_sensor_error_status:normal',
            'netbotz_other_state_sensor_id:zombies but',
            'netbotz_other_state_sensor_label:their their zombies',
            'netbotz_other_state_sensor_value_str:forward but zombies',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.netbotz.otherStateSensor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'netbotz_error_cond_enc_id:driving Jaded zombies acted kept acted their driving oxen',
            'netbotz_error_cond_id:forward Jaded forward their but',
            'netbotz_error_cond_index:3217337092',
            'netbotz_error_cond_resolved:no',
            'netbotz_error_cond_sensor_id:driving their oxen kept acted kept oxen but',
            'netbotz_error_cond_severity:info',
            'netbotz_error_cond_type_id:their acted oxen zombies Jaded zombies quaintly',
        ],
        [
            'netbotz_error_cond_enc_id:quaintly quaintly acted their',
            'netbotz_error_cond_id:their acted forward forward their',
            'netbotz_error_cond_index:2828061222',
            'netbotz_error_cond_resolved:null',
            'netbotz_error_cond_sensor_id:but Jaded kept driving but',
            'netbotz_error_cond_severity:critical',
            'netbotz_error_cond_type_id:kept acted zombies their but their Jaded their',
        ],
        [
            'netbotz_error_cond_enc_id:their oxen their kept oxen quaintly but',
            'netbotz_error_cond_id:zombies oxen driving',
            'netbotz_error_cond_index:813439363',
            'netbotz_error_cond_resolved:null',
            'netbotz_error_cond_sensor_id:driving',
            'netbotz_error_cond_severity:normal',
            'netbotz_error_cond_type_id:forward zombies kept',
        ],
        [
            'netbotz_error_cond_enc_id:zombies zombies but their but their oxen',
            'netbotz_error_cond_id:but acted acted their quaintly but',
            'netbotz_error_cond_index:3504759843',
            'netbotz_error_cond_resolved:yes',
            'netbotz_error_cond_sensor_id:Jaded kept forward quaintly their driving',
            'netbotz_error_cond_severity:info',
            'netbotz_error_cond_type_id:zombies but their Jaded quaintly their Jaded forward zombies',
        ],
    ]

    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.netbotz.errorCond', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'apc-netbotz Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'apc-netbotz.device.name',
        'profile': 'apc-netbotz',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.5528.100.20.10.2000',
        'vendor': 'apc',
        'device_type': 'sensor',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
