# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.kube_discovery import (
    assert_all_discovery_candidates_stable_kubernetes,
    run_discovery_check_kubernetes,
)
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.fluxcd import FluxcdCheck

from .common import EXPECTED_METRICS


def assert_metrics(aggregator):
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
def test_e2e_discovery(aggregator, datadog_agent):
    # Kubelet Autodiscovery is expected to find all four flux-system controller pods exercised by
    # the non-discovery E2E test above (source, helm, kustomize, notification-controller).
    run_discovery_check_kubernetes(aggregator, datadog_agent, discovery_min_instances=4)
    assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(aggregator, datadog_agent):
    assert_all_discovery_candidates_stable_kubernetes(
        FluxcdCheck,
        aggregator,
        datadog_agent,
        namespace='flux-system',
        pod_selector='app=source-controller',
    )
