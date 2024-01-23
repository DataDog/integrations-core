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


def test_e2e_profile__cisco_ipsec_flow_monitor(dd_agent_check):
    config = create_e2e_core_test_config('_cisco-ipsec-flow-monitor')
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:cisco-ipsec-flow-monitor',
        'snmp_host:_cisco-ipsec-flow-monitor.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    tag_rows = [
        [
            'peer_local_value:forward quaintly',
            'peer_remote_value:oxen but acted Jaded driving',
            'phase_1_tunnel_index:9',
            'tunnel_status:active',
        ],
        [
            'peer_local_value:kept quaintly oxen acted but driving',
            'peer_remote_value:kept Jaded their',
            'phase_1_tunnel_index:3',
            'tunnel_status:destroy',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cikeTunInDropPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cikeTunInOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cikeTunInPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cikeTunLifeTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cikeTunOutDropPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cikeTunOutOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cikeTunOutPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    tag_rows = [
        [
            'peer_local_address:oxen',
            'peer_remote_address:oxen forward but',
            'phase_1_tunnel_index:21',
            'phase_2_tunnel_index:31',
            'tunnel_alive:true',
            'tunnel_status:destroy',
        ],
        [
            'peer_local_address:their Jaded kept',
            'peer_remote_address:oxen',
            'phase_1_tunnel_index:27',
            'phase_2_tunnel_index:5',
            'tunnel_alive:false',
            'tunnel_status:destroy',
        ],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric('snmp.cipSecTunHcInOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cipSecTunHcOutOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cipSecTunInAuthFails', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cipSecTunInDecryptFails', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cipSecTunInOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cipSecTunInPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cipSecTunLifeTime', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cipSecTunOutAuthFails', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric(
            'snmp.cipSecTunOutEncryptFails', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric('snmp.cipSecTunOutOctets', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)
        aggregator.assert_metric('snmp.cipSecTunOutPkts', metric_type=aggregator.GAUGE, tags=common_tags + tag_row)

    # --- TEST METADATA ---
    device = {
        'description': '_cisco-ipsec-flow-monitor Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': '_cisco-ipsec-flow-monitor.device.name',
        'profile': 'cisco-ipsec-flow-monitor',
        'status': 1,
        'sys_object_id': '1.2.3.1008.123',
        # 'vendor': '_cisco',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
