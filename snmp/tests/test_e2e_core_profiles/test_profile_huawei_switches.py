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


def test_e2e_profile_huawei_switches(dd_agent_check):
    profile = 'huawei-switches'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:huawei-switches',
        'snmp_host:huawei-switches.device.name',
        'device_hostname:huawei-switches.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.huawei.hwStackReservedVlanId', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'huawei_hw_member_stack_device_type:zombies',
            'huawei_hw_member_stack_mac_address:11:11:11:11:11:11',
            'huawei_hw_member_stack_object_id:1.3.6.1.3.171.33.176.239.107.21.245',
            'huawei_hw_member_stack_role:standby',
        ],
        [
            'huawei_hw_member_stack_device_type:zombies',
            'huawei_hw_member_stack_mac_address:12:12:12:12:12:12',
            'huawei_hw_member_stack_object_id:1.3.6.1.3.122.98',
            'huawei_hw_member_stack_role:standby',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.huawei.hwMemberStackPriority', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )

    tag_rows = [
        ['huawei_hw_stack_port_name:acted oxen', 'huawei_hw_stack_port_status:up'],
        ['huawei_hw_stack_port_name:zombies their oxen their but forward', 'huawei_hw_stack_port_status:up'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.huawei.hwStackPort', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'huawei-switches Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'huawei-switches.device.name',
        'profile': 'huawei-switches',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.2011.2.23.606',
        'vendor': 'huawei',
        'device_type': 'switch',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
