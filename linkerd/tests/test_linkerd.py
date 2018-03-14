# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.linkerd import LinkerdCheck

# 3p
import mock
import pytest

PROMETHEUS_URL = 'http://127.0.0.1:19990/admin/datadog/metrics'

MOCK_INSTANCE = {
    'name': 'linkerd',
    'prometheus_url': PROMETHEUS_URL,
    #'prometheus_metrics_prefix': 'dd_linkerd_',
    'metrics': [{'jvm:start_time': 'jvm.start_time'}],
    'type_overrides': {'jvm:start_time': 'gauge'},
}

CHECK_NAME = METRIC_PREFIX = 'linkerd'

class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type):
        if isinstance(content, list):
            self.content = content
        else:
            self.content = [content]
        self.headers = {'Content-Type': content_type}

    def iter_lines(self, **_):
        content = self.content.pop(0)
        for elt in content.split("\n"):
            yield elt

    def close(self):
        pass

@pytest.fixture
def linkerd_fixture():
    metrics_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'linkerd.txt')
    responses = []
    with open(metrics_file_path, 'rb') as f:
        responses.append(f.read())

    p = mock.patch('datadog_checks.checks.prometheus.Scraper.poll',
                   return_value=MockResponse(responses, 'text/plain'),
                   __name__="poll")
    yield p.start()
    p.stop()

@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator

def test_linkerd(aggregator, linkerd_fixture):
    """
    Test the full check
    """
    c = LinkerdCheck('linkerd', None, {}, [MOCK_INSTANCE])
    c.check(MOCK_INSTANCE)

    metrics = ['linkerd.jvm.start_time']
    for metric in metrics:
        aggregator.assert_metric(metric)
