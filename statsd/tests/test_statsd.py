# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname
from datadog_checks.statsd.statsd import SERVICE_CHECK_NAME, SERVICE_CHECK_NAME_HEALTH, StatsCheck

log = logging.getLogger(__file__)

CHECK_NAME = 'statsd'
HOST = get_docker_hostname()
PORT = 8126
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)

METRICS = [
    'statsd.uptime',
    'statsd.timers.count',
    'statsd.counters.count',
    'statsd.gauges.count',
    'statsd.messages.last_msg_seen',
    'statsd.graphite.last_exception',
    'statsd.messages.bad_lines_seen',
    'statsd.graphite.flush_time',
    'statsd.graphite.last_flush',
    'statsd.graphite.flush_length',
]

DEFAULT_INSTANCE = {'host': HOST, 'port': PORT}


@pytest.fixture
def instance():
    return DEFAULT_INSTANCE


@pytest.fixture(scope='session')
def dd_environment():
    with docker_run(compose_file=os.path.join(HERE, 'compose', 'statsd.yaml'), log_patterns=['server is up']):
        yield DEFAULT_INSTANCE


@pytest.mark.usefixtures("dd_environment")
def test_simple_run(aggregator, instance):
    stats_check = StatsCheck(CHECK_NAME, {}, {})
    stats_check.check(instance)
    expected_tags = ["host:{}".format(HOST), "port:{}".format(PORT)]

    for mname in METRICS:
        aggregator.assert_metric(mname, count=1, tags=expected_tags)

    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=stats_check.OK, count=1, tags=expected_tags)
    aggregator.assert_service_check(SERVICE_CHECK_NAME_HEALTH, status=stats_check.OK, count=1, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
