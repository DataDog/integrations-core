# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs import tagger
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tekton import TektonCheck

from .common import PIPELINES_E2E_METRICS, PIPELINES_OPTIONAL_METRICS, TRIGGERS_METRICS


def assert_metrics(aggregator: AggregatorStub) -> None:
    for expected_metric in PIPELINES_E2E_METRICS:
        aggregator.assert_metric(f"tekton.pipelines_controller.{expected_metric}")

    for optional_metrics in PIPELINES_OPTIONAL_METRICS:
        aggregator.assert_metric(f"tekton.pipelines_controller.{optional_metrics}", at_least=0)

    for expected_metric in TRIGGERS_METRICS:
        aggregator.assert_metric(f"tekton.triggers_controller.{expected_metric}")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("tekton.pipelines_controller.openmetrics.health", status=AgentCheck.OK)
    aggregator.assert_service_check("tekton.triggers_controller.openmetrics.health", status=AgentCheck.OK)


def test_check(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    assert_metrics(aggregator)


def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True, discovery_min_instances=2)

    assert_metrics(aggregator)


@pytest.mark.parametrize('container_name', ('tekton-pipelines-controller', 'tekton-triggers-controller'))
def test_e2e_discovery_all_candidates(dd_agent_check, tekton_kubeconfig, container_name):
    tagger.set_tags({f'container_id://{container_name}': [f'kube_container_name:{container_name}']})
    try:
        assert_all_discovery_candidates_stable_kubernetes(
            dd_agent_check,
            TektonCheck,
            tekton_kubeconfig,
            namespace='tekton-pipelines',
            pod_selector=f'app={container_name}',
            service_id=f'docker://{container_name}',
        )
    finally:
        tagger.reset()
