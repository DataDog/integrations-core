# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.traffic_server import TrafficServerCheck

from .common import EXPECTED_METRICS


def assert_metrics(aggregator, tags=None):
    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK)

    for metric_name in EXPECTED_METRICS:
        aggregator.assert_metric(metric_name, at_least=1)
        for tag in tags or []:
            aggregator.assert_metric_has_tag(metric_name, tag)


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance, aggregator):
    dd_agent_check(instance, rate=True)
    traffic_server_tags = instance.get('tags')

    assert_metrics(aggregator, tags=traffic_server_tags)


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery(rate=True)

    assert_metrics(aggregator)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, TrafficServerCheck, compose_service='trafficserver')
