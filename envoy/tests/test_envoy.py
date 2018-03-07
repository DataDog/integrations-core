# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
try:
    from functools import lru_cache
except ImportError:
    from backports.functools_lru_cache import lru_cache

import mock
import pytest
from datadog_checks.stubs import aggregator as _aggregator

from datadog_checks.envoy import Envoy
from datadog_checks.envoy.metrics import METRIC_PREFIX, METRICS

FIXTURE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures')


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
    _aggregator.reset()
    return _aggregator


class TestEnvoy:
    CHECK_NAME = 'envoy'
    INSTANCES = {
        'main': {
            'stats_url': 'http://localhost:80/stats',
        },
    }

    def test_success(self, aggregator):
        instance = self.INSTANCES['main']
        c = Envoy(self.CHECK_NAME, None, {}, [instance])

        with mock.patch('requests.get', return_value=response('multiple_services')):
            c.check(instance)

        metrics_collected = 0
        for metric in METRICS.keys():
            metrics_collected += len(aggregator.metrics(METRIC_PREFIX + metric))

        # The 244 is how many metrics are collected from our
        # particular example fixture in the first release.
        assert metrics_collected >= 244
