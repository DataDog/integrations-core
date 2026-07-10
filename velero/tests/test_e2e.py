# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.velero import VeleroCheck

from .common import OPTIONAL_METRICS, TEST_METRICS


@pytest.mark.e2e
def test_check_velero_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)

    for metric, _ in TEST_METRICS.items():
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(name=metric, at_least=0)
        else:
            aggregator.assert_metric(name=metric, at_least=1)

    aggregator.assert_service_check('velero.openmetrics.health', ServiceCheck.OK)


@pytest.mark.e2e
def test_e2e_discovery(aggregator, datadog_agent):
    # Both the velero server and node-agent pods run the same image and expose the same metrics on
    # the same port, so discovery is expected to produce one instance per pod.
    run_discovery_check_kubernetes(aggregator, datadog_agent, check_rate=True, discovery_min_instances=2)

    for metric, _ in TEST_METRICS.items():
        if metric in OPTIONAL_METRICS:
            aggregator.assert_metric(name=metric, at_least=0)
        else:
            aggregator.assert_metric(name=metric, at_least=1)

    aggregator.assert_service_check('velero.openmetrics.health', ServiceCheck.OK)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        VeleroCheck,
        aggregator,
        datadog_agent,
        namespace='velero',
        pod_selector='name=velero',
    )
