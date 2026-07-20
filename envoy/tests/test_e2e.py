# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.utils.discovery import Port, Service
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy import Envoy

from .common import (
    ADAPTIVE_CONCURRENCY_PROMETHEUS_METRICS,
    CONNECTION_LIMIT_METRICS,
    DEFAULT_INSTANCE,
    FLAKY_METRICS,
    HOST,
    LOCAL_RATE_LIMIT_METRICS,
    PORT,
    PROMETHEUS_METRICS,
    TLS_INSPECTOR_METRICS,
    requires_new_environment,
)

pytestmark = [requires_new_environment]


@pytest.mark.e2e
def test_e2e(dd_agent_check, exercise_envoy):
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)

    for metric in (
        PROMETHEUS_METRICS
        + LOCAL_RATE_LIMIT_METRICS
        + CONNECTION_LIMIT_METRICS
        + TLS_INSPECTOR_METRICS
        + ADAPTIVE_CONCURRENCY_PROMETHEUS_METRICS
    ):
        formatted_metric = "envoy.{}".format(metric)
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(formatted_metric, at_least=0)
            continue
        aggregator.assert_metric(formatted_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check(
        'envoy.openmetrics.health', Envoy.OK, tags=['endpoint:{}'.format(DEFAULT_INSTANCE['openmetrics_endpoint'])]
    )


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery, exercise_envoy):
    aggregator = dd_agent_check_discovery(rate=True)

    for metric in (
        PROMETHEUS_METRICS
        + LOCAL_RATE_LIMIT_METRICS
        + CONNECTION_LIMIT_METRICS
        + TLS_INSPECTOR_METRICS
        + ADAPTIVE_CONCURRENCY_PROMETHEUS_METRICS
    ):
        formatted_metric = "envoy.{}".format(metric)
        if metric in FLAKY_METRICS:
            aggregator.assert_metric(formatted_metric, at_least=0)
            continue
        aggregator.assert_metric(formatted_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    # discovery can't know the endpoint ahead of time, and Autodiscovery-injected
    # container tags (docker_image, image_id, etc.) would break an exact tag match,
    # so the endpoint tag isn't asserted here, unlike in test_e2e above.
    aggregator.assert_service_check('envoy.openmetrics.health', Envoy.OK)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, Envoy, compose_service='front-envoy')


@pytest.mark.e2e
def test_e2e_discovery_stats_url_candidate(dd_agent_check):
    # assert_all_discovery_candidates_stable only checks that the container stays up and logs
    # cleanly; it doesn't verify the legacy stats_url candidate actually collects metrics. Run
    # it directly here to confirm the admin-port filtering in discovery_overrides.py still
    # produces a working legacy instance.
    service = Service(id='envoy', host=HOST, ports=(Port(number=int(PORT)),))
    stats_url_candidates = [
        candidate for candidate in Envoy.generate_configs(service) if 'stats_url' in candidate['instances'][0]
    ]
    assert len(stats_url_candidates) == 1
    instance = stats_url_candidates[0]['instances'][0]
    assert 'openmetrics_endpoint' not in instance

    aggregator = dd_agent_check(stats_url_candidates[0], rate=True)

    aggregator.assert_metric('envoy.server.uptime')
    aggregator.assert_service_check('envoy.can_connect', Envoy.OK)
