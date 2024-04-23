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


def test_e2e_profile_meraki(dd_agent_check):
    profile = 'meraki'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'device_namespace:default',
        'device_vendor:meraki',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'snmp_host:dashboard.meraki.com',
        'device_hostname:dashboard.meraki.com',
        'snmp_profile:meraki',
    ]

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    # --- TEST METADATA ---
    device = {
        'description': 'Cisco Meraki Device mini',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'location': '123 Fake Blvd, San Francisco, CA 94158, USA',
        'name': 'dashboard.meraki.com',
        'profile': 'meraki',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.29671.2.1',
        'tags': [
            'device_id:default:' + ip_address,
            'device_ip:' + ip_address,
            'device_namespace:default',
            'device_vendor:meraki',
            'snmp_device:' + ip_address,
            'snmp_host:dashboard.meraki.com',
            'device_hostname:dashboard.meraki.com',
            'snmp_profile:meraki',
        ],
        'vendor': 'meraki',
        'device_type': 'other',
    }
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
