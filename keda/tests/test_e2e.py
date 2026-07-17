# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.dev.utils import assert_service_checks
from datadog_checks.keda import KedaCheck

KEDA_POD_SELECTORS = (
    'app=keda-operator',
    'app=keda-operator-metrics-apiserver',
    'app=keda-admission-webhooks',
)


def test_e2e_openmetrics_v2(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_service_check('keda.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(aggregator, datadog_agent):
    run_discovery_check_kubernetes(aggregator, datadog_agent, discovery_min_instances=len(KEDA_POD_SELECTORS))

    aggregator.assert_service_check('keda.openmetrics.health', ServiceCheck.OK, count=len(KEDA_POD_SELECTORS))
    assert_service_checks(aggregator)


@pytest.mark.e2e
@pytest.mark.parametrize('pod_selector', KEDA_POD_SELECTORS)
def test_e2e_discovery_all_candidates(aggregator, datadog_agent, pod_selector):
    assert_all_discovery_candidates_stable_kubernetes(
        KedaCheck,
        aggregator,
        datadog_agent,
        namespace='keda',
        pod_selector=pod_selector,
    )
