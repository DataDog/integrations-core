# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import pytest

from datadog_checks.argocd.resources_constants import (
    GENRESOURCES_API_UP_METRIC,
    GENRESOURCES_STREAM_EVENTS_METRIC,
    GENRESOURCES_STREAM_UP_METRIC,
)
from datadog_checks.base.constants import ServiceCheck
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
def test_e2e_genresources(dd_agent_check, genresources_instance):
    aggregator = dd_agent_check(genresources_instance, rate=True)

    # REST collection reachable + authenticated for each resource type.
    for resource_type in ('argocd_application', 'argocd_cluster', 'argocd_repository'):
        aggregator.assert_metric(GENRESOURCES_API_UP_METRIC, value=1, tags=['resource_type:{}'.format(resource_type)])

    # The application watch stream ran; on connect it replays current Applications (our sample app).
    aggregator.assert_metric(GENRESOURCES_STREAM_UP_METRIC)
    aggregator.assert_metric(GENRESOURCES_STREAM_EVENTS_METRIC, at_least=1)

    # collect_openmetrics is disabled -> the OpenMetrics scrape does not run.
    aggregator.assert_metric('argocd.app_controller.app.info', count=0)
