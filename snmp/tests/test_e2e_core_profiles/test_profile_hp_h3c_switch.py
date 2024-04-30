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


def test_e2e_profile_hp_h3c_switch(dd_agent_check):
    profile = 'hp-h3c-switch'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:hp-h3c-switch',
        'snmp_host:hp-h3c-switch.device.name',
        'device_hostname:hp-h3c-switch.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)
    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['hh3c_process_id:17191', 'hh3c_process_name:kept but'],
        ['hh3c_process_id:27865', 'hh3c_process_name:kept their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.hh3cProcessUtil5Min', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['cpu:11', 'hh3c_entity_ext_physical_index:11', 'ent_physical_name:name2'],
        ['cpu:2', 'hh3c_entity_ext_physical_index:2', 'ent_physical_name:name1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem:11', 'hh3c_entity_ext_physical_index:11', 'ent_physical_name:name2'],
        ['mem:2', 'hh3c_entity_ext_physical_index:2', 'ent_physical_name:name1'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'hp-h3c-switch Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'hp-h3c-switch.device.name',
        'profile': 'hp-h3c-switch',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.25506.11.1.999',
        'vendor': 'hp',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
