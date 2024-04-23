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


def test_e2e_profile_ubiquiti_unifi(dd_agent_check):
    profile = 'ubiquiti-unifi'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:ubiquiti-unifi',
        'snmp_host:ubiquiti-unifi.device.name',
        'device_hostname:ubiquiti-unifi.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + []

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.memory.free', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.total', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    tag_rows = [
        [
            'ubiquiti_unifi_radio_index:11',
            'ubiquiti_unifi_radio_name:kept zombies quaintly their zombies kept driving',
            'ubiquiti_unifi_radio_radio:driving kept oxen their',
        ],
        [
            'ubiquiti_unifi_radio_index:27',
            'ubiquiti_unifi_radio_name:but but oxen kept Jaded driving oxen',
            'ubiquiti_unifi_radio_radio:acted kept driving driving zombies quaintly Jaded driving zombies',
        ],
        ['ubiquiti_unifi_radio_index:31', 'ubiquiti_unifi_radio_name:kept', 'ubiquiti_unifi_radio_radio:kept forward'],
    ]
    for tag_row in tag_rows:
        aggregator.assert_metric(
            'snmp.ubiquiti.unifiRadioCuSelfRx', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ubiquiti.unifiRadioCuSelfTx', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ubiquiti.unifiRadioCuTotal', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ubiquiti.unifiRadioOtherBss', metric_type=aggregator.GAUGE, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ubiquiti.unifiRadioRxPackets', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )
        aggregator.assert_metric(
            'snmp.ubiquiti.unifiRadioTxPackets', metric_type=aggregator.COUNT, tags=common_tags + tag_row
        )

    # --- TEST METADATA ---
    device = {
        'description': 'ubiquiti-unifi Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'ubiquiti-unifi.device.name',
        'profile': 'ubiquiti-unifi',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.41112',
        'vendor': 'ubiquiti',
        'device_type': 'other',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
