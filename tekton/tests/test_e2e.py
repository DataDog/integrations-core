# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tekton import TektonCheck

from .common import PIPELINES_E2E_METRICS, PIPELINES_OPTIONAL_METRICS, TRIGGERS_METRICS


def assert_pipeline_metrics(aggregator):
    for expected_metric in PIPELINES_E2E_METRICS:
        aggregator.assert_metric(f"tekton.pipelines_controller.{expected_metric}")

    for optional_metrics in PIPELINES_OPTIONAL_METRICS:
        aggregator.assert_metric(f"tekton.pipelines_controller.{optional_metrics}", at_least=0)

    aggregator.assert_service_check("tekton.pipelines_controller.openmetrics.health", status=AgentCheck.OK)


def assert_triggers_metrics(aggregator):
    for expected_metric in TRIGGERS_METRICS:
        aggregator.assert_metric(f"tekton.triggers_controller.{expected_metric}")

    aggregator.assert_service_check("tekton.triggers_controller.openmetrics.health", status=AgentCheck.OK)


def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    assert_pipeline_metrics(aggregator)
    assert_triggers_metrics(aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_discovery(aggregator, datadog_agent):
    run_discovery_check_kubernetes(aggregator, datadog_agent, check_rate=True)

    # Discovery only probes the Pipelines Controller's own container port since
    # the Triggers Controller doesn't have a declared port in its container
    # metadata.
    assert_pipeline_metrics(aggregator)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        TektonCheck,
        aggregator,
        datadog_agent,
        namespace='tekton-pipelines',
        pod_selector='app=tekton-pipelines-controller',
    )
