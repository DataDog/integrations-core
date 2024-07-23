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


def test_e2e_profile__generic_entity_sensor(dd_agent_check):
    profile = '_generic-entity-sensor'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-entity-sensor',
        'snmp_host:_generic-entity-sensor.device.name',
        'device_hostname:_generic-entity-sensor.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'ent_phy_sensor_type:percent_rh',
            'ent_phy_sensor_scale:micro',
            'ent_phy_sensor_precision:0',
            'ent_phy_sensor_units_display:driving driving forward acted their but',
            'ent_physical_descr:example admin string',
            'ent_physical_class:energy_object',
            'ent_physical_name:console',
            'ent_physical_serial_num:SN12345678',
            'ent_physical_model_name:model name',
            'ent_phy_sensor_oper_status:nonoperational',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.entPhySensorValue', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-entity-sensor Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-entity-sensor.device.name',
        'profile': 'generic-entity-sensor',
        'status': 1,
        'sys_object_id': '1.2.3.1002',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
