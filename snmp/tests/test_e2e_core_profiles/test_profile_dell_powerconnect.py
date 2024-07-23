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


def test_e2e_profile_dell_powerconnect(dd_agent_check):
    profile = 'dell-powerconnect'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:dell-powerconnect',
        'snmp_host:dell-powerconnect.device.name',
        'device_hostname:dell-powerconnect.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, value=41.14, tags=common_tags)
    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        ['dell_env_mon_fan_state:not_functioning', 'dell_env_mon_fan_status_descr:acted Jaded'],
        ['dell_env_mon_fan_state:warning', 'dell_env_mon_fan_status_descr:driving driving oxen but kept'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dell.envMonFanSpeed', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'dell_env_mon_supply_source:dc',
            'dell_env_mon_supply_state:critical',
            'dell_env_mon_supply_status_descr:quaintly oxen their forward oxen',
        ],
        [
            'dell_env_mon_supply_source:dc',
            'dell_env_mon_supply_state:warning',
            'dell_env_mon_supply_status_descr:oxen quaintly quaintly',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.dell.envMonSupplyAveragePower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.dell.envMonSupplyCurrentPower', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'dell-powerconnect Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'dell-powerconnect.device.name',
        'profile': 'dell-powerconnect',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.674.10895.3115',
        'vendor': 'dell',
        'version': '6.0',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
