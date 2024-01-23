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
    assert_extend_generic_host_resources,
    assert_extend_generic_if,
    create_e2e_core_test_config,
    get_device_ip_from_config,
)

pytestmark = [pytest.mark.e2e, common.py3_plus_only, common.snmp_integration_only]


def test_e2e_profile_exagrid(dd_agent_check):
    profile = 'exagrid'
    config = create_e2e_core_test_config(profile)
    aggregator = common.dd_agent_check_wrapper(dd_agent_check, config, rate=True)

    ip_address = get_device_ip_from_config(config)
    common_tags = [
        'snmp_profile:exagrid',
        'snmp_host:exagrid.device.name',
        'device_namespace:default',
        'snmp_device:' + ip_address,
    ]

    # --- TEST EXTENDED METRICS ---
    # Examples:
    assert_extend_generic_host_resources(aggregator, common_tags)
    assert_extend_generic_if(aggregator, common_tags)

    # --- TEST METRICS ---
    assert_common_metrics(aggregator, common_tags)

    aggregator.assert_metric(
        'snmp.egBackupDataAvailableFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.egBackupDataAvailableWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.egBackupDataSpaceConsumedFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egBackupDataSpaceConsumedWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egLandingSpaceAvailableFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egLandingSpaceAvailableWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egLandingSpaceConfiguredFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egLandingSpaceConfiguredWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric('snmp.egPendingDeduplicationAge', metric_type=aggregator.GAUGE, tags=common_tags)
    aggregator.assert_metric(
        'snmp.egPendingDeduplicationFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egPendingDeduplicationWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egRetentionSpaceAvailableFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egRetentionSpaceAvailableWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egRetentionSpaceConfiguredFractionalGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )
    aggregator.assert_metric(
        'snmp.egRetentionSpaceConfiguredWholeGigabytes', metric_type=aggregator.GAUGE, tags=common_tags
    )

    # --- TEST METADATA ---
    device = {
        'description': 'exagrid Device Description',
        'id': 'default:' + ip_address,
        'id_tags': ['device_namespace:default', 'snmp_device:' + ip_address],
        'ip_address': '' + ip_address,
        'name': 'exagrid.device.name',
        'profile': 'exagrid',
        'status': 1,
        'sys_object_id': '1.3.6.1.4.1.14941.3.999',
        'vendor': 'exagrid',
    }
    device['tags'] = common_tags
    assert_device_metadata(aggregator, device)

    # --- CHECK COVERAGE ---
    assert_all_profile_metrics_and_tags_covered(profile, aggregator)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
