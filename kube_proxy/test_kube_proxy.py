# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import mock
from nose.plugins.attrib import attr

# 3p

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
    'namespace': 'kubeproxy',
    'metrics': [
        {'kubeproxy_sync_proxy_rules_latency_microseconds': 'sync_rules.latency'},
        {'process_cpu_seconds_total': 'cpu.time'},
        {'process_resident_memory_bytes': 'mem.resident'},
        {'process_virtual_memory_bytes': 'mem.virtual'},
        {'rest_client_requests_total': 'client.http.requests'}
    ],
    'send_histograms_buckets': True
}


# NOTE: Feel free to declare multiple test classes if needed

@attr(requires='kube_proxy')
class TestKube_proxy(AgentCheckTest):
    """Basic Test for kube_proxy integration."""
    CHECK_NAME = 'kube_proxy'
    NAMESPACE = 'kubeproxy'
    METRICS_COMMON = [
        NAMESPACE + '.cpu.time',
        NAMESPACE + '.mem.resident',
        NAMESPACE + '.mem.virtual',
        NAMESPACE + '.client.http.requests'
    ]
    METRICS_IPTABLES = [
        NAMESPACE + '.sync_rules.latency.count',
        NAMESPACE + '.sync_rules.latency.sum'
    ]

    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test_check_iptables(self, mock_poll):
        """
        Testing Kube_proxy in iptables mode.
        """
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'metrics_iptables.txt')
        with open(f_name, 'r') as f:
            mock_poll.return_value = MockResponse(f.read(), 'text/plain')

        self.run_check({'instances': [instance]})
        for metric in self.METRICS_COMMON:
            self.assertMetric(metric)
        for metric in self.METRICS_IPTABLES:
            self.assertMetric(metric)

        self.coverage_report()


    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test_check_userspace(self, mock_poll):
        """
        Testing Kube_proxy in userspace mode.
        """
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'metrics_userspace.txt')
        with open(f_name, 'r') as f:
            mock_poll.return_value = MockResponse(f.read(), 'text/plain')

        self.run_check({'instances': [instance]})
        for metric in self.METRICS_COMMON:
            self.assertMetric(metric)

        self.coverage_report()
