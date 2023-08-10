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


def test_e2e_profile_meraki_cloud_controller(dd_agent_check):
    config = create_e2e_core_test_config('meraki-cloud-controller')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:meraki-cloud-controller',
        'snmp_host:dashboard.meraki.com',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_vendor:meraki',
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        ['mac_address:02:02:00:66:f5:7f', 'network:L_NETWORK', 'product:MR16-HW'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.devClientCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.devStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['mac_address:02:02:00:66:f5:7f', 'network:L_NETWORK', 'product:MR16-HW', 'status:online'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.dev', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['index:4', 'interface:wifi0', 'mac_address:02:02:00:66:f5:00'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.devInterfaceRecvBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.devInterfaceRecvPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.devInterfaceSentBytes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.devInterfaceSentPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': 'Cisco Meraki Cloud Controller',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'location': '123 Fake Blvd, San Francisco, CA 94158, USA',
        'name': 'dashboard.meraki.com',
        'profile': 'meraki-cloud-controller',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.29671.1',
        'vendor': 'meraki',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
