# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base.utils.common import ensure_unicode
from datadog_checks.kubernetes_state import KubernetesState

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_PATH = os.path.join(HERE, 'fixtures')
NAMESPACE = 'kubernetes_state'
CHECK_NAME = 'kubernetes_state'

METRICS = [
    # nodes
    NAMESPACE + '.node.count',
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
    NAMESPACE + '.daemonset.updated',
    # hpa
    NAMESPACE + '.hpa.min_replicas',
    NAMESPACE + '.hpa.max_replicas',
    NAMESPACE + '.hpa.desired_replicas',
    NAMESPACE + '.hpa.current_replicas',
    NAMESPACE + '.hpa.condition',
    # pdb
    NAMESPACE + '.pdb.disruptions_allowed',
    NAMESPACE + '.pdb.pods_desired',
    NAMESPACE + '.pdb.pods_healthy',
    NAMESPACE + '.pdb.pods_total',
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
    # services
    NAMESPACE + '.service.count',
    # jobs
    NAMESPACE + '.job.failed',
    NAMESPACE + '.job.succeeded',
    # vpa
    NAMESPACE + '.vpa.lower_bound',
    NAMESPACE + '.vpa.target',
    NAMESPACE + '.vpa.uncapped_target',
    NAMESPACE + '.vpa.upperbound',
    NAMESPACE + '.vpa.update_mode',
]

TAGS = {
    NAMESPACE
    + '.node.count': [
        'container_runtime_version:docker://1.12.6',
        'kernel_version:4.9.13',
        'kubelet_version:v1.8.0',
        'kubeproxy_version:v1.8.0',
        'os_image:buildroot 2017.02',
    ],
    NAMESPACE + '.pod.ready': ['node:minikube'],
    NAMESPACE + '.pod.scheduled': ['node:minikube'],
    NAMESPACE
    + '.nodes.by_condition': [
        'condition:memorypressure',
        'condition:diskpressure',
        'condition:outofdisk',
        'condition:ready',
        'status:true',
        'status:false',
        'status:unknown',
    ],
    NAMESPACE
    + '.pod.status_phase': [
        'phase:pending',
        'phase:running',
        'phase:failed',
        'phase:succeeded',
        'phase:unknown',
        'namespace:default',
        'namespace:kube-system',
    ],
    NAMESPACE
    + '.container.status_report.count.waiting': [
        'reason:containercreating',
        'reason:crashloopbackoff',  # Lowercase "off"
        'reason:crashloopbackoff',  # Uppercase "Off"
        'reason:errimagepull',
        'reason:imagepullbackoff',
        'pod:kube-dns-1326421443-hj4hx',
        'pod:hello-1509998340-k4f8q',
    ],
    NAMESPACE + '.container.status_report.count.terminated': ['pod:pod2'],
    NAMESPACE + '.persistentvolumeclaim.request_storage': ['storageclass:manual'],
    NAMESPACE
    + '.service.count': [
        'namespace:kube-system',
        'namespace:default',
        'type:clusterip',
        'type:nodeport',
        'type:loadbalancer',
    ],
    NAMESPACE + '.job.failed': ['job:hello', 'job_name:hello2'],
    NAMESPACE + '.job.succeeded': ['job:hello', 'job_name:hello2'],
    NAMESPACE + '.hpa.condition': ['namespace:default', 'hpa:myhpa', 'condition:true', 'status:abletoscale'],
}

JOINED_METRICS = {
    NAMESPACE + '.deployment.replicas': ['label_addonmanager_kubernetes_io_mode:reconcile', 'deployment:kube-dns'],
    NAMESPACE
    + '.deployment.replicas_available': ['label_addonmanager_kubernetes_io_mode:reconcile', 'deployment:kube-dns'],
    NAMESPACE
    + '.deployment.replicas_unavailable': ['label_addonmanager_kubernetes_io_mode:reconcile', 'deployment:kube-dns'],
    NAMESPACE
    + '.deployment.replicas_updated': ['label_addonmanager_kubernetes_io_mode:reconcile', 'deployment:kube-dns'],
    NAMESPACE
    + '.deployment.replicas_desired': ['label_addonmanager_kubernetes_io_mode:reconcile', 'deployment:kube-dns'],
    NAMESPACE + '.deployment.paused': ['label_addonmanager_kubernetes_io_mode:reconcile', 'deployment:kube-dns'],
    NAMESPACE
    + '.deployment.rollingupdate.max_unavailable': [
        'label_addonmanager_kubernetes_io_mode:reconcile',
        'deployment:kube-dns',
    ],
}

HOSTNAMES = {
    NAMESPACE + '.pod.ready': 'minikube',
    NAMESPACE + '.pod.scheduled': 'minikube',
    NAMESPACE + '.container.status_report.count.waiting': 'minikube',
    NAMESPACE + '.container.status_report.count.terminated': 'minikube',
}

ZERO_METRICS = [
    NAMESPACE + '.deployment.replicas_unavailable',
    NAMESPACE + '.deployment.paused',
    NAMESPACE + '.daemonset.misscheduled',
    NAMESPACE + '.container.terminated',
    NAMESPACE + '.container.waiting',
    NAMESPACE + '.endpoint.address_available',
    NAMESPACE + '.endpoint.address_not_ready',
    NAMESPACE + '.job.failed',
    NAMESPACE + '.job.succeeded',
]


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly
    returned by requests.get
    """

    def __init__(self, content, content_type):
        self.content = content
        self.headers = {'Content-Type': content_type}
        self.encoding = 'utf-8'

    def iter_lines(self, **_):
        for elt in self.content.split(b"\n"):
            yield ensure_unicode(elt)

    def close(self):
        pass


def mock_from_file(fname):
    with open(os.path.join(HERE, 'fixtures', fname), 'rb') as f:
        return f.read()


@pytest.fixture
def instance():
    return {
        'host': 'foo',
        'kube_state_url': 'http://foo',
        'tags': ['optional:tag1'],
        'telemetry': False,
    }


def _check(instance,mock_file="prometheus.txt"):
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    check.poll = mock.MagicMock(return_value=MockResponse(mock_from_file(mock_file), 'text/plain'))
    return check


@pytest.fixture
def check(instance):
    return _check(instance)


@pytest.fixture
def check_with_join_kube_labels(instance):
    instance['join_kube_labels'] = True
    return _check(instance)


@pytest.fixture
def check_with_join_standard_tag_labels(instance, ):
    instance['join_standard_tags'] = True
    return _check(instance=instance, mock_file="ksm-standard-tags-gke.txt")


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

    # Make sure we send counts for all statuses to avoid no-data graphing issues
    aggregator.assert_metric(
        NAMESPACE + '.nodes.by_condition', tags=['condition:ready', 'status:true', 'optional:tag1'], value=1
    )
    aggregator.assert_metric(
        NAMESPACE + '.nodes.by_condition', tags=['condition:ready', 'status:false', 'optional:tag1'], value=0
    )
    aggregator.assert_metric(
        NAMESPACE + '.nodes.by_condition', tags=['condition:ready', 'status:unknown', 'optional:tag1'], value=0
    )

    # Make sure we send counts for all phases to avoid no-data graphing issues
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:pending', 'pod_phase:pending', 'optional:tag1'],
        value=1,
    )
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:running', 'pod_phase:running', 'optional:tag1'],
        value=3,
    )
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:succeeded', 'pod_phase:succeeded', 'optional:tag1'],
        value=2,
    )
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:failed', 'pod_phase:failed', 'optional:tag1'],
        value=2,
    )
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:unknown', 'pod_phase:unknown', 'optional:tag1'],
        value=1,
    )

    # Persistentvolume counts
    aggregator.assert_metric(
        NAMESPACE + '.persistentvolumes.by_phase',
        tags=['storageclass:local-data', 'phase:available', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.persistentvolumes.by_phase',
        tags=['storageclass:local-data', 'phase:bound', 'optional:tag1'],
        value=2,
    )
    aggregator.assert_metric(
        NAMESPACE + '.persistentvolumes.by_phase',
        tags=['storageclass:local-data', 'phase:failed', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.persistentvolumes.by_phase',
        tags=['storageclass:local-data', 'phase:pending', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.persistentvolumes.by_phase',
        tags=['storageclass:local-data', 'phase:released', 'optional:tag1'],
        value=0,
    )

    for metric in METRICS:
        aggregator.assert_metric(metric, hostname=HOSTNAMES.get(metric, None))
        for tag in TAGS.get(metric, []):
            aggregator.assert_metric_has_tag(metric, tag)
        if metric not in ZERO_METRICS:
            assert_not_all_zeroes(aggregator, metric)

    assert NAMESPACE + '.pod.status_phase' not in aggregator._service_checks

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


def test_join_kube_labels(aggregator, instance, check_with_join_kube_labels):
    # run check twice to have pod/node mapping
    for _ in range(2):
        check_with_join_kube_labels.check(instance)

    aggregator.assert_metric(
        NAMESPACE + '.container.ready',
        tags=[
            'container:kube-state-metrics',
            'kube_container_name:kube-state-metrics',
            'kube_namespace:default',
            'label_app:kube-state-metrics',
            'label_pod_template_hash:639670438',
            'label_release:jaundiced-numbat',
            'namespace:default',
            'node:minikube',
            'optional:tag1',
            'phase:running',
            'pod:jaundiced-numbat-kube-state-metrics-b7fbc487d-4phhj',
            'pod_name:jaundiced-numbat-kube-state-metrics-b7fbc487d-4phhj',
            'pod_phase:running',
        ],
        value=1,
    )
    aggregator.assert_metric(
        NAMESPACE + '.deployment.replicas',
        tags=[
            'deployment:jaundiced-numbat-kube-state-metrics',
            'kube_deployment:jaundiced-numbat-kube-state-metrics',
            'kube_namespace:default',
            'label_app:kube-state-metrics',
            'label_chart:kube-state-metrics-0.3.1',
            'label_heritage:tiller',
            'label_release:jaundiced-numbat',
            'namespace:default',
            'optional:tag1',
        ],
        value=1,
    )


def test_join_standard_tags_labels(aggregator, instance, check_with_join_standard_tag_labels):
    # run check twice to have pod/node mapping
    for _ in range(2):
        check_with_join_standard_tag_labels.check(instance)

    # Pod standard tags
    aggregator.assert_metric(
        NAMESPACE + '.container.ready',
        tags=[
            'container:master',
            'kube_container_name:master',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            'node:gke-abcdef-cluster-default-pool-53c8a4ea-z9rw',
            'phase:running',
            'pod:redis-599d64fcb9-c654j',
            'pod_name:redis-599d64fcb9-c654j',
            'pod_phase:running',
            "env:dev",
            "service:redis",
            "version:v1"
        ],
        value=1,
    )

    # Deployment standard tags
    aggregator.assert_metric(
        NAMESPACE + '.deployment.replicas',
        tags=[
            'deployment:redis',
            'kube_deployment:redis',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            "env:dev",
            "service:redis",
            "version:v1"
        ],
        value=1,
    )

    # ReplicaSet standard tags
    aggregator.assert_metric(
        NAMESPACE + '.replicaset.replicas_ready',
        tags=[
            'replicaset:redis-599d64fcb9',
            'kube_replica_set:redis-599d64fcb9',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            "env:dev",
            "service:redis",
            "version:v1"
        ],
        value=1,
    )

    # Daemonset standard tags
    aggregator.assert_metric(
        NAMESPACE + '.daemonset.desired',
        tags=[
            'daemonset:datadog-monitoring',
            'kube_daemon_set:datadog-monitoring',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            "env:dev",
            "service:datadog-agent",
            "version:7"
        ],
        value=3,
    )

    # StatefulSet standard tags
    aggregator.assert_metric(
        NAMESPACE + '.statefulset.replicas_ready',
        tags=[
            'statefulset:web',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            "env:dev",
            "service:web",
            "version:v1"
        ],
        value=2,
    )

    # Job standard tags
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=[
            'job_name:curl-job',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            "env:dev",
            "service:curl-job",
            "version:v1"
        ],
        value=1,
    )

    # CronJob standard tags
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=[
            'job_name:curl-cron-job',
            'kube_namespace:default',
            'namespace:default',
            'optional:tag1',
            "env:dev",
            "service:curl-cron-job",
            "version:v1"
        ],
        value=1,
    )


def test_join_custom_labels(aggregator, instance, check):
    instance['label_joins'] = {
        'kube_deployment_labels': {
            'label_to_match': 'deployment',
            'labels_to_get': ['label_addonmanager_kubernetes_io_mode'],
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


def test_pod_phase_gauges(aggregator, instance, check):
    for _ in range(2):
        check.check(instance)
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:running', 'pod_phase:running', 'optional:tag1'],
        value=3,
    )
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase',
        tags=['kube_namespace:default', 'namespace:default', 'phase:failed', 'pod_phase:failed', 'optional:tag1'],
        value=2,
    )


def test_extract_timestamp(check):
    job_name = "hello2-1509998340"
    job_name2 = "hello-2-1509998340"
    job_name3 = "hello2"
    result = check._extract_job_timestamp(job_name)
    assert result == 1509998340
    result = check._extract_job_timestamp(job_name2)
    assert result == 1509998340
    result = check._extract_job_timestamp(job_name3)
    assert result is None


def test_job_counts(aggregator, instance):
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    payload = mock_from_file("prometheus.txt")
    check.poll = mock.MagicMock(return_value=MockResponse(payload, 'text/plain'))

    for _ in range(2):
        check.check(instance)

    # Test cron jobs
    aggregator.assert_metric(
        NAMESPACE + '.job.failed',
        tags=['namespace:default', 'kube_namespace:default', 'kube_job:hello', 'job:hello', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'kube_job:hello', 'job:hello', 'optional:tag1'],
        value=3,
    )

    # Test jobs
    aggregator.assert_metric(
        NAMESPACE + '.job.failed',
        tags=['namespace:default', 'kube_namespace:default', 'job_name:test', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'job_name:test', 'optional:tag1'],
        value=1,
    )

    # Re-run check to make sure we don't count the same jobs
    check.check(instance)

    # Test cron jobs
    aggregator.assert_metric(
        NAMESPACE + '.job.failed',
        tags=['namespace:default', 'kube_namespace:default', 'kube_job:hello', 'job:hello', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'kube_job:hello', 'job:hello', 'optional:tag1'],
        value=3,
    )

    # Test jobs
    aggregator.assert_metric(
        NAMESPACE + '.job.failed',
        tags=['namespace:default', 'kube_namespace:default', 'job_name:test', 'optional:tag1'],
        value=0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'job_name:test', 'optional:tag1'],
        value=1,
    )

    # Edit the payload and rerun the check
    payload = payload.replace(
        b'kube_job_status_succeeded{job="hello-1509998340",namespace="default"} 1',
        b'kube_job_status_succeeded{job="hello-1509998500",namespace="default"} 1',
    )
    payload = payload.replace(
        b'kube_job_status_failed{job="hello-1509998340",namespace="default"} 0',
        b'kube_job_status_failed{job="hello-1509998510",namespace="default"} 1',
    )
    payload = payload.replace(
        b'kube_job_status_succeeded{job_name="test",namespace="default"} 1',
        b'kube_job_status_succeeded{job_name="test",namespace="default"} 0',
    )

    check.poll = mock.MagicMock(return_value=MockResponse(payload, 'text/plain'))
    check.check(instance)
    aggregator.assert_metric(
        NAMESPACE + '.job.failed',
        tags=['namespace:default', 'kube_namespace:default', 'job:hello', 'kube_job:hello', 'optional:tag1'],
        value=1,
    )
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'job:hello', 'kube_job:hello', 'optional:tag1'],
        value=4,
    )

    # Edit the payload to mimick a job running and rerun the check
    payload = payload.replace(
        b'kube_job_status_succeeded{job="hello-1509998500",namespace="default"} 1',
        b'kube_job_status_succeeded{job="hello-1509998600",namespace="default"} 0',
    )
    # Edit the payload to mimick a job re-creation
    payload = payload.replace(
        b'kube_job_status_succeeded{job_name="test",namespace="default"} 0',
        b'kube_job_status_succeeded{job_name="test",namespace="default"} 1',
    )

    check.poll = mock.MagicMock(return_value=MockResponse(payload, 'text/plain'))
    check.check(instance)
    # Test if we now have two as the value for the same job
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'job_name:test', 'optional:tag1'],
        value=2,
    )

    # Edit the payload to mimick a job that stopped running and rerun the check
    payload = payload.replace(
        b'kube_job_status_succeeded{job="hello-1509998600",namespace="default"} 0',
        b'kube_job_status_succeeded{job="hello-1509998600",namespace="default"} 1',
    )

    check.poll = mock.MagicMock(return_value=MockResponse(payload, 'text/plain'))
    check.check(instance)
    aggregator.assert_metric(
        NAMESPACE + '.job.succeeded',
        tags=['namespace:default', 'kube_namespace:default', 'job:hello', 'kube_job:hello', 'optional:tag1'],
        value=5,
    )


def test_keep_ksm_labels_desactivated(aggregator, instance):
    instance['keep_ksm_labels'] = False
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    check.poll = mock.MagicMock(return_value=MockResponse(mock_from_file("prometheus.txt"), 'text/plain'))
    check.check(instance)
    for _ in range(2):
        check.check(instance)
    aggregator.assert_metric(
        NAMESPACE + '.pod.status_phase', tags=['kube_namespace:default', 'pod_phase:running', 'optional:tag1'], value=3
    )


def test_experimental_labels(aggregator, instance):
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    check.poll = mock.MagicMock(return_value=MockResponse(mock_from_file("prometheus.txt"), 'text/plain'))
    for _ in range(2):
        check.check(instance)

    assert aggregator.metrics(NAMESPACE + '.hpa.spec_target_metric') == []

    instance['experimental_metrics'] = True
    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    check.poll = mock.MagicMock(return_value=MockResponse(mock_from_file("prometheus.txt"), 'text/plain'))
    for _ in range(2):
        check.check(instance)

    aggregator.assert_metric(
        NAMESPACE + '.hpa.spec_target_metric',
        tags=[
            'hpa:dummy-nginx-ingress-controller',
            'kube_namespace:default',
            'metric_name:cpu',
            'metric_target_type:utilization',
            'namespace:default',
            'optional:tag1',
        ],
        value=80.0,
    )


def test_telemetry(aggregator, instance):
    instance['telemetry'] = True
    instance['experimental_metrics'] = True

    check = KubernetesState(CHECK_NAME, {}, {}, [instance])
    check.poll = mock.MagicMock(return_value=MockResponse(mock_from_file("prometheus.txt"), 'text/plain'))

    endpoint = instance['kube_state_url']
    scraper_config = check.config_map[endpoint]
    scraper_config['_text_filter_blacklist'] = ['resourcequota']

    for _ in range(2):
        check.check(instance)
    aggregator.assert_metric(NAMESPACE + '.telemetry.payload.size', tags=['optional:tag1'], value=90948.0)
    aggregator.assert_metric(NAMESPACE + '.telemetry.metrics.processed.count', tags=['optional:tag1'], value=914.0)
    aggregator.assert_metric(NAMESPACE + '.telemetry.metrics.input.count', tags=['optional:tag1'], value=1288.0)
    aggregator.assert_metric(NAMESPACE + '.telemetry.metrics.blacklist.count', tags=['optional:tag1'], value=24.0)
    aggregator.assert_metric(NAMESPACE + '.telemetry.metrics.ignored.count', tags=['optional:tag1'], value=374.0)
    aggregator.assert_metric(
        NAMESPACE + '.telemetry.collector.metrics.count',
        tags=['resource_name:pod', 'resource_namespace:default', 'optional:tag1'],
        value=540.0,
    )
    aggregator.assert_metric(
        NAMESPACE + '.telemetry.collector.metrics.count',
        tags=['resource_name:hpa', 'resource_namespace:ns1', 'optional:tag1'],
        value=8.0,
    )
