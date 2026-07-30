# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.flink import FlinkCheck

from .common import METRICS, TAGS

pytestmark = [pytest.mark.unit]

OPERATOR_TAGS = TAGS + ["tm_id:tm-1", "job_name:wordcount", "operator_name:Source", "subtask_index:0"]


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


def test_service_checks(dd_run_check, aggregator, check, mock_metrics):
    dd_run_check(check)
    aggregator.assert_service_check('flink.openmetrics.health', FlinkCheck.OK, tags=TAGS)


def test_custom_metric_not_collected_by_default(dd_run_check, aggregator, check, mock_metrics):
    """A job-defined custom metric (not in METRIC_MAP) is silently dropped without `extra_metrics`."""
    dd_run_check(check)
    aggregator.assert_metric("flink.operator.messageLatency", count=0)
    aggregator.assert_metric("flink.flink_taskmanager_job_task_operator_messageLatency", count=0)


def test_custom_metric_collected_via_extra_metrics(dd_run_check, aggregator, instance, mock_metrics):
    """`extra_metrics` with an explicit rename collects the custom metric under a clean DD name."""
    instance = copy.deepcopy(instance)
    instance["extra_metrics"] = [{"flink_taskmanager_job_task_operator_messageLatency": "operator.messageLatency"}]
    check = FlinkCheck('flink', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "flink.operator.messageLatency.count",
        value=7.0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=OPERATOR_TAGS,
    )


def test_custom_metric_collected_via_extra_metrics_regex(dd_run_check, aggregator, instance, mock_metrics):
    """A regex `extra_metrics` entry also collects the metric, but under its raw Prometheus name --
    regex entries can't be renamed (see the `extra_metrics` docs in the README)."""
    instance = copy.deepcopy(instance)
    instance["extra_metrics"] = ["^flink_taskmanager_job_task_operator_messageLatency$"]
    check = FlinkCheck('flink', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "flink.flink_taskmanager_job_task_operator_messageLatency.count",
        value=7.0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=OPERATOR_TAGS,
    )


def test_custom_metric_type_override_via_extra_metrics(dd_run_check, aggregator, instance, mock_metrics):
    """`extra_metrics`' `type:` override fixes a wrong exposed type (same failure mode as Bug 1 --
    counters exposed as `gauge` -- but on a custom metric this integration can't know about ahead of time)."""
    instance = copy.deepcopy(instance)
    instance["extra_metrics"] = [
        {
            "flink_taskmanager_job_task_operator_customEventsTotal": {
                "name": "operator.customEventsTotal",
                "type": "counter",
            }
        }
    ]
    check = FlinkCheck('flink', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "flink.operator.customEventsTotal.count",
        value=9.0,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=OPERATOR_TAGS,
    )
