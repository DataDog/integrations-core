# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, get_docker_hostname
from datadog_checks.statsd.statsd import StatsCheck, SERVICE_CHECK_NAME_HEALTH, SERVICE_CHECK_NAME


CHECK_NAME = 'statsd'
HOST = get_docker_hostname()
PORT = 8126
HERE = os.path.dirname(os.path.abspath(__file__))
URL = "http://{}:{}".format(HOST, PORT)

METRICS = [
    'statsd.graphite.flush_length',
    'statsd.messages.last_msg_seen',
    'statsd.counters.count',
    'statsd.graphite.last_exception',
    'statsd.gauges.count',
    'statsd.messages.bad_lines_seen',
    'statsd.graphite.flush_time',
    'statsd.graphite.last_flush',
    'statsd.uptime',
    'statsd.timers.count'
]


@pytest.fixture
def get_instance():
    return {
        'host': HOST,
        'port': PORT,
    }


@pytest.fixture(scope='session', autouse=True)
def spin_up_statsd():
    with docker_run(
        compose_file=os.path.join(HERE, 'compose', 'statsd.yaml'),
        endpoints=URL
    ):
        yield


def test_simple_run(aggregator, get_instance):
    stats_check = StatsCheck(CHECK_NAME, {}, {})
    stats_check.check(get_instance)
    expected_tags = ["host:{}".format(HOST), "port:{}".format(PORT)]
    for mname in METRICS:
        aggregator.assert_metric(mname, count=1, tags=expected_tags)

    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=stats_check.OK, count=1, tags=expected_tags)
    aggregator.assert_service_check(SERVICE_CHECK_NAME_HEALTH, status=stats_check.OK, count=1, tags=expected_tags)
    aggregator.assert_all_metrics_covered()
