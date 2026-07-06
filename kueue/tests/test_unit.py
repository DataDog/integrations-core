# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json

import pytest

from datadog_checks.base.stubs import tagger
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kueue import KueueCheck
from datadog_checks.kueue.check import OTHER_RESOURCE_NAME, RESOURCE_NAME_MAP
from datadog_checks.kueue.kube_client import to_mutable_config
from datadog_checks.kueue.metrics import LOCAL_QUEUE_METRIC_MAP, METRIC_MAP, RESOURCE_METRIC_MAP
from datadog_checks.kueue.topology import DomainStat, build_node_gpu_usage, iter_domain_stats

from .common import EXPECTED_METRIC_TAGS, UNIT_METRICS, get_fixture_path

pytestmark = pytest.mark.unit


def test_mapped_metrics_are_in_metadata():
    mapped_metrics = set()
    mapped_metrics.update(_metadata_metric_name(metric_name) for metric_name in METRIC_MAP.values())
    mapped_metrics.update(_metadata_metric_name(metric_name) for metric_name in LOCAL_QUEUE_METRIC_MAP.values())

    resource_names = {OTHER_RESOURCE_NAME, *RESOURCE_NAME_MAP.values()}
    for metric_name in RESOURCE_METRIC_MAP.values():
        mapped_metrics.update(
            _metadata_metric_name(f'{metric_name}.{resource_name}') for resource_name in resource_names
        )

    metadata_metrics = {_base_metric_name(metric) for metric in get_metadata_metrics()}
    assert mapped_metrics.issubset(metadata_metrics)


def _metadata_metric_name(metric_name):
    if isinstance(metric_name, dict):
        metric_name = metric_name['name']

    return f'kueue.{metric_name}'


def _base_metric_name(metric_name):
    for suffix in ('.bucket', '.count', '.sum'):
        if metric_name.endswith(suffix):
            return metric_name[: -len(suffix)]

    return metric_name


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))

    check = KueueCheck('kueue', {}, [{**instance, 'collect_workload_events': False}])
    check.kube_client = FakeKubernetesAPIClient(**topology_fixtures())
    dd_run_check(check)

    for metric in UNIT_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    for metric, tags in EXPECTED_METRIC_TAGS.items():
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


def test_queue_tagger_tags(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.set_tags(
        {
            'kubernetes_kueue_queue://clusterqueue//cluster-queue': ['cluster_queue_tag:value'],
            'kubernetes_kueue_queue://localqueue/default/user-queue': ['local_queue_tag:value'],
            'kueue_resource_flavor://default-flavor': ['resource_flavor_tag:value'],
        }
    )

    check = KueueCheck(
        'kueue', {}, [{**instance, 'collect_workload_events': False, 'collect_topology_domain_metrics': False}]
    )
    dd_run_check(check)

    aggregator.assert_metric_has_tag('kueue.pending_workloads', 'cluster_queue_tag:value')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.gpu', 'cluster_queue_tag:value')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.gpu', 'resource_flavor_tag:value')
    aggregator.assert_metric_has_tag('kueue.local_queue.pending_workloads', 'cluster_queue_tag:value')
    aggregator.assert_metric_has_tag('kueue.local_queue.pending_workloads', 'local_queue_tag:value')
    aggregator.assert_metric_has_tag('kueue.local_queue.resource_reservation.cpu', 'local_queue_tag:value')
    aggregator.assert_metric_has_tag('kueue.local_queue.resource_usage.cpu', 'local_queue_tag:value')
    tagger.assert_called('kubernetes_kueue_queue://clusterqueue//cluster-queue', tagger.ORCHESTRATOR)
    tagger.assert_called('kubernetes_kueue_queue://localqueue/default/user-queue', tagger.ORCHESTRATOR)
    tagger.assert_called('kueue_resource_flavor://default-flavor', tagger.ORCHESTRATOR)


def test_queue_tagger_tags_are_scoped(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.set_tags(
        {
            'kubernetes_kueue_queue://clusterqueue//cluster-queue': ['cluster_queue_tag:value'],
        }
    )

    check = KueueCheck(
        'kueue', {}, [{**instance, 'collect_workload_events': False, 'collect_topology_domain_metrics': False}]
    )
    dd_run_check(check)

    go_goroutines_tags = _get_metric_tags(aggregator, 'kueue.go.goroutines')
    local_queue_tags = _get_metric_tags(aggregator, 'kueue.local_queue.pending_workloads')
    assert 'cluster_queue_tag:value' not in go_goroutines_tags
    assert 'local_queue_tag:value' not in local_queue_tags


def test_resource_name_map(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    instance = {
        **instance,
        'resource_name_map': {
            'example.com/fpga': 'fpga',
            'nvidia.com/gpu': 'custom_gpu',
        },
    }

    check = KueueCheck(
        'kueue', {}, [{**instance, 'collect_workload_events': False, 'collect_topology_domain_metrics': False}]
    )
    dd_run_check(check)

    aggregator.assert_metric('kueue.cluster_queue.resource_usage.cpu')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.gpu')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.memory')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.fpga')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.custom_gpu', count=0)
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'test:tag')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'kueue_cluster_queue:cluster-queue')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'kueue_resource_flavor:default-flavor')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'replica_role:leader')


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='openmetrics_endpoint\\n  Field required',
    ):
        check = KueueCheck('kueue', {}, [{}])
        dd_run_check(check)


def test_to_mutable_config_converts_immutable_config_model_values():
    value = {'clusters': ({'cluster': {'server': 'https://example.com'}, 'name': 'cluster'},), 'contexts': ()}

    assert to_mutable_config(value) == {
        'clusters': [{'cluster': {'server': 'https://example.com'}, 'name': 'cluster'}],
        'contexts': [],
    }


def test_workload_events_config_can_be_parsed_before_check(instance):
    check = KueueCheck('kueue', {}, [instance])

    check._parse_workload_events_config()

    assert check.collect_workload_events is True


class FakeKubernetesAPIClient:
    def __init__(
        self,
        *workload_snapshots,
        nodes=None,
        pods=None,
        resource_flavors=None,
        topologies=None,
    ):
        self.workload_snapshots = list(workload_snapshots)
        self.list_workloads_namespaces = []
        self.nodes = nodes or []
        self.pods = pods or []
        self.resource_flavors = resource_flavors or []
        self.topologies = topologies or []

    def list_workloads(self, namespace=None):
        self.list_workloads_namespaces.append(namespace)
        return self.workload_snapshots.pop(0)

    def list_nodes(self):
        return self.nodes

    def list_pods(self):
        return self.pods

    def list_resource_flavors(self):
        return self.resource_flavors

    def list_topologies(self):
        return self.topologies


def load_workloads(name):
    with open(get_fixture_path(f'workloads/{name}.json')) as f:
        return json.load(f)


def load_topology_fixture(name):
    with open(get_fixture_path(f'topology/{name}.json')) as f:
        return json.load(f)


def with_namespace(workloads, namespace):
    workloads = json.loads(json.dumps(workloads))
    for workload in workloads:
        workload['metadata']['namespace'] = namespace
    return workloads


def with_uid(workloads, uid):
    workloads = json.loads(json.dumps(workloads))
    for workload in workloads:
        workload['metadata']['uid'] = uid
    return workloads


def without_admission(workloads):
    workloads = json.loads(json.dumps(workloads))
    for workload in workloads:
        workload['status'].pop('admission', None)
    return workloads


def topology_fixtures():
    return {
        'nodes': load_topology_fixture('nodes'),
        'pods': load_topology_fixture('pods'),
        'resource_flavors': load_topology_fixture('resourceflavors'),
        'topologies': load_topology_fixture('topologies'),
    }


def test_node_gpu_usage_counts_only_bound_non_terminal_gpu_pods():
    usage = build_node_gpu_usage(load_topology_fixture('pods'))

    assert usage == {
        'node-a1': 3,
        'node-b1': 4,
        'node-other-flavor': 6,
    }


def test_iter_domain_stats_groups_domains_by_topology_path_and_classifies_usage():
    stats = list(iter_domain_stats(**topology_fixtures()))

    assert (
        DomainStat(
            flavor='tas-flavor',
            level='cloud.provider.com/topology-block',
            total=2,
            available=0,
            fully_used=1,
            partially_used=1,
        )
        in stats
    )
    assert (
        DomainStat(
            flavor='tas-flavor',
            level='cloud.provider.com/topology-rack',
            total=2,
            available=0,
            fully_used=1,
            partially_used=1,
        )
        in stats
    )
    assert (
        DomainStat(
            flavor='tas-flavor',
            level='kubernetes.io/hostname',
            total=3,
            available=1,
            fully_used=1,
            partially_used=1,
        )
        in stats
    )
    assert (
        DomainStat(
            flavor='other-flavor',
            level='zone',
            total=1,
            available=0,
            fully_used=0,
            partially_used=1,
        )
        in stats
    )
    assert (
        DomainStat(
            flavor='other-flavor',
            level='kubernetes.io/hostname',
            total=1,
            available=0,
            fully_used=0,
            partially_used=1,
        )
        in stats
    )
    assert all(stat.flavor not in {'no-topology-flavor', 'missing-topology-flavor'} for stat in stats)


def test_iter_domain_stats_empty_node_labels_match_all_nodes_with_complete_topology_labels():
    stats = list(iter_domain_stats(**topology_fixtures()))

    assert (
        DomainStat(
            flavor='all-nodes-flavor',
            level='kubernetes.io/hostname',
            total=3,
            available=1,
            fully_used=1,
            partially_used=1,
        )
        in stats
    )


def test_topology_domain_metrics(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.set_tags({'kueue_resource_flavor://tas-flavor': ['resource_flavor_tag:value']})
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(load_workloads('pending'), **topology_fixtures())

    dd_run_check(check)

    expected_tags = [
        'test:tag',
        'kueue_resource_flavor:tas-flavor',
        'domain:kubernetes.io/hostname',
        'domain_short:hostname',
        'resource_flavor_tag:value',
    ]
    aggregator.assert_metric('kueue.topology_domains.total', value=3, tags=expected_tags)
    aggregator.assert_metric('kueue.topology_domains.available', value=1, tags=expected_tags)
    aggregator.assert_metric('kueue.topology_domains.fully_used', value=1, tags=expected_tags)
    aggregator.assert_metric('kueue.topology_domains.partially_used', value=1, tags=expected_tags)
    tagger.assert_called('kueue_resource_flavor://tas-flavor', tagger.ORCHESTRATOR)


def test_workload_events_suppress_first_poll(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(load_workloads('admitted'))

    dd_run_check(check)

    assert not aggregator.events


def test_workload_events_transitions(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.reset()
    tagger.set_tags(
        {
            'kubernetes_kueue_queue://clusterqueue//default': ['cluster_queue_tag:value'],
            'kubernetes_kueue_queue://localqueue/team-a/gpu': ['local_queue_tag:value'],
            'kueue_workload://team-a/training-job': ['workload_tag:value'],
        }
    )
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(load_workloads('pending'), load_workloads('admitted'))

    dd_run_check(check)
    dd_run_check(check)

    expected_tags = [
        'test:tag',
        'kube_namespace:team-a',
        'kueue_workload:training-job',
        'kueue_workload_uid:workload-uid',
        'kueue_local_queue:gpu',
        'kueue_cluster_queue:default',
        'kueue_workload_priority:100',
        'kueue_workload_priority_class:high',
        'cluster_queue_tag:value',
        'local_queue_tag:value',
        'workload_tag:value',
    ]
    aggregator.assert_event(
        'Workload team-a/training-job quota reserved. Quota reserved in ClusterQueue default',
        source_type_name='kueue',
        tags=[*expected_tags, 'kueue_transition:quota_reserved'],
    )
    aggregator.assert_event(
        'Workload team-a/training-job admitted. The workload is admitted Queued wait time was 8s.',
        source_type_name='kueue',
        tags=[*expected_tags, 'kueue_transition:admitted'],
    )
    aggregator.assert_event(
        'Workload team-a/training-job running. All pods are ready',
        source_type_name='kueue',
        tags=[*expected_tags, 'kueue_transition:running'],
    )


def test_workload_events_no_duplicates(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(
        load_workloads('pending'),
        load_workloads('admitted'),
        load_workloads('admitted'),
    )

    dd_run_check(check)
    dd_run_check(check)
    dd_run_check(check)

    aggregator.assert_event('Workload team-a/training-job admitted.', count=1, exact_match=False)


def test_workload_events_created_for_new_workload(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(
        load_workloads('pending'),
        with_uid(load_workloads('admitted'), 'new-workload-uid'),
    )

    dd_run_check(check)
    dd_run_check(check)

    assert_event_has_tags(
        aggregator,
        'Workload team-a/training-job created.',
        ['kueue_workload_uid:new-workload-uid', 'kueue_transition:created'],
        event_type='kueue.workload.created',
        alert_type='info',
    )
    assert_event_has_tags(
        aggregator,
        'Workload team-a/training-job admitted.',
        ['kueue_workload_uid:new-workload-uid', 'kueue_transition:admitted'],
    )


def test_workload_events_evicted_and_finished(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.reset()
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(load_workloads('admitted'), load_workloads('evicted'))

    dd_run_check(check)
    dd_run_check(check)

    expected_evicted_tags = [
        'test:tag',
        'kube_namespace:team-a',
        'kueue_workload:training-job',
        'kueue_workload_uid:workload-uid',
        'kueue_local_queue:gpu',
        'kueue_transition:evicted',
        'kueue_workload_priority:100',
        'kueue_workload_priority_class:high',
        'kueue_cluster_queue:default',
        'kueue_eviction_reason:Preempted',
        'kueue_preemption_reason:InClusterQueue',
        'kueue_preempted_by:preempting-workload-uid',
    ]
    aggregator.assert_event(
        'Workload team-a/training-job evicted. Preempted to accommodate a workload '
        '(UID: preempting-workload-uid) due to prioritization in the ClusterQueue Eviction reason: Preempted. '
        'Preemption reason: InClusterQueue.',
        alert_type='warning',
        tags=expected_evicted_tags,
    )
    aggregator.assert_event(
        'Workload team-a/training-job finished. Reached expected number of succeeded pods Finished reason: Succeeded.',
        alert_type='info',
    )


def test_workload_events_evicted_uses_previous_admission(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.set_tags(
        {
            'kubernetes_kueue_queue://clusterqueue//default': ['cluster_queue_tag:value'],
        }
    )
    check = KueueCheck('kueue', {}, [instance])
    check.kube_client = FakeKubernetesAPIClient(
        load_workloads('admitted'),
        without_admission(load_workloads('evicted')),
    )

    dd_run_check(check)
    dd_run_check(check)

    assert_event_has_tags(
        aggregator,
        'Workload team-a/training-job evicted.',
        ['kueue_cluster_queue:default', 'cluster_queue_tag:value'],
    )


def test_workload_events_namespace_filter(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = KueueCheck(
        'kueue',
        {},
        [
            {
                **instance,
                'workload_events_namespaces': ['default'],
            }
        ],
    )
    check.kube_client = FakeKubernetesAPIClient(
        with_namespace(load_workloads('pending'), 'default'),
        with_namespace(load_workloads('admitted'), 'default'),
    )

    dd_run_check(check)
    dd_run_check(check)

    assert_event_has_tags(
        aggregator,
        'Workload default/training-job admitted.',
        ['kube_namespace:default'],
    )
    assert check.kube_client.list_workloads_namespaces == ['default', 'default']


def assert_event_has_tags(aggregator, msg_text, tags, **kwargs):
    for event in aggregator.events:
        if msg_text not in event['msg_text']:
            continue
        if not set(tags).issubset(event['tags']):
            continue
        for name, value in kwargs.items():
            if event[name] != value:
                break
        else:
            return

    raise AssertionError(f'No event matching {msg_text!r} with tags {tags!r}')


def _get_metric_tags(aggregator, metric_name):
    return {tag for metric in aggregator.metrics(metric_name) for tag in metric.tags}
