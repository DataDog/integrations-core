# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.kube_discovery import run_discovery_check_kubernetes
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    API_SERVER_METRICS,
    APP_CONTROLLER_METRICS,
    APPSET_CONTROLLER_METRICS,
    E2E_NOT_EXPOSED_METRICS,
    NOT_EXPOSED_METRICS,
    NOTIFICATIONS_CONTROLLER_METRICS,
    REPO_SERVER_METRICS,
)


@pytest.mark.e2e
def test_e2e_openmetrics_v1(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    metrics = (
        APP_CONTROLLER_METRICS
        + APPSET_CONTROLLER_METRICS
        + API_SERVER_METRICS
        + REPO_SERVER_METRICS
        + NOTIFICATIONS_CONTROLLER_METRICS
    )
    not_exposed_metrics = E2E_NOT_EXPOSED_METRICS + NOT_EXPOSED_METRICS

    aggregator.assert_service_check('argocd.api_server.openmetrics.health', ServiceCheck.OK, count=2)
    aggregator.assert_service_check('argocd.repo_server.openmetrics.health', ServiceCheck.OK, count=2)
    aggregator.assert_service_check('argocd.app_controller.openmetrics.health', ServiceCheck.OK, count=2)
    aggregator.assert_service_check('argocd.appset_controller.openmetrics.health', ServiceCheck.OK, count=2)
    aggregator.assert_service_check('argocd.notifications_controller.openmetrics.health', ServiceCheck.OK, count=2)
    for metric in metrics:
        if metric in not_exposed_metrics:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_discovery(aggregator: Any, datadog_agent: Any) -> None:
    aggregator = run_discovery_check_kubernetes(
        aggregator,
        datadog_agent,
        check_rate=True,
        # The fixture has 5 runnable Argo CD roles. The helper waits for raw resolved
        # discovery configs, before the collector removes MetricsExcluded configs. The
        # repo-server `copyutil` init container shares the pod-level kube_app_name tag
        # with the main repo-server container, so it resolves one extra candidate that
        # the collector then drops because metrics collection excludes non-running
        # containers.
        discovery_min_instances=6,
        discovery_timeout=60,
    )
    metrics = (
        APP_CONTROLLER_METRICS
        + APPSET_CONTROLLER_METRICS
        + API_SERVER_METRICS
        + REPO_SERVER_METRICS
        + NOTIFICATIONS_CONTROLLER_METRICS
    )
    not_exposed_metrics = E2E_NOT_EXPOSED_METRICS + NOT_EXPOSED_METRICS

    aggregator.assert_service_check('argocd.api_server.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_service_check('argocd.repo_server.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_service_check('argocd.app_controller.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_service_check('argocd.appset_controller.openmetrics.health', ServiceCheck.OK)
    aggregator.assert_service_check('argocd.notifications_controller.openmetrics.health', ServiceCheck.OK)
    for metric in metrics:
        if metric in not_exposed_metrics:
            aggregator.assert_metric(metric, at_least=0)
        else:
            aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
