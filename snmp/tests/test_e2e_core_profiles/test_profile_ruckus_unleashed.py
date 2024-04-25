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


def test_e2e_profile_ruckus_unleashed(dd_agent_check):
    profile = 'ruckus-unleashed'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:ruckus-unleashed',
        'snmp_host:ruckus-unleashed.device.name',
        'device_hostname:ruckus-unleashed.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
        'device_ip:' + ip_address,
        'device_id:default:' + ip_address,
    ] + [
        'ruckus_unleashed_system_licensed_aps:34750',
        'ruckus_unleashed_system_serial_number:acted but',
        'ruckus_unleashed_system_model:forward driving',
    ]

    # --- TEST EXTENDED METRICS ---
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric('snmp.cpu.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.memory.usage', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ruckusUnleashedSystemStatsAllNumSta', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric('snmp.ruckusUnleashedSystemStatsNumAP', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsNumRegisteredAP', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalAssocFail', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalRxBytes', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalRxPkts', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalTxBytes', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalTxFail', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalTxPkts', metric_type=aggregator.COUNT, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.ruckusUnleashedSystemStatsWLANTotalTxRetry', metric_type=aggregator.COUNT, tags=common_tags
    )

    # --- TEST METADATA ---
    device = {
        'description': 'ruckus-unleashed Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'ruckus-unleashed.device.name',
        'profile': 'ruckus-unleashed',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.25053.3.1.5.15',
        'vendor': 'ruckus',
        'device_type': 'wlc',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
