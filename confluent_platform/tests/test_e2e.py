# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub

from .common import CHECK_CONFIG
from .metrics import ALWAYS_PRESENT_METRICS, NOT_ALWAYS_PRESENT_METRICS

# TODO: `rate`, `count` metrics are not tested yet in e2e since for the moment those aggregate metrics are not reported.
# TODO: missing e2e coverage for following metrics. See metrics in metrics.yaml.
#   - Kafka Connect Task Metrics
#   - Kafka Connect Sink Metrics
#   - Kafka Connect Source Tasks Metrics
#   - Kafka Connect Task Error Metrics
#   - Confluent Streams Thread
#   - Confluent Streams Thread Task
#   - Confluent Stream Processor Node Metrics


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
