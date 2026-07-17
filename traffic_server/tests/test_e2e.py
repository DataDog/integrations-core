# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.traffic_server import TrafficServerCheck

from .common import EXPECTED_METRICS

DISCOVERY_METRICS_PATTERN = re.compile(
    '|'.join(
        (
            'traffic_server.node.*',
            'traffic_server.process.http.code.*',
            'traffic_server.process.http(s|2)?.*current',
            'traffic_server.process.http(s|2)?.*_requests',
            'traffic_server.process.http(s|2)?.*_connections',
            'traffic_server.process.http.transaction_.*',
            'traffic_server.process.hostdb.*',
            'traffic_server.process.dns.*',
            'traffic_server.process.traffic_server.memory.rss',
            'traffic_server.process.eventloop.*',
            'traffic_server.process.ssl.user_agent_session.*',
            'traffic_server.process.ssl.ssl_error.*',
            'traffic_server.process.ssl.user_agent_sessions',
            'traffic_server.process.cache.total.*',
            'traffic_server.process.cache.volume.dir.*',
            'traffic_server.process.cache.volume.percent_full',
            'traffic_server.process.cache.volume.bytes.*',
            'traffic_server.process.cache.volume.ram_cache.*',
        )
    )
)
DISCOVERY_EXPECTED_METRICS = tuple(metric for metric in EXPECTED_METRICS if DISCOVERY_METRICS_PATTERN.search(metric))


def assert_metrics(aggregator, *, expected_metrics=EXPECTED_METRICS, tags=None):
    aggregator.assert_service_check('traffic_server.can_connect', TrafficServerCheck.OK)

    for metric_name in expected_metrics:
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

    assert_metrics(aggregator, expected_metrics=DISCOVERY_EXPECTED_METRICS)


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, TrafficServerCheck, compose_service='trafficserver')
