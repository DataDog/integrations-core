# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.traffic_server import TrafficServerCheck

from .common import EXPECTED_COUNT_METRICS, EXPECTED_GAUGE_METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance, aggregator):
    dd_agent_check(instance, rate=True)
    traffic_server_tags = instance.get('tags')

    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK)
    for metric_name in EXPECTED_COUNT_METRICS:
        aggregator.assert_metric(metric_name, count=1, tags=traffic_server_tags, metric_type=AggregatorStub.COUNT)

    for metric_name in EXPECTED_GAUGE_METRICS:
        aggregator.assert_metric(metric_name, count=2, tags=traffic_server_tags, metric_type=AggregatorStub.GAUGE)
