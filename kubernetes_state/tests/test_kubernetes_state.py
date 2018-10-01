# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import mock
import pytest

from datadog_checks.stubs import aggregator as _aggregator
from datadog_checks.kubernetes_state import KubernetesState


HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, 'fixtures')
NAMESPACE = 'kubernetes_state'
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
    # endpoints
    NAMESPACE + '.endpoint.address_available',
    NAMESPACE + '.endpoint.address_not_ready',
    NAMESPACE + '.endpoint.created',
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
    NAMESPACE + '.container.waiting',
    NAMESPACE + '.container.status_report.count.waiting',
    NAMESPACE + '.container.status_report.count.terminated',
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
    NAMESPACE + '.persistentvolumeclaim.request_storage',
    # statefulset
    NAMESPACE + '.statefulset.replicas',
    NAMESPACE + '.statefulset.replicas_current',
    NAMESPACE + '.statefulset.replicas_ready',
    NAMESPACE + '.statefulset.replicas_updated',
    # resourcequotas
    NAMESPACE + '.resourcequota.cpu.used',
    NAMESPACE + '.resourcequota.cpu.limit',
    NAMESPACE + '.resourcequota.memory.used',
    NAMESPACE + '.resourcequota.memory.limit',
    NAMESPACE + '.resourcequota.pods.used',
    NAMESPACE + '.resourcequota.pods.limit',
    NAMESPACE + '.resourcequota.limits.cpu.used',
    NAMESPACE + '.resourcequota.limits.cpu.limit',
    NAMESPACE + '.resourcequota.limits.memory.used',
    NAMESPACE + '.resourcequota.limits.memory.limit',
    # limitrange
    NAMESPACE + '.limitrange.cpu.default_request',
]

TAGS = {
    NAMESPACE + '.pod.ready': ['node:minikube'],
    NAMESPACE + '.pod.scheduled': ['node:minikube'],
    NAMESPACE + '.nodes.by_condition': [
        'condition:MemoryPressure', 'condition:DiskPressure',
        'condition:OutOfDisk', 'condition:Ready',
        'status:true', 'status:false', 'status:unknown',
    ],
    NAMESPACE + '.pod.status_phase': [
        'phase:Pending', 'phase:Running',
        'phase:Failed', 'phase:Succeeded',
        'phase:Unknown', 'namespace:default',
        'namespace:kube-system'
    ],
    NAMESPACE + '.container.status_report.count.waiting': [
        'reason:ContainerCreating',
        'reason:CrashLoopBackoff',  # Lowercase "off"
        'reason:CrashLoopBackOff',  # Uppercase "Off"
        'reason:ErrImagePull',
        'reason:ImagePullBackoff',
        'pod:kube-dns-1326421443-hj4hx',
        'pod:hello-1509998340-k4f8q'
    ],
    NAMESPACE + '.container.status_report.count.terminated': [
        'pod:pod2',
    ],
    NAMESPACE + '.persistentvolumeclaim.request_storage': [
        'storageclass:manual'
    ]
}

JOINED_METRICS = {
    NAMESPACE + '.deployment.replicas': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
    NAMESPACE + '.deployment.replicas_available': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
    NAMESPACE + '.deployment.replicas_unavailable': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
    NAMESPACE + '.deployment.replicas_updated': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
    NAMESPACE + '.deployment.replicas_desired': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
    NAMESPACE + '.deployment.paused': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
    NAMESPACE + '.deployment.rollingupdate.max_unavailable': [
        'label_addonmanager_kubernetes_io_mode:Reconcile', 'deployment:kube-dns'
    ],
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
    NAMESPACE + '.endpoint.address_available',
    NAMESPACE + '.endpoint.address_not_ready',
]


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly
    returned by requests.get
    """
    def __init__(self, content, content_type):
        self.content = content
        self.headers = {'Content-Type': content_type}

    def iter_lines(self, **_):
        for elt in self.content.split("\n"):
            yield elt

    def close(self):
        pass


@pytest.fixture
def aggregator():
    _aggregator.reset()
    return _aggregator


@pytest.fixture
def instance():
    return {
        'host': 'foo',
        'kube_state_url': 'http://foo',
        'tags': ['optional:tag1']
    }


@pytest.fixture
def check(instance):
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    with open(os.path.join(HERE, 'fixtures', 'prometheus.txt'), 'rb') as f:
        check.poll = mock.MagicMock(return_value=MockResponse(f.read(), 'text/plain'))

    return check


def assert_not_all_zeroes(aggregator, metric_name):
    for m in aggregator.metrics(metric_name):
        if m.value != 0:
            return True
    raise AssertionError("All metrics named {} have 0 value.".format(metric_name))


def resourcequota_was_collected(aggregator):
    """ The metric name is created dynamically so we just check some exist. """
    for m in aggregator.metric_names:
        if '.resourcequota.' in m:
            return True
    return False


def test_update_kube_state_metrics(aggregator, instance, check):
    # run check twice to have pod/node mapping
    for _ in range(2):
        check.check(instance)

    aggregator.assert_service_check(NAMESPACE + '.node.ready', check.OK)
    aggregator.assert_service_check(NAMESPACE + '.node.out_of_disk', check.OK)
    aggregator.assert_service_check(NAMESPACE + '.node.memory_pressure', check.OK)
    aggregator.assert_service_check(NAMESPACE + '.node.network_unavailable', check.OK)
    aggregator.assert_service_check(NAMESPACE + '.node.disk_pressure', check.OK)
    # Running
    aggregator.assert_service_check(NAMESPACE + '.pod.phase', check.OK,
                                    tags=['namespace:default', 'pod:task-pv-pod', 'optional:tag1'])
    # Pending
    aggregator.assert_service_check(NAMESPACE + '.pod.phase', check.WARNING,
                                    tags=['namespace:default', 'pod:failingtest-f585bbd4-2fsml', 'optional:tag1'])
    # Succeeded
    aggregator.assert_service_check(NAMESPACE + '.pod.phase', check.OK,
                                    tags=['namespace:default', 'pod:hello-1509998340-k4f8q', 'optional:tag1'])
    # Failed
    aggregator.assert_service_check(NAMESPACE + '.pod.phase', check.CRITICAL,
                                    tags=['namespace:default', 'pod:should-run-once', 'optional:tag1'])
    # Unknown
    aggregator.assert_service_check(NAMESPACE + '.pod.phase', check.UNKNOWN,
                                    tags=['namespace:default', 'pod:hello-1509998460-tzh8k', 'optional:tag1'])

    # Make sure we send counts for all statuses to avoid no-data graphing issues
    aggregator.assert_metric(NAMESPACE + '.nodes.by_condition',
                             tags=['condition:Ready', 'status:true', 'optional:tag1'], value=1)
    aggregator.assert_metric(NAMESPACE + '.nodes.by_condition',
                             tags=['condition:Ready', 'status:false', 'optional:tag1'], value=0)
    aggregator.assert_metric(NAMESPACE + '.nodes.by_condition',
                             tags=['condition:Ready', 'status:unknown', 'optional:tag1'], value=0)

    # Make sure we send counts for all phases to avoid no-data graphing issues
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Pending', 'optional:tag1'], value=1)
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Running', 'optional:tag1'], value=3)
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Succeeded', 'optional:tag1'], value=2)
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Failed', 'optional:tag1'], value=2)
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Unknown', 'optional:tag1'], value=1)

    # Persistentvolume counts
    aggregator.assert_metric(NAMESPACE + '.persistentvolumes.by_phase',
                             tags=['storageclass:local-data', 'phase:Available', 'optional:tag1'], value=0)
    aggregator.assert_metric(NAMESPACE + '.persistentvolumes.by_phase',
                             tags=['storageclass:local-data', 'phase:Bound', 'optional:tag1'], value=2)
    aggregator.assert_metric(NAMESPACE + '.persistentvolumes.by_phase',
                             tags=['storageclass:local-data', 'phase:Failed', 'optional:tag1'], value=0)
    aggregator.assert_metric(NAMESPACE + '.persistentvolumes.by_phase',
                             tags=['storageclass:local-data', 'phase:Pending', 'optional:tag1'], value=0)
    aggregator.assert_metric(NAMESPACE + '.persistentvolumes.by_phase',
                             tags=['storageclass:local-data', 'phase:Released', 'optional:tag1'], value=0)

    for metric in METRICS:
        aggregator.assert_metric(metric, hostname=HOSTNAMES.get(metric, None))
        for tag in TAGS.get(metric, []):
            aggregator.assert_metric_has_tag(metric, tag)
        if metric not in ZERO_METRICS:
            assert_not_all_zeroes(aggregator, metric)

    # FIXME: the original assert for resourcequota wasn't working, following line should be uncommented
    # assert resourcequota_was_collected(aggregator)


def test_update_kube_state_metrics_v040(aggregator, instance, check):
    # run check twice to have pod/node mapping
    for _ in range(2):
        check.check(instance)

    aggregator.assert_service_check(NAMESPACE + '.node.ready', check.OK)
    aggregator.assert_service_check(NAMESPACE + '.node.out_of_disk', check.OK)

    for metric in METRICS:
        if not metric.startswith(NAMESPACE + '.hpa'):
            aggregator.assert_metric(metric)

    # FIXME: the original assert for resourcequota wasn't working, following line should be uncommented
    # assert resourcequota_was_collected(aggregator)


def test_join_custom_labels(aggregator, instance, check):
    instance['label_joins'] = {
        'kube_deployment_labels': {
            'label_to_match': 'deployment',
            'labels_to_get': ['label_addonmanager_kubernetes_io_mode']
        }
    }

    endpoint = instance['kube_state_url']
    scraper_config = check.config_map[endpoint]

    # this would be normally done in the __init__ function of the check
    scraper_config['label_joins'].update(instance['label_joins'])

    # run check twice to have pod/node mapping
    for _ in range(2):
        check.check(instance)

    for metric in METRICS:
        aggregator.assert_metric(metric, hostname=HOSTNAMES.get(metric, None))
        for tag in JOINED_METRICS.get(metric, []):
            aggregator.assert_metric_has_tag(metric, tag)
        if metric not in ZERO_METRICS:
            assert_not_all_zeroes(aggregator, metric)


def test_disabling_hostname_override(instance):
    endpoint = instance['kube_state_url']
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    scraper_config = check.config_map[endpoint]
    assert scraper_config['label_to_hostname'] == "node"

    instance["hostname_override"] = False
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    scraper_config = check.config_map[endpoint]
    assert scraper_config['label_to_hostname'] is None


def test_removing_pod_phase_service_checks(aggregator, instance, check):
    check.send_pod_phase_service_checks = False
    for _ in range(2):
        check.check(instance)
    # We should still send gauges
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Running', 'optional:tag1'], value=3)
    aggregator.assert_metric(NAMESPACE + '.pod.status_phase',
                             tags=['namespace:default', 'phase:Failed', 'optional:tag1'], value=2)
    # the service checks should not be sent
    assert NAMESPACE + '.pod.status_phase' not in aggregator._service_checks
