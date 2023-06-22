# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_apc_netbotz(dd_agent_check):
    config = create_e2e_core_test_config('apc-netbotz')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:apc-netbotz',
        'snmp_host:apc-netbotz.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_all_metrics_covered()

    # --- TEST METADATA ---
    device = {
        'description': 'apc-netbotz Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'apc-netbotz.device.name',
        'profile': 'apc-netbotz',
        'status': 1,
        'sys_object_id': '1.2.3.999',
        'vendor': 'apc',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)
