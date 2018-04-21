# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

import mock
import pytest
from datadog_checks.utils.common import get_docker_hostname

from datadog_checks.envoy import Envoy
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

HERE = os.path.dirname(os.path.abspath(__file__))
DOCKER_DIR = os.path.join(HERE, 'docker')
FIXTURE_DIR = os.path.join(HERE, 'fixtures')


class MockResponse:
    def __init__(self, content, status_code):
        self.content = content
        self.status_code = status_code


@lru_cache(maxsize=None)
def response(kind):
    if kind == 'bad':
        return MockResponse(b'', 500)
    else:
        file_path = os.path.join(FIXTURE_DIR, kind)
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                return MockResponse(f.read(), 200)
        else:
            raise IOError('File `{}` does not exist.'.format(file_path))


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


@pytest.fixture(scope='session', autouse=True)
def spin_up_envoy():
    env = dict(os.environ)
    env['ENVOY_VERSION'] = 'latest'
    flavor = os.getenv('FLAVOR', 'default')
    base_command = [
        'docker-compose', '-f', os.path.join(DOCKER_DIR, flavor, 'docker-compose.yaml')
    ]
    subprocess.check_call(base_command + ['up', '-d', '--build'], env=env)
    yield
    subprocess.check_call(base_command + ['down'], env=env)


class TestEnvoy:
    CHECK_NAME = 'envoy'
    INSTANCES = {
        'main': {
            'stats_url': 'http://{}:8001/stats'.format(get_docker_hostname()),
        },
    }

    def test_success(self, aggregator):
        instance = self.INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])
        c.check(instance)

        metrics_collected = 0
        for metric in METRICS.keys():
            metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

        assert metrics_collected >= 250

    def test_success_fixture(self, aggregator):
        instance = self.INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        metrics_collected = 0
        for metric in METRICS.keys():
            metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

        num_metrics = len(response('multiple_services').content.decode().splitlines())
        num_metrics -= sum(c.unknown_metrics.values()) + sum(c.unknown_tags.values())
        assert 4150 <= metrics_collected == num_metrics

    def test_service_check(self, aggregator):
        instance = self.INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        assert aggregator.service_checks(Envoy.SERVICE_CHECK_NAME)[0].status == Envoy.OK

    def test_unknown(self):
        instance = self.INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('unknown_metrics')):
            c.check(instance)

        assert sum(c.unknown_metrics.values()) == 5
