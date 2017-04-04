# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import mock
import os

# project
from tests.checks.common import AgentCheckTest
from utils.kubernetes import NAMESPACE


class TestKubernetesState(AgentCheckTest):

    CHECK_NAME = 'kubernetes_state'

    METRICS = [
        NAMESPACE + '.node.cpu_capacity',
        NAMESPACE + '.node.memory_capacity',
        NAMESPACE + '.node.pods_capacity',
        NAMESPACE + '.node.cpu_allocatable',
        NAMESPACE + '.node.memory_allocatable',
        NAMESPACE + '.node.pods_allocatable',
        NAMESPACE + '.node.status',
        NAMESPACE + '.container.cpu_requested',
        NAMESPACE + '.container.memory_requested',
        NAMESPACE + '.container.cpu_limit',
        NAMESPACE + '.container.memory_limit',
        NAMESPACE + '.container.restarts',
        NAMESPACE + '.deployment.replicas_available',
        NAMESPACE + '.deployment.replicas_unavailable',
        NAMESPACE + '.deployment.replicas_desired',
        NAMESPACE + '.deployment.replicas_updated',
    ]

    ZERO_METRICS = [
        NAMESPACE + '.deployment.replicas_unavailable',
    ]

    def test__get_kube_state(self):
        headers = {
            'accept': 'application/vnd.google.protobuf; proto=io.prometheus.client.MetricFamily; encoding=delimited',
            'accept-encoding': 'gzip',
        }
        url = 'https://example.com'

        self.load_check({'instances': [{'host': 'foo'}]})
        with mock.patch('{}.requests'.format(self.check.__module__)) as r:
            self.check._get_kube_state(url)
            r.get.assert_called_once_with(url, headers=headers)

    def test_kube_state(self):
        mocked = mock.MagicMock()
        mocks = {
            '_perform_kubelet_checks': mock.MagicMock(),
            '_update_metrics': mock.MagicMock(),
            '_update_kube_state_metrics': mocked,
        }
        config = {'instances': [{'host': 'foo', 'kube_state_url': 'https://example.com:12345'}]}
        self.run_check(config, force_reload=True, mocks=mocks)
        mocked.assert_called_once()

    def assertMetricNotAllZeros(self, metric_name):
        for mname, ts, val, mdata in self.metrics:
            if mname == metric_name:
                if val != 0:
                    return True
        raise AssertionError("All metrics named %s have 0 value." % metric_name)

    def test__update_kube_state_metrics(self):
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'fixtures', 'prometheus', 'protobuf.bin')
        mocked = mock.MagicMock()
        with open(f_name, 'rb') as f:
            mocked.return_value = f.read()

        mocks = {
            '_perform_kubelet_checks': mock.MagicMock(),
            '_update_metrics': mock.MagicMock(),
            'kubeutil': mock.MagicMock(),
            '_get_kube_state': mocked,
        }

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
            }]
        }

        self.run_check(config, mocks=mocks)

        self.assertServiceCheck(NAMESPACE + '.node.ready', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.out_of_disk', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.pod.phase.running', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.pod.phase.failed', self.check.CRITICAL)
        # TODO: uncomment when any of these are in the test protobuf.bin
        # self.assertServiceCheck(NAMESPACE + '.pod.phase.pending', self.check.WARNING)
        # self.assertServiceCheck(NAMESPACE + '.pod.phase.succeeded', self.check.OK)
        # self.assertServiceCheck(NAMESPACE + '.pod.phase.unknown', self.check.UNKNOWN)

        for metric in self.METRICS:
            self.assertMetric(metric)
            if metric not in self.ZERO_METRICS:
                self.assertMetricNotAllZeros(metric)
