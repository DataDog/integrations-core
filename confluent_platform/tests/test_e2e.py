# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub

from .common import CHECK_CONFIG
from .metrics import ALWAYS_PRESENT_METRICS, NOT_ALWAYS_PRESENT_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CHECK_CONFIG, rate=True)  # type: AggregatorStub

    # Skip default `jvm.*` metrics by marking them as asserted
    for metric_name in aggregator._metrics:
        if metric_name.startswith('jvm.'):
            aggregator.assert_metric(metric_name)

    for metric in ALWAYS_PRESENT_METRICS:
        aggregator.assert_metric(metric)

    for metric in NOT_ALWAYS_PRESENT_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
