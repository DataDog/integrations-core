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


def test_e2e_profile_3com_huawei(dd_agent_check):
    profile = '3com-huawei'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:3com-huawei',
        'snmp_host:3com-huawei.device.name',
        'device_hostname:3com-huawei.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    cpu_ids = [881, 882]
    for cpu in cpu_ids:
        cpu_tags = common_tags + ['cpu:{}'.format(cpu)]
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=cpu_tags)

    mem_ids = [991, 992]
    for mem in mem_ids:
        mem_tags = common_tags + ['mem:{}'.format(mem)]
        aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=mem_tags)
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=mem_tags)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=mem_tags)

    fan_row_tags = [
        ["fan_num:11", "fan_status:active"],
        ["fan_num:12", "fan_status:deactive"],
        ["fan_num:13", "fan_status:not_installed"],
        ["fan_num:14", "fan_status:unsupported"],
    ]
    for fan_tags in fan_row_tags:
        aggregator.assert_metric('snmp.hwdevMFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + fan_tags)

    fan_row_tags = [
        ["power_num:11", "power_status:active"],
        ["power_num:12", "power_status:deactive"],
        ["power_num:13", "power_status:not_installed"],
        ["power_num:14", "power_status:unsupported"],
    ]
    for fan_tags in fan_row_tags:
        aggregator.assert_metric('snmp.hwdevMPowerStatus', metric_type=aggregator.GAUGE, tags=common_tags + fan_tags)

    # --- TEST METADATA ---
    device = {
        'description': '3Com Huawei Device Desc',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '3com-huawei.device.name',
        'profile': '3com-huawei',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.43.45.1.2.999',
        'tags': [
            'device_id:default:' + ip_address,
            'device_ip:' + ip_address,
            'device_namespace:default',
            'snmp_device:' + ip_address,
            'snmp_host:3com-huawei.device.name',
            'device_hostname:3com-huawei.device.name',
            'snmp_profile:3com-huawei',
        ],
        'vendor': '3com',
        'device_type': 'other',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
