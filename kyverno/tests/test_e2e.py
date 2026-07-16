# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.dev.utils import assert_service_checks
from datadog_checks.kyverno import KyvernoCheck


def test_kyverno_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(aggregator, datadog_agent):
    run_discovery_check_kubernetes(aggregator, datadog_agent, discovery_min_instances=4, check_rate=True)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        KyvernoCheck,
        aggregator,
        datadog_agent,
        namespace='kyverno',
        pod_selector='app.kubernetes.io/component=admission-controller',
    )
