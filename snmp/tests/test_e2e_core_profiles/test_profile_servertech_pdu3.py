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


def test_e2e_profile_servertech_pdu3(dd_agent_check):
    profile = 'servertech-pdu3'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:servertech-pdu3',
        'snmp_host:servertech-pdu3.device.name',
        'device_hostname:servertech-pdu3.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'servertech_sentry3_system_nic_serial_number:oxen',
        'servertech_sentry3_system_version:zombies acted kept quaintly but but',
    ]

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.servertech.sentry3.systemConfigModifiedCount', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.servertech.sentry3.systemTotalPower', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'servertech_sentry3_tower_id:h',
            'servertech_sentry3_tower_model_number:Jaded',
            'servertech_sentry3_tower_name:quaintly acted zombies',
            'servertech_sentry3_tower_product_sn:their their',
            'servertech_sentry3_tower_status:nvm_fail',
        ],
        [
            'servertech_sentry3_tower_id:h',
            'servertech_sentry3_tower_model_number:acted oxen',
            'servertech_sentry3_tower_name:their kept',
            'servertech_sentry3_tower_product_sn:oxen forward',
            'servertech_sentry3_tower_status:nvm_fail',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerActivePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerApparentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerEnergy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerInfeedCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerLineFrequency', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerPowerFactor', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerVACapacity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.towerVACapacityUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry3_infeed_id:ah',
            'servertech_sentry3_infeed_line_id:kept',
            'servertech_sentry3_infeed_line_to_line_id:forward',
            'servertech_sentry3_infeed_load_status:read_error',
            'servertech_sentry3_infeed_name:their quaintly',
            'servertech_sentry3_infeed_phase_id:oxen',
            'servertech_sentry3_infeed_reactance:inductive',
            'servertech_sentry3_infeed_status:no_comm',
        ],
        [
            'servertech_sentry3_infeed_id:ch',
            'servertech_sentry3_infeed_line_id:but',
            'servertech_sentry3_infeed_line_to_line_id:their',
            'servertech_sentry3_infeed_load_status:normal',
            'servertech_sentry3_infeed_name:Jaded acted acted',
            'servertech_sentry3_infeed_phase_id:acted',
            'servertech_sentry3_infeed_reactance:unknown',
            'servertech_sentry3_infeed_status:no_comm',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedCapacity', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedCapacityUsed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedEnergy', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedLoadValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedOutletCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedPhaseCurrent', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedPhaseVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.infeedVoltage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry3_outlet_control_state:locked_off',
            'servertech_sentry3_outlet_id:but',
            'servertech_sentry3_outlet_name:kept',
            'servertech_sentry3_outlet_status:on',
            'servertech_sentry3_outlet_wakeup_state:last',
        ],
        [
            'servertech_sentry3_outlet_control_state:pend_on',
            'servertech_sentry3_outlet_id:but',
            'servertech_sentry3_outlet_name:forward oxen but kept',
            'servertech_sentry3_outlet_status:off_error',
            'servertech_sentry3_outlet_wakeup_state:last',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry3.outlet', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry3_env_mon_id:k',
            'servertech_sentry3_env_mon_name:acted',
            'servertech_sentry3_env_mon_status:no_comm',
        ],
        [
            'servertech_sentry3_env_mon_id:k',
            'servertech_sentry3_env_mon_name:but',
            'servertech_sentry3_env_mon_status:no_comm',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry3.envMon', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        [
            'servertech_sentry3_temp_humid_sensor_humid_status:no_comm',
            'servertech_sentry3_temp_humid_sensor_id:nf',
            'servertech_sentry3_temp_humid_sensor_name:their quaintly',
            'servertech_sentry3_temp_humid_sensor_status:no_comm',
            'servertech_sentry3_temp_humid_sensor_temp_scale:celsius',
            'servertech_sentry3_temp_humid_sensor_temp_status:read_error',
        ],
        [
            'servertech_sentry3_temp_humid_sensor_humid_status:normal',
            'servertech_sentry3_temp_humid_sensor_id:bf',
            'servertech_sentry3_temp_humid_sensor_name:kept',
            'servertech_sentry3_temp_humid_sensor_status:found',
            'servertech_sentry3_temp_humid_sensor_temp_scale:celsius',
            'servertech_sentry3_temp_humid_sensor_temp_status:no_comm',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.servertech.sentry3.tempHumidSensorHumidValue',
            metric_type=aggregator.GAUGE,
            tags=common_tags + tag_row,
        )
        aggregator.assert_metric(
            'snmp.servertech.sentry3.tempHumidSensorTempValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'servertech-pdu3 Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'servertech-pdu3.device.name',
        'profile': 'servertech-pdu3',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.1718.3',
        'vendor': 'servertech',
        'device_type': 'pdu',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
