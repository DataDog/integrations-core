# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import PIPELINES_METRICS, PIPELINES_OPTIONAL_METRICS, TRIGGERS_METRICS


def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for expected_metric in PIPELINES_METRICS:
        aggregator.assert_metric(f"tekton.pipelines_controller.{expected_metric}")

    for optional_metrics in PIPELINES_OPTIONAL_METRICS:
        aggregator.assert_metric(f"tekton.pipelines_controller.{optional_metrics}", at_least=0)

    for expected_metric in TRIGGERS_METRICS:
        aggregator.assert_metric(f"tekton.triggers_controller.{expected_metric}")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("tekton.pipelines_controller.openmetrics.health", status=AgentCheck.OK)
    aggregator.assert_service_check("tekton.triggers_controller.openmetrics.health", status=AgentCheck.OK)
