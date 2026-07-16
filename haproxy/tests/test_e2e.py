# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import is_affirmative
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.haproxy import HAProxyCheck

from .common import ENDPOINT_PROMETHEUS, HAPROXY_LEGACY, requires_new_environment

pytestmark = [requires_new_environment, pytest.mark.e2e]


def test_check(dd_agent_check, instancev1, prometheus_metrics):
    aggregator = dd_agent_check(instancev1, rate=True)

    for metric in prometheus_metrics:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()

    exclude_metrics = []
    if not is_affirmative(HAPROXY_LEGACY):
        # These metrics are submitted as counts with Prometheus
        exclude_metrics = [
            'haproxy.backend.bytes.in.total',
            'haproxy.backend.bytes.out.total',
            'haproxy.frontend.bytes.in.total',
            'haproxy.frontend.bytes.out.total',
        ]
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=exclude_metrics)


def test_checkv2(dd_agent_check, instancev2, prometheus_metricsv2):
    aggregator = dd_agent_check(instancev2, rate=True)

    for metric in prometheus_metricsv2:
        aggregator.assert_metric('haproxy.{}'.format(metric))
        aggregator.assert_metric_has_tag('haproxy.{}'.format(metric), tag="endpoint:" + ENDPOINT_PROMETHEUS)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_discovery(dd_agent_check_discovery, prometheus_metricsv2):
    aggregator = dd_agent_check_discovery(rate=True)

    # discovery resolves the container's internal network address, which differs from
    # ENDPOINT_PROMETHEUS's host-mapped one, so the endpoint tag isn't asserted here.
    for metric in prometheus_metricsv2:
        aggregator.assert_metric('haproxy.{}'.format(metric))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, HAProxyCheck)
