# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
import urllib2
import os
import subprocess
import time

import pytest

from datadog_checks.lighttpd import Lighttpd
from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
STATUS_URL = 'http://{}:9449/server-status'.format(HOST)
CHECK_GAUGES = [
    'lighttpd.net.bytes',
    'lighttpd.net.bytes_per_s',
    'lighttpd.net.hits',
    'lighttpd.net.request_per_s',
    'lighttpd.performance.busy_servers',
    'lighttpd.performance.idle_server',
    'lighttpd.performance.uptime',
]


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture
def instance():
    return {
        'lighttpd_status_url': STATUS_URL,
        'tags': ['instance:first'],
        'user': 'username',
        'password': 'password',
        'auth_type': 'digest',
    }


@pytest.fixture(scope="session")
def lighttpd():
    """
    Start a lighttpd server instance.
    """
    subprocess.check_call(["docker-compose", "-f", os.path.join(HERE, 'docker', 'docker-compose.yaml'), "up", "-d"])
    attempts = 0
    while True:
        if attempts > 10:
            raise Exception("lighttpd boot timed out!")

        try:
            urllib2.urlopen(STATUS_URL).read()
        except urllib2.HTTPError:
            # endpoint is secured, we do expect 401
            break
        except urllib2.URLError:
            attempts += 1
            time.sleep(1)

    yield

    subprocess.check_call(["docker-compose", "-f", os.path.join(HERE, 'docker', 'docker-compose.yaml'), "down"])


def test_lighttpd(aggregator, instance, lighttpd):
    """
    """
    tags = [
        'host:{}'.format(HOST),
        'port:9449',
        'instance:first'
    ]
    check = Lighttpd("lighttpd", {}, {})
    check.check(instance)

    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Lighttpd.OK, tags=tags)

    for gauge in CHECK_GAUGES:
        aggregator.assert_metric(gauge, tags=['instance:first'], count=1)
    aggregator.assert_all_metrics_covered()


def test_service_check_ko(instance, aggregator):
    """
    """
    instance['lighttpd_status_url'] = 'http://localhost:1337'
    tags = [
        'host:localhost',
        'port:1337',
        'instance:first'
    ]
    check = Lighttpd("lighttpd", {}, {})
    with pytest.raises(Exception):
        check.check(instance)
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=Lighttpd.CRITICAL, tags=tags)
