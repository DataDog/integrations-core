import pytest
import os
import subprocess
import logging
import requests
import time

from datadog_checks.kong import Kong
from datadog_checks.utils.common import get_docker_hostname

log = logging.getLogger('test_kong')

HERE = os.path.dirname(os.path.abspath(__file__))

CHECK_NAME = 'kong'
HOST = get_docker_hostname()
PORT = 8001

STATUS_URL = 'http://{0}:{1}/status/'.format(HOST, PORT)

CONFIG_STUBS = [
    {
        'kong_status_url': STATUS_URL,
        'tags': ['first_instance']
    },
    {
        'kong_status_url': STATUS_URL,
        'tags': ['second_instance']
    }
]

BAD_CONFIG = {
    'kong_status_url': 'http://localhost:1111/status/'
}

GAUGES = [
    'kong.total_requests',
    'kong.connections_active',
    'kong.connections_waiting',
    'kong.connections_reading',
    'kong.connections_accepted',
    'kong.connections_writing',
    'kong.connections_handled',
]

DATABASES = [
    'reachable'
]


def wait_for_cluster():
    for _ in xrange(0, 100):
        res = None
        try:
            res = requests.get(STATUS_URL)
            res.raise_for_status()
            return True
        except Exception as e:
            log.debug("exception: {0} res: {1}".format(e, res))
            time.sleep(2)

    return False


@pytest.fixture(scope="session", autouse=True)
def kong_cluster():
    """
    Start a kong cluster
    """
    compose_directory = os.path.join(HERE, 'compose')
    os.environ['COMPOSE_DIRECTORY_PATH'] = compose_directory

    args = [
        "docker-compose",
        "-f", os.path.join(compose_directory, 'docker-compose.yml')
    ]
    subprocess.check_call(args + ["up", "-d"])
    if not wait_for_cluster():
        subprocess.check_call(args + ["down"])
        raise Exception("Kong cluster boot timed out!")
    yield
    subprocess.check_call(args + ["down"])


@pytest.fixture
def check():
    return Kong(CHECK_NAME, {}, {})


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def test_check(aggregator, check):
    for stub in CONFIG_STUBS:
        check.check(stub)
        expected_tags = stub['tags']

        for mname in GAUGES:
            aggregator.assert_metric(mname, tags=expected_tags, count=1)

        aggregator.assert_metric('kong.table.count', len(DATABASES), tags=expected_tags, count=1)

        for name in DATABASES:
            tags = expected_tags + ['table:{}'.format(name)]
            aggregator.assert_metric('kong.table.items', tags=tags, count=1)

        aggregator.assert_service_check('kong.can_connect', status=Kong.OK,
                                        tags=['kong_host:localhost', 'kong_port:8001'] + expected_tags, count=1)

        aggregator.all_metrics_asserted()


def test_connection_failure(aggregator, check):
    with pytest.raises(Exception):
        check.check(BAD_CONFIG)
    aggregator.assert_service_check('kong.can_connect', status=Kong.CRITICAL,
                                    tags=['kong_host:localhost', 'kong_port:1111'], count=1)

    aggregator.all_metrics_asserted()
