# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub

from .common import CHECK_CONFIG
from .metrics import ALWAYS_PRESENT_METRICS, NOT_ALWAYS_PRESENT_METRICS

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
    # type: (Any) -> None
    aggregator = dd_agent_check(CHECK_CONFIG, rate=True)  # type: AggregatorStub

    for metric in ALWAYS_PRESENT_METRICS:
        aggregator.assert_metric(metric)

    for metric in NOT_ALWAYS_PRESENT_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()

    for instance in CHECK_CONFIG['instances']:
        tags = ['instance:confluent_platform-localhost-{}'.format(instance['port']), 'jmx_server:localhost']
        aggregator.assert_service_check('confluent.can_connect', status=AgentCheck.OK, tags=tags)
