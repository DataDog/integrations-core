# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..metrics import (
    IF_BANDWIDTH_USAGE,
    IF_COUNTS,
    IF_CUSTOM_SPEED_GAUGES,
    IF_GAUGES,
    IF_RATES,
    IF_SCALAR_GAUGE,
)
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_all_profile_metrics_and_tags_covered,
    assert_common_metrics,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_meraki_cloud_controller(dd_agent_check):
    profile = 'meraki-cloud-controller'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:meraki-cloud-controller',
        'snmp_host:dashboard.meraki.com',
        'device_hostname:dashboard.meraki.com',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
        'device_vendor:meraki',
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    if_tags = ['interface:eth0', 'interface_index:11'] + common_tags
    for metric in IF_COUNTS:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.COUNT, tags=if_tags, count=1)

    for metric in IF_SCALAR_GAUGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=common_tags)

    for metric in IF_GAUGES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags)

    for metric in IF_RATES:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags)

    for metric in IF_BANDWIDTH_USAGE:
        aggregator.assert_metric('snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags)

    for metric in IF_CUSTOM_SPEED_GAUGES:
        aggregator.assert_metric(
            'snmp.{}'.format(metric), metric_type=aggregator.GAUGE, tags=if_tags + ['speed_source:device']
        )

    aggregator.assert_metric('snmp.sysUpTimeInstance', metric_type=aggregator.GAUGE, tags=common_tags)

    tag_rows = [
        ['mac_address:02:02:00:66:f5:7f', 'network:L_NETWORK', 'product:MR16-HW', 'device_name:Gymnasium'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.devClientCount', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.devStatus', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'mac_address:02:02:00:66:f5:7f',
            'network:L_NETWORK',
            'product:MR16-HW',
            'status:online',
            'device_name:Gymnasium',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.meraki.dev', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

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
        'device_type': 'sd-wan',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
