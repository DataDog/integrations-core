# (C) Datadog, Inc. 2010-2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import mock
from nose.plugins.attrib import attr

# 3p
from prometheus_client import generate_latest, CollectorRegistry, Gauge

# project
from tests.checks.common import AgentCheckTest

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

    def close(self):
        pass

instance = {
    'prometheus_url': 'http://localhost:10249/metrics',
    'namespace': 'prometheus',
    'metrics': [
        {'metric1': 'renamed.metric1'},
        'metric2'
    ],
    'send_histograms_buckets': True
}

@attr(requires='prometheus')
class TestPrometheus(AgentCheckTest):
    """Basic Test for prometheus integration."""
    CHECK_NAME = 'prometheus'
    NAMESPACE = 'prometheus'
    METRICS_COMMON = [
        NAMESPACE + '.renamed.metric1',
        NAMESPACE + '.metric2'
    ]

    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test_check(self, mock_poll):
        """
        Testing Kube_proxy in userspace mode.
        """
        registry = CollectorRegistry()
        g1 = Gauge('metric1', 'processor usage', ['matched_label', 'node', 'flavor'], registry=registry)
        g1.labels(matched_label="foobar", node="localhost", flavor="test").set(99.9)
        g2 = Gauge('metric2', 'memory usage', ['matched_label', 'node', 'timestamp'], registry=registry)
        g2.labels(matched_label="foobar", node="localhost", timestamp="123").set(12.2)

        mock_poll.return_value = MockResponse(generate_latest(registry), 'text/plain')

        self.run_check({'instances': [instance]})
        for metric in self.METRICS_COMMON:
            self.assertMetric(metric)

        self.coverage_report()
