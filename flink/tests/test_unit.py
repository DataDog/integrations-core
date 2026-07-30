# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.flink import FlinkCheck

from .common import COUNTER_METRICS, METRICS, TAGS

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)

    for expected_metric in METRICS:
        aggregator.assert_metric(
            name=f"flink.{expected_metric['name']}",
            value=expected_metric.get("value"),
            metric_type=expected_metric.get("type", aggregator.GAUGE),
            tags=expected_metric.get("tags", TAGS),
        )

    aggregator.assert_no_duplicate_all()


def test_counters_submitted_as_monotonic_count(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)

    for expected_metric in COUNTER_METRICS:
        aggregator.assert_metric(
            name=f"flink.{expected_metric['name']}",
            value=expected_metric["value"],
            metric_type=AggregatorStub.MONOTONIC_COUNT,
            tags=expected_metric["tags"],
        )


def test_service_checks(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    aggregator.assert_service_check('flink.openmetrics.health', FlinkCheck.OK, tags=TAGS)
