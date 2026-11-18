# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import assert_service_checks
from datadog_checks.kyverno import KyvernoCheck

CONTROLLERS = (
    'admission-controller',
    'background-controller',
    'cleanup-controller',
    'reports-controller',
)


def test_kyverno_e2e(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    aggregator.assert_service_check('kyverno.openmetrics.health', ServiceCheck.OK, count=8)
    assert_service_checks(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(check_rate=True, discovery_min_instances=4)
    aggregator.assert_service_check('kyverno.openmetrics.health', ServiceCheck.OK, count=8)
    assert_service_checks(aggregator)


@pytest.mark.e2e
@pytest.mark.parametrize('controller', CONTROLLERS)
def test_e2e_discovery_all_candidates(dd_agent_check, kyverno_kubeconfig, controller):
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        KyvernoCheck,
        kyverno_kubeconfig,
        namespace='kyverno',
        pod_selector=f'app.kubernetes.io/component={controller}',
    )
