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


def test_e2e_profile_silverpeak_edgeconnect(dd_agent_check):
    profile = 'silverpeak-edgeconnect'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:silverpeak-edgeconnect',
        'snmp_host:silverpeak-edgeconnect.device.name',
        'device_hostname:silverpeak-edgeconnect.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.silverpeak.mgmt.spsActiveAlarmCount', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'silverpeak_mgmt_sps_active_alarm_acked:no',
            'silverpeak_mgmt_sps_active_alarm_active:yes',
            'silverpeak_mgmt_sps_active_alarm_clearable:no',
            'silverpeak_mgmt_sps_active_alarm_descr:forward acted driving quaintly kept zombies but Jaded',
            'silverpeak_mgmt_sps_active_alarm_name:Jaded but zombies their zombies',
            'silverpeak_mgmt_sps_active_alarm_service_affect:yes',
            'silverpeak_mgmt_sps_active_alarm_severity:acknowledged',
            'silverpeak_mgmt_sps_active_alarm_source:Jaded driving Jaded oxen driving quaintly quaintly but forward',
            'silverpeak_mgmt_sps_active_alarm_type:acted forward driving driving oxen kept zombies acted driving',
        ],
        [
            'silverpeak_mgmt_sps_active_alarm_acked:no',
            'silverpeak_mgmt_sps_active_alarm_active:yes',
            'silverpeak_mgmt_sps_active_alarm_clearable:yes',
            'silverpeak_mgmt_sps_active_alarm_descr:Jaded oxen oxen their acted acted kept',
            'silverpeak_mgmt_sps_active_alarm_name:their Jaded but forward oxen zombies kept Jaded acted',
            'silverpeak_mgmt_sps_active_alarm_service_affect:no',
            'silverpeak_mgmt_sps_active_alarm_severity:info',
            'silverpeak_mgmt_sps_active_alarm_source:forward quaintly quaintly driving quaintly',
            'silverpeak_mgmt_sps_active_alarm_type:but forward forward Jaded driving quaintly forward',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.silverpeak.mgmt.spsActiveAlarm', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'silverpeak-edgeconnect Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'silverpeak-edgeconnect.device.name',
        'os_version': '9.2',
        'product_name': 'NX-1700',
        'profile': 'silverpeak-edgeconnect',
        'serial_number': '01972WA81B1D',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.23867.1.2.1',
        'vendor': 'silverpeak',
        'device_type': 'sd-wan',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
