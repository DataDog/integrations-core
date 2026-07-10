# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.kuma import KumaCheck

from .test_metrics import (
    GAUGE_METRICS_E2E,
)


@pytest.mark.e2e
@pytest.mark.parametrize('gauge', GAUGE_METRICS_E2E)
def test_e2e_gauge_metrics(dd_agent_check, gauge):
    aggregator = dd_agent_check(rate=True)
    aggregator.assert_metric('kuma.' + gauge)


@pytest.mark.e2e
@pytest.mark.parametrize('gauge', GAUGE_METRICS_E2E)
def test_e2e_discovery(aggregator, datadog_agent, gauge):
    run_discovery_check_kubernetes(aggregator, datadog_agent, check_rate=True)
    aggregator.assert_metric('kuma.' + gauge)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        KumaCheck,
        aggregator,
        datadog_agent,
        namespace='kuma-system',
        pod_selector='app=kuma-control-plane',
    )
