# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .. import common
from ..test_e2e_core_metadata import assert_device_metadata
from .utils import (
    assert_common_metrics,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile__generic_rtp(dd_agent_check):
    config = create_e2e_core_test_config('_generic-rtp')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:generic-rtp',
        'snmp_host:_generic-rtp.device.name',
        'device_hostname:_generic-rtp.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'rtpSessionIndex:1',
            'rtpSessionLocAddr:but acted their forward Jaded but',
            'rtpSessionRemAddr:quaintly driving quaintly their driving acted Jaded their',
        ],
        ['rtpSessionIndex:15', 'rtpSessionLocAddr:forward their their acted Jaded', 'rtpSessionRemAddr:acted their'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.rtpSessionByes', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.rtpSessionReceiverJoins', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.rtpSessionSenderJoins', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['rtpSenderSSRC:42843', 'rtpSessionIndex:9'],
        ['rtpSenderSSRC:56224', 'rtpSessionIndex:26'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.rtpSenderOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.rtpSenderPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        ['rtpRcvrSRCSSRC:4008', 'rtpRcvrSSRC:728', 'rtpSessionIndex:14'],
        ['rtpRcvrSRCSSRC:50583', 'rtpRcvrSSRC:48690', 'rtpSessionIndex:21'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.rtpRcvrJitter', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.rtpRcvrLostPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.rtpRcvrOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.rtpRcvrPackets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_generic-rtp Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_generic-rtp.device.name',
        'profile': 'generic-rtp',
        'status': 1,
        'sys_object_id': '1.2.3.1009.123',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
