# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kueue import KueueCheck
from datadog_checks.kueue.check import OTHER_RESOURCE_NAME, RESOURCE_NAME_MAP
from datadog_checks.kueue.metrics import LOCAL_QUEUE_METRIC_MAP, METRIC_MAP, RESOURCE_METRIC_MAP

from .common import TEST_METRICS, get_fixture_path

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

    check = KueueCheck('kueue', {}, [instance])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    expected_metric_tags = (
        ('kueue.go.info', 'go_version:go1.24.4'),
        ('kueue.cluster_queue.resource_usage.gpu', 'kueue_cluster_queue:default'),
        ('kueue.cluster_queue.resource_pending.gpu', 'kueue_cluster_queue:default'),
        ('kueue.pending_workloads', 'kueue_cluster_queue:default'),
        ('kueue.pending_workloads', 'status:inadmissible'),
        ('kueue.resource_flavor.quota_reserved_workloads', 'kueue_cluster_queue:default'),
        ('kueue.local_queue.pending_workloads', 'kueue_local_queue:gpu'),
        ('kueue.local_queue.pending_workloads', 'namespace:team-a'),
        ('kueue.local_queue.pending_workloads', 'status:active'),
    )
    for metric, tag in expected_metric_tags:
        aggregator.assert_metric_has_tag(metric, tag)
    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        check_symmetric_inclusion=True,
    )


def test_resource_name_map(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    instance = {
        **instance,
        'resource_name_map': {
            'example.com/fpga': 'fpga',
            'nvidia.com/gpu': 'custom_gpu',
        },
    }

    check = KueueCheck('kueue', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('kueue.cluster_queue.resource_usage.cpu')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.gpu')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.memory')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.fpga')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.custom_gpu', count=0)
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'test:tag')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'kueue_cluster_queue:default')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'flavor:on-demand')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'replica_role:leader')


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='openmetrics_endpoint\\n  Field required',
    ):
        check = KueueCheck('kueue', {}, [{}])
        dd_run_check(check)
