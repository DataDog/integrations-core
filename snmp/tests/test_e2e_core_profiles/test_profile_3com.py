# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    create_profile_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_3com(dd_agent_check):
    config = create_profile_test_config('3com')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:3com',
        'snmp_host:3com.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)
    aggregator.assert_all_metrics_covered()

    # --- TEST METADATA ---
    device = {
        'description': '3Com Device Desc',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '3com.device.name',
        'profile': '3com',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.43.1.999',
        'tags': [
            'device_namespace:default',
            'snmp_device:' + ip_address,
            'snmp_host:3com.device.name',
            'snmp_profile:3com',
        ],
        'vendor': '3com',
    }
    assert_device_metadata(aggregator, device)
