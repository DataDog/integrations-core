# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_3com_huawei(dd_agent_check):
    config = create_e2e_core_test_config('3com-huawei')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:3com-huawei',
        'snmp_host:3com-huawei.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['cpu:881'],
        ['cpu:882'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mem:991'],
        ['mem:992'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['hw_dev_m_fan_num:11', 'hw_dev_m_fan_status:active'],
        ['hw_dev_m_fan_num:12', 'hw_dev_m_fan_status:deactive'],
        ['hw_dev_m_fan_num:13', 'hw_dev_m_fan_status:not_installed'],
        ['hw_dev_m_fan_num:14', 'hw_dev_m_fan_status:unsupported'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.hwdevMFanStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['hw_dev_m_power_num:11', 'hw_dev_m_power_status:active'],
        ['hw_dev_m_power_num:12', 'hw_dev_m_power_status:deactive'],
        ['hw_dev_m_power_num:13', 'hw_dev_m_power_status:not_installed'],
        ['hw_dev_m_power_num:14', 'hw_dev_m_power_status:unsupported'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.hwdevMPowerStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

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
        'vendor': '3com',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
