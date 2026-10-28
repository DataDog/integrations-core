# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterable

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.weaviate import WeaviateCheck

from .common import E2E_METRICS, FLAKY_E2E_METRICS, OM_METRICS


def assert_metrics(aggregator: AggregatorStub, metrics: Iterable[str]) -> None:
    aggregator.assert_service_check('weaviate.openmetrics.health', ServiceCheck.OK, count=2)
    for metric in metrics:
        if metric in FLAKY_E2E_METRICS:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    assert_metrics(aggregator, E2E_METRICS)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True)

    # Discovery only knows about the metrics port, not the Restful API port, so
    # only the OpenMetrics metrics are collected here.
    assert_metrics(aggregator, OM_METRICS)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check, weaviate_kubeconfig):
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        WeaviateCheck,
        weaviate_kubeconfig,
        namespace='weaviate',
        pod_selector='app=weaviate',
    )
