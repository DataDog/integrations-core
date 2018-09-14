# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import pytest
import logging
import socket
import time
import requests

from datadog_checks.utils.common import get_docker_hostname
from datadog_checks.dev import docker_run
from datadog_checks.twemproxy import Twemproxy


log = logging.getLogger('test_twemproxy')


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TESTS_HELPER_DIR = os.path.join(ROOT, 'datadog_checks_tests_helper')
HOST = get_docker_hostname()
PORT = 6222

GLOBAL_STATS = set([
    'curr_connections',
    'total_connections'
])

POOL_STATS = set([
    'client_eof',
    'client_err',
    'client_connections',
    'server_ejects',
    'forward_error',
    'fragments'
])

SERVER_STATS = set([
    'in_queue',
    'out_queue',
    'in_queue_bytes',
    'out_queue_bytes',
    'server_connections',
    'server_timedout',
    'server_err',
    'server_eof',
    'requests',
    'request_bytes',
    'responses',
    'response_bytes',
])

SC_TAGS = ['host:{}'.format(HOST), 'port:{}'.format(PORT), 'optional:tag1']


@pytest.fixture
def check():
    check = Twemproxy('twemproxy', {}, {})
    return check


@pytest.fixture(scope="session")
def spin_up_twemproxy(request):
    """
    Start a cluster with one master, one replica and one unhealthy replica and
    stop it after the tests are done.
    If there's any problem executing docker-compose, let the exception bubble
    up.
    """

    env = {}

    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')

    env['DOCKER_COMPOSE_FILE'] = compose_file
    env['DOCKER_ADDR'] = get_docker_hostname()
    env['WAIT_FOR_IT_SCRIPT_PATH'] = _wait_for_it_script()
    env['SETUP_SCRIPT_PATH'] = os.path.join(HERE, 'compose', 'setup.sh')

    with docker_run(compose_file, env_vars=env):
        if not wait_for_cluster():
            raise Exception("The cluster never came up")
        time.sleep(15)
        yield


def wait_for_cluster():
    for _ in xrange(0, 10):
        res = None
        try:
            socket.getaddrinfo(HOST, PORT, 0, 0, socket.IPPROTO_TCP)
            return True
        except Exception as e:
            log.debug("exception: {0} res: {1}".format(e, res))
            time.sleep(5)

    return False


def _wait_for_it_script():
    """
    FIXME: relying on the filesystem layout is a bad idea, the testing helper
    should expose its path through the api instead
    """
    dir = os.path.join(TESTS_HELPER_DIR, 'scripts', 'wait-for-it.sh')
    return os.path.abspath(dir)


@pytest.fixture
def setup_request():
    """
    A request needs to be made in order for some of the data to be seeded
    """
    url = "http://{}:{}".format(HOST, PORT)
    try:
        requests.get(url)
    except Exception:
        pass


def test_check(check, spin_up_twemproxy, setup_request, aggregator):
    instance = {
        'host': get_docker_hostname(),
        'port': 6222,
        'tags': ['optional:tag1']
    }

    check.check(instance)

    for stat in GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), at_least=0)
    for stat in POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)
    for stat in SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)

    # Test service check
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK,
                                    tags=SC_TAGS, count=1)

    # Raises when COVERAGE=true and coverage < 100%
    aggregator.assert_all_metrics_covered()
