# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .common import COUNTS, GAUGES


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    instance = {}
    aggregator = dd_agent_check(instance, rate=True)

    for metric in GAUGES:
        aggregator.assert_metric(metric, metric_type=aggregator.GAUGE)

    for metric in COUNTS:
        aggregator.assert_metric(metric, metric_type=aggregator.MONOTONIC_COUNT)

    aggregator.assert_all_metrics_covered()

    jvm_metrics = [metric for metric in GAUGES if metric.startswith('jvm')]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_metric_type=False, exclude=jvm_metrics)

    aggregator.assert_service_check("ignite.can_connect")
