# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Callable, Dict

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.traffic_server import TrafficServerCheck
from datadog_checks.traffic_server.metrics import COUNT_METRICS, GAUGE_METRICS


def test_check(aggregator, instance, dd_run_check):
    check = TrafficServerCheck('traffic_server', {}, [instance])
    dd_run_check(check)

    for metric_name in COUNT_METRICS:
        aggregator.assert_metric(
            metric_name, count=1, tags=instance.get('tags'), metric_type=AggregatorStub.MONOTONIC_COUNT
        )

    for metric_name in GAUGE_METRICS:
        aggregator.assert_metric(metric_name, count=1, tags=instance.get('tags'), metric_type=AggregatorStub.GAUGE)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    check = TrafficServerCheck('traffic_server', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK)
