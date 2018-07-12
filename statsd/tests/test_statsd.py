# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import sys
import time
import pytest
import subprocess
from datadog_checks.utils.common import get_docker_hostname
from datadog_checks.statsd import StatsCheck

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

SERVICE_CHECKS = [
    'statsd.is_up',
    'statsd.can_connect'
]


@pytest.fixture
def get_instance():
    return {
        'host': HOST,
        'port': PORT,
    }


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope="session")
def spin_up_statsd():
    env = os.environ
    args = [
        'docker-compose', '-f', os.path.join(HERE, 'compose', 'statsd.yaml')
    ]
    subprocess.check_call(args + ["up", "-d"], env=env)
    sys.stderr.write("Waiting for Statsd instance to boot")
    for _ in xrange(2):
        try:
            res = requests.get(URL)
            res.raise_for_status()
        except Exception:
            time.sleep(1)
    yield
    subprocess.check_call(args + ["down"], env=env)


def test_simple_run(aggregator, spin_up_statsd, get_instance):
    stats_check = StatsCheck(CHECK_NAME, {}, {})
    stats_check.check(get_instance)
    for mname in METRICS:
        aggregator.assert_metric(mname)
    for sc in SERVICE_CHECKS:
        aggregator.assert_service_check(sc)
