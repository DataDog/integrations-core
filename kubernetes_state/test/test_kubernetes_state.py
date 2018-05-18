# (C) Datadog, Inc. 2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import mock
import os

# 3p
from nose.plugins.attrib import attr

# project
from tests.checks.common import AgentCheckTest

NAMESPACE = 'kubernetes_state'

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


@attr(requires='kubernetes_state')
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
        NAMESPACE + '.nodes.by_condition',
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
        NAMESPACE + '.pod.status_phase',
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

    TAGS = {
        NAMESPACE + '.pod.ready': ['node:minikube'],
        NAMESPACE + '.pod.scheduled': ['node:minikube'],
        NAMESPACE + '.nodes.by_condition': [
            'condition:MemoryPressure', 'condition:DiskPressure',
            'condition:OutOfDisk', 'condition:Ready',
            'status:true', 'status:false', 'status:unknown',
        ]
    }

    JOINED_METRICS = {
        NAMESPACE + '.deployment.replicas': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
        NAMESPACE + '.deployment.replicas_available': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
        NAMESPACE + '.deployment.replicas_unavailable': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
        NAMESPACE + '.deployment.replicas_updated': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
        NAMESPACE + '.deployment.replicas_desired': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
        NAMESPACE + '.deployment.paused': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
        NAMESPACE + '.deployment.rollingupdate.max_unavailable': ['label_addonmanager_kubernetes_io_mode:Reconcile','deployment:kube-dns'],
    }

    HOSTNAMES = {
        NAMESPACE + '.pod.ready': 'minikube',
        NAMESPACE + '.pod.scheduled': 'minikube'
    }

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
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'fixtures', 'prometheus', 'prometheus.txt')
        with open(f_name, 'rb') as f:
            mock_poll.return_value = MockResponse(f.read(), 'text/plain')

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
                'tags': ['optional:tag1']
            }]
        }

        # run check twice to have pod/node mapping
        self.run_check_twice(config)

        self.assertServiceCheck(NAMESPACE + '.node.ready', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.out_of_disk', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.memory_pressure', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.network_unavailable', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.disk_pressure', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.OK,
                                tags=['namespace:default', 'pod:task-pv-pod', 'optional:tag1'])  # Running
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.WARNING,
                                tags=['namespace:default', 'pod:failingtest-f585bbd4-2fsml', 'optional:tag1'])  # Pending
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.OK,
                                tags=['namespace:default', 'pod:hello-1509998340-k4f8q', 'optional:tag1'])  # Succeeded
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.CRITICAL,
                                tags=['namespace:default', 'pod:should-run-once', 'optional:tag1'])  # Failed
        self.assertServiceCheck(NAMESPACE + '.pod.phase', self.check.UNKNOWN,
                                tags=['namespace:default', 'pod:hello-1509998460-tzh8k', 'optional:tag1'])  # Unknown

        # Make sure we send counts for all statuses to avoid no-data graphing issues
        self.assertMetric(NAMESPACE + '.nodes.by_condition', tags=['condition:Ready', 'status:true', 'optional:tag1'], value=1)
        self.assertMetric(NAMESPACE + '.nodes.by_condition', tags=['condition:Ready', 'status:false', 'optional:tag1'], value=0)
        self.assertMetric(NAMESPACE + '.nodes.by_condition', tags=['condition:Ready', 'status:unknown', 'optional:tag1'], value=0)

        for metric in self.METRICS:
            self.assertMetric(
                metric,
                hostname=self.HOSTNAMES.get(metric, None)
            )
            tags = self.TAGS.get(metric, None)
            if tags:
                for tag in tags:
                    self.assertMetricTag(metric, tag)
            if metric not in self.ZERO_METRICS:
                self.assertMetricNotAllZeros(metric)

        self.assert_resourcequota()

    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test__update_kube_state_metrics_v040(self, mock_poll):
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'fixtures', 'prometheus', 'prometheus.txt')
        with open(f_name, 'rb') as f:
            mock_poll.return_value = MockResponse(f.read(), 'text/plain')

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
            }]
        }

        # run check twice to have pod/node mapping
        self.run_check_twice(config)

        self.assertServiceCheck(NAMESPACE + '.node.ready', self.check.OK)
        self.assertServiceCheck(NAMESPACE + '.node.out_of_disk', self.check.OK)

        for metric in self.METRICS:
            if not metric.startswith(NAMESPACE + '.hpa'):
                self.assertMetric(metric)

        self.assert_resourcequota()

    @mock.patch('checks.prometheus_check.PrometheusCheck.poll')
    def test__join_custom_labels(self, mock_poll):
        f_name = os.path.join(os.path.dirname(__file__), 'ci', 'fixtures', 'prometheus', 'prometheus.txt')
        with open(f_name, 'rb') as f:
            mock_poll.return_value = MockResponse(f.read(), 'text/plain')

        config = {
            'instances': [{
                'host': 'foo',
                'kube_state_url': 'http://foo',
                'label_joins': {
                    'kube_deployment_labels': {
                        'label_to_match': 'deployment',
                        'labels_to_get':['label_addonmanager_kubernetes_io_mode']
                    }
                },
            }]
        }
        # run check twice to have the labels join mapping.
        self.run_check_twice(config)
        for metric in self.METRICS:
            self.assertMetric(
                metric,
                hostname=self.HOSTNAMES.get(metric, None)
            )
            tags = self.JOINED_METRICS.get(metric, None)
            if tags:
                for tag in tags:
                    self.assertMetricTag(metric, tag)
            if metric not in self.ZERO_METRICS:
                self.assertMetricNotAllZeros(metric)

    def assert_resourcequota(self):
        """ The metric name is created dynamically so we just check some exist. """
        for m in self.metrics:
            if 'kubernetes_state.resourcequota.' in m[0]:
                return True
        return False
