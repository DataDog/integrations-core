# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import mock
import pytest
import requests
import subprocess

# project
from datadog_checks.coredns import CoreDNSCheck
from datadog_checks.utils.common import get_docker_hostname

instance = {
    'prometheus_endpoint': 'http://localhost:9153/metrics',
}

HERE = os.path.dirname(os.path.abspath(__file__))

COREDNS_HOST = get_docker_hostname()
COREDNS_PORT = '9153'

DOCKER_COMPOSE_ARGS = [
    "docker-compose",
    "-f", os.path.join(HERE, 'docker', 'docker-compose.yaml')
]

DIG_ARGS = [
    "dig",
    "google.com",
    "@127.0.0.1",
    "-p",
    "54"
]

class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type):
        self.content = content
        self.headers = {'Content-Type': content_type}

    def iter_lines(self, **_):
        for elt in self.content.split("\n"):
            yield elt

    def raise_for_status(self):
        pass

    def close(self):
        pass

@pytest.fixture
def coredns():
    env = os.environ
    env['COREDNS_CONFIG_FOLDER'] = os.path.join(HERE, 'docker', 'coredns')

    start_coredns(env)
    yield
    subprocess.check_call(DOCKER_COMPOSE_ARGS + ["down"], env=env)

def start_coredns(env):
    subprocess.check_call(DOCKER_COMPOSE_ARGS + ["up", "-d"], env=env)

    sys.stderr.write("Waiting for CoreDNS to boot...")

    attempts = 1
    while True:
        if attempts >= 10:
            subprocess.check_call(DOCKER_COMPOSE_ARGS + ["down"], env=env)
            raise Exception("CoreDNS failed to boot...")

        try:
            res = requests.get('http://{}:{}/metrics'.format(COREDNS_HOST, COREDNS_PORT))
            # create some metrics by using dig
            subprocess.check_call(DIG_ARGS, env=env)
            res.raise_for_status
            break
        except Exception:
            attempts += 1
            time.sleep(1)


@pytest.fixture
def dockercheck():
    return CoreDNSCheck('coredns', {}, {}, [])

@pytest.fixture
def dockerinstance():
    return {
        'prometheus_endpoint': 'http://{}:{}/metrics'.format(COREDNS_HOST, COREDNS_PORT),
    }

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator

    aggregator.reset()
    return aggregator


@pytest.fixture
def mock_get():
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    text_data = None
    with open(mesh_file_path, 'rb') as f:
        text_data = f.read()

    p = mock.patch('requests.get', return_value=MockResponse(text_data, 'text/plain; version=0.0.4'), __name__='get')
    yield p.start()
    p.stop()


class TestCoreDNS:
    """Basic Test for coredns integration."""
    CHECK_NAME = 'coredns'
    NAMESPACE = 'coredns'
    METRICS = [
        NAMESPACE + '.request_duration.seconds.sum',
        NAMESPACE + '.request_duration.seconds.count',
        NAMESPACE + '.request_size.bytes.sum',
        NAMESPACE + '.request_size.bytes.count',
        NAMESPACE + '.proxy_request_duration.seconds.count',
        NAMESPACE + '.proxy_request_duration.seconds.sum',
        NAMESPACE + '.cache_size.count',
    ]
    COUNT_METRICS = [
        # NAMESPACE + '.response_code_count',
        # NAMESPACE + '.proxy_request_count',
        # NAMESPACE + '.cache_hits_count',
        # NAMESPACE + '.cache_misses_count',
        # NAMESPACE + '.request_count',
        # NAMESPACE + '.request_type_count',
        # NAMESPACE + '.response_code_count.count',
        # NAMESPACE + '.proxy_request_count.count',
        # NAMESPACE + '.cache_hits_count.count',
        # NAMESPACE + '.cache_misses_count.count',
        # NAMESPACE + '.request_count.count',
        # NAMESPACE + '.request_type_count.count',
    ]


    def test_check(self, aggregator, mock_get):
        """
        Testing coredns check.
        """

        check = CoreDNSCheck('coredns', {}, {}, [instance])
        check.check(instance)

        # check that we then get the count metrics also
        check.check(instance)

        for metric in self.METRICS + self.COUNT_METRICS:
            aggregator.assert_metric(metric)

        aggregator.assert_all_metrics_covered()

    def test_connect(dockercheck, dockerinstance, aggregator, coredns):
        """
        Testing that connection will work with instance
        """
        check.check(dockerinstance)
        aggregator.assert_metric("nginx.net.connections", tags=TAGS, count=1)
        extra_tags = ['host:{}'.format(NGINX_HOST), 'port:{}'.format(NGINX_PORT)]
        aggregator.assert_service_check('nginx.can_connect', tags=TAGS+extra_tags)