# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from .common import PIPELINES_METRICS, TRIGGERS__METRICS


def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for expected_metric in PIPELINES_METRICS + TRIGGERS__METRICS:
        aggregator.assert_metric(f"tekton.{expected_metric}")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("tekton.openmetrics.health", status=AgentCheck.OK, count=4)
