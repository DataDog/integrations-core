# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.kubernetes import assert_all_discovery_candidates_stable_kubernetes
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.fluxcd import FluxcdCheck

from .common import EXPECTED_METRICS

# All flux-system controllers deployed by the kind fixture and matched by the check's
# ad_identifiers, including image-automation-controller, which the non-discovery E2E test's
# fixed instance list omits. image-reflector-controller is also a valid ad_identifier but isn't
# listed here: the kind fixture's install.yaml deliberately excludes its Deployment because it
# never reached Ready in CI, so it has no running pod for the discovery E2E tests to exercise.
ALL_CONTROLLERS = (
    'source-controller',
    'helm-controller',
    'image-automation-controller',
    'kustomize-controller',
    'notification-controller',
)


def assert_metrics(aggregator: AggregatorStub) -> None:
    ignore = {
        'fluxcd.controller.runtime.reconcile.count',
        'fluxcd.controller.runtime.reconcile.errors.count',
        'fluxcd.controller.runtime.reconcile.time.seconds.bucket',
        'fluxcd.controller.runtime.reconcile.time.seconds.count',
        'fluxcd.controller.runtime.reconcile.time.seconds.sum',
        'fluxcd.gotk.reconcile.condition',
        'fluxcd.gotk.reconcile.duration.seconds.bucket',
        'fluxcd.gotk.reconcile.duration.seconds.count',
        'fluxcd.gotk.reconcile.duration.seconds.sum',
        # Emitted by kube-state-metrics (Flux 2.1+), not Flux controller /metrics endpoints.
        'fluxcd.gotk.resource.info',
        'fluxcd.gotk.suspend.status',
        'fluxcd.process.cpu_seconds.count',
        'fluxcd.workqueue.adds.count',
        'fluxcd.workqueue.retries.count',
    }
    for metric_name in set(EXPECTED_METRICS['v2']) - ignore:
        aggregator.assert_metric(metric_name)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_source_controller_metrics(dd_agent_check):
    """
    This only tests version 2 of flux.

    Version 1 is in maintenance mode, all our users are on version 2.
    """
    aggregator = dd_agent_check()
    assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    # Kubelet Autodiscovery is expected to find all five flux-system controller pods (the four
    # exercised by the non-discovery E2E test above plus image-automation-controller).
    aggregator = dd_agent_check_discovery(discovery_min_instances=len(ALL_CONTROLLERS))
    assert_metrics(aggregator)


@pytest.mark.e2e
@pytest.mark.parametrize('controller', ALL_CONTROLLERS)
def test_e2e_discovery_all_candidates(dd_agent_check, fluxcd_kubeconfig, controller):
    assert_all_discovery_candidates_stable_kubernetes(
        dd_agent_check,
        FluxcdCheck,
        fluxcd_kubeconfig,
        namespace='flux-system',
        pod_selector=f'app={controller}',
    )
