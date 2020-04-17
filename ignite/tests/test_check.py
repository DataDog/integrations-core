# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

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

    aggregator.assert_service_check("ignite.can_connect")
