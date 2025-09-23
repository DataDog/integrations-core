# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.openmetrics import OpenMetricsCheck

from .common import CHECK_NAME, INSTANCE


@pytest.mark.integration
def test_integration(aggregator, dd_run_check, dd_environment):
    check = OpenMetricsCheck('openmetrics', {}, [dd_environment])
    dd_run_check(check)
    aggregator.assert_metric(CHECK_NAME + '.go_memstats_mallocs_total', metric_type=aggregator.MONOTONIC_COUNT)
    assert_metrics_covered(aggregator)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)
    aggregator.assert_metric(CHECK_NAME + '.go_memstats_mallocs_total', metric_type=aggregator.COUNT)
    assert_metrics_covered(aggregator)


def assert_metrics_covered(aggregator):
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.sum', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.count', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.target_interval_seconds.quantile', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.go_memstats_alloc_bytes', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.http_req_duration_seconds.count', metric_type=aggregator.GAUGE)
    aggregator.assert_metric(CHECK_NAME + '.http_req_duration_seconds.sum', metric_type=aggregator.GAUGE)
    aggregator.assert_all_metrics_covered()
