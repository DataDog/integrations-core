# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import E2E_EXPECTED_METRIC_COUNTS, E2E_EXPECTED_VALUES, EXCLUDED_APPLIANCE_IP, NS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    for metric_name, expected_count in E2E_EXPECTED_METRIC_COUNTS.items():
        aggregator.assert_metric(f'{NS}.{metric_name}', count=expected_count)

    for metric_name, expected_value, tag_subset in E2E_EXPECTED_VALUES:
        full_name = f'{NS}.{metric_name}'
        aggregator.assert_metric(full_name, value=expected_value)
        if tag_subset:
            aggregator.assert_metric_has_tags(full_name, tag_subset)

    # The excluded appliance must not produce a device.reachability metric.
    for metric in aggregator.metrics(f'{NS}.device.reachability'):
        assert f'device_ip:{EXCLUDED_APPLIANCE_IP}' not in metric.tags

    aggregator.assert_all_metrics_covered()
