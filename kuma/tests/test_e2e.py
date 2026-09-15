# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
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
def test_e2e_discovery(dd_agent_check_discovery, gauge):
    aggregator = dd_agent_check_discovery(check_rate=True)
    aggregator.assert_metric('kuma.' + gauge)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check, kuma_kubeconfig):
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        KumaCheck,
        kuma_kubeconfig,
        namespace='kuma-system',
        pod_selector='app=kuma-control-plane',
    )
