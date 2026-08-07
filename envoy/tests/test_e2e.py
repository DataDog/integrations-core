# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy import Envoy

from .common import (
    ADAPTIVE_CONCURRENCY_PROMETHEUS_METRICS,
    CONNECTION_LIMIT_METRICS,
    DEFAULT_INSTANCE,
    FLAKY_METRICS,
    LOCAL_RATE_LIMIT_METRICS,
    PROMETHEUS_METRICS,
    TLS_INSPECTOR_METRICS,
    requires_new_environment,
)

pytestmark = [requires_new_environment]


def assert_prometheus_metrics(aggregator: AggregatorStub) -> None:
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


@pytest.mark.e2e
def test_e2e(dd_agent_check: Callable[..., AggregatorStub], exercise_envoy: None) -> None:
    aggregator = dd_agent_check(DEFAULT_INSTANCE, rate=True)

    assert_prometheus_metrics(aggregator)
    aggregator.assert_service_check(
        'envoy.openmetrics.health', Envoy.OK, tags=['endpoint:{}'.format(DEFAULT_INSTANCE['openmetrics_endpoint'])]
    )


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery: Callable[..., AggregatorStub], exercise_envoy: None) -> None:
    aggregator = dd_agent_check_discovery(rate=True)

    assert_prometheus_metrics(aggregator)
    # discovery can't know the endpoint ahead of time, and Autodiscovery-injected
    # container tags (docker_image, image_id, etc.) would break an exact tag match,
    # so the endpoint tag isn't asserted here, unlike in test_e2e above.
    aggregator.assert_service_check('envoy.openmetrics.health', Envoy.OK)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check: Callable[..., AggregatorStub]) -> None:
    assert_all_discovery_candidates_stable(dd_agent_check, Envoy, compose_service='front-envoy')
