# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import mock
import os

# project
from tests.checks.common import AgentCheckTest

NAMESPACE = 'kubernetes_state'

class TestKubernetesState(AgentCheckTest):

    CHECK_NAME = 'kubernetes_state'

    METRICS = [
        # nodes
        NAMESPACE + '.node.cpu_capacity',
        NAMESPACE + '.node.memory_capacity',
        NAMESPACE + '.node.pods_capacity',
        NAMESPACE + '.node.cpu_allocatable',
        NAMESPACE + '.node.memory_allocatable',
        NAMESPACE + '.node.pods_allocatable',
        NAMESPACE + '.node.gpu.cards_capacity',
        NAMESPACE + '.node.gpu.cards_allocatable',
        # deployments
        NAMESPACE + '.deployment.replicas',
        NAMESPACE + '.deployment.replicas_available',
        NAMESPACE + '.deployment.replicas_unavailable',
        NAMESPACE + '.deployment.replicas_updated',
        NAMESPACE + '.deployment.replicas_desired',
        NAMESPACE + '.deployment.paused',
        NAMESPACE + '.deployment.rollingupdate.max_unavailable',
        # daemonsets
        NAMESPACE + '.daemonset.scheduled',
        NAMESPACE + '.daemonset.misscheduled',
        NAMESPACE + '.daemonset.desired',
        # hpa
        NAMESPACE + '.hpa.min_replicas',
        NAMESPACE + '.hpa.max_replicas',
        NAMESPACE + '.hpa.desired_replicas',
        NAMESPACE + '.hpa.current_replicas',
        # pods
        NAMESPACE + '.pod.ready',
        NAMESPACE + '.pod.scheduled',
        # containers
        NAMESPACE + '.container.ready',
        NAMESPACE + '.container.running',
        NAMESPACE + '.container.terminated',
        NAMESPACE + '.container.status_report.count.terminated',
        NAMESPACE + '.container.waiting',
        NAMESPACE + '.container.status_report.count.waiting',
        NAMESPACE + '.container.restarts',
        NAMESPACE + '.container.cpu_requested',
        NAMESPACE + '.container.memory_requested',
        NAMESPACE + '.container.cpu_limit',
        NAMESPACE + '.container.memory_limit',
        NAMESPACE + '.container.gpu.request',
        NAMESPACE + '.container.gpu.limit',
        # replicasets
        NAMESPACE + '.replicaset.replicas',
        NAMESPACE + '.replicaset.fully_labeled_replicas',
        NAMESPACE + '.replicaset.replicas_ready',
        NAMESPACE + '.replicaset.replicas_desired',
        # persistentvolume claim
        NAMESPACE + '.persistentvolumeclaim.status',
        # statefulset
        NAMESPACE + '.statefulset.replicas',
        NAMESPACE + '.statefulset.replicas_current',
        NAMESPACE + '.statefulset.replicas_ready',
        NAMESPACE + '.statefulset.replicas_updated',
    ]

    ZERO_METRICS = [
        NAMESPACE + '.deployment.replicas_unavailable',
        NAMESPACE + '.deployment.paused',
        NAMESPACE + '.daemonset.misscheduled',
        NAMESPACE + '.container.terminated',
        NAMESPACE + '.container.waiting',
    ]

    def assertMetricNotAllZeros(self, metric_name):
        for mname, ts, val, mdata in self.metrics:
            if mname == metric_name:
                if val != 0:
                    return True
        raise AssertionError("All metrics named %s have 0 value." % metric_name)

    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test__update_kube_state_metrics(self, mock_poll):
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'fixtures', 'prometheus', 'protobuf.bin')
        with open(f_name, 'rb') as f:
            mock_poll.return_value = ('text/plain', f.read())

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
            }]
        }

        self.run_check(config)

        self.assertServiceCheck(NAMESPACE + '.node.ready', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.out_of_disk', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.memory_pressure', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.network_unavailable', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.disk_pressure', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.OK,tags=['namespace:default','pod:task-pv-pod']) # Running
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.WARNING,tags=['namespace:default','pod:failingtest-f585bbd4-2fsml']) # Pending
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.OK,tags=['namespace:default','pod:hello-1509998340-k4f8q']) # Succeeded
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.CRITICAL,tags=['namespace:default','pod:should-run-once']) # Failed
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.UNKNOWN,tags=['namespace:default','pod:hello-1509998460-tzh8k']) # Unknown

        for metric in self.METRICS:
            self.assertMetric(metric)
            if metric not in self.ZERO_METRICS:
                self.assertMetricNotAllZeros(metric)

        self.assert_resourcequota()

    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test__update_kube_state_metrics_v040(self, mock_poll):
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'fixtures', 'prometheus', 'protobuf.bin')
        with open(f_name, 'rb') as f:
            mock_poll.return_value = ('text/plain', f.read())

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
            }]
        }

        self.run_check(config)

        self.assertServiceCheck(NAMESPACE + '.node.ready', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.out_of_disk', self.check.OK)


        for metric in self.METRICS:
            if not metric.startswith(NAMESPACE + '.hpa'):
                self.assertMetric(metric)

        self.assert_resourcequota()

    def assert_resourcequota(self):
        """ The metric name is created dynamically so we just check some exist. """
        for m in self.metrics:
            if 'kubernetes_state.resourcequota.' in m[0]:
                return True
        return False
