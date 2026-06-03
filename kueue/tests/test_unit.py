# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kueue import KueueCheck
from datadog_checks.kueue.check import OTHER_RESOURCE_NAME, RESOURCE_NAME_MAP
from datadog_checks.kueue.metrics import LOCAL_QUEUE_METRIC_MAP, METRIC_MAP, RESOURCE_METRIC_MAP

from .common import TEST_METRICS, get_fixture_path


def test_mapped_metrics_are_in_metadata():
    mapped_metrics = set()
    mapped_metrics.update(_metadata_metric_name(metric_name) for metric_name in METRIC_MAP.values())
    mapped_metrics.update(_metadata_metric_name(metric_name) for metric_name in LOCAL_QUEUE_METRIC_MAP.values())

    resource_names = {OTHER_RESOURCE_NAME, *RESOURCE_NAME_MAP.values()}
    for metric_name in RESOURCE_METRIC_MAP.values():
        mapped_metrics.update(_metadata_metric_name(f'{metric_name}.{resource_name}') for resource_name in resource_names)

    assert mapped_metrics.issubset(set(get_metadata_metrics()))


def _metadata_metric_name(metric_name):
    if isinstance(metric_name, dict):
        metric_name = metric_name['name']

    return f'kueue.{metric_name}'


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    mock_http_response(file_path=get_fixture_path('metrics.txt'))

    check = KueueCheck('kueue', {}, [instance])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.gpu', 'kueue_cluster_queue:default')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_pending.gpu', 'kueue_cluster_queue:default')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.pending_workloads', 'kueue_cluster_queue:default')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.pending_workloads', 'status:inadmissible')
    aggregator.assert_metric_has_tag('kueue.resource_flavor.quota_reserved_workloads', 'kueue_cluster_queue:default')
    aggregator.assert_metric_has_tag('kueue.local_queue.pending_workloads', 'kueue_local_queue:gpu')
    aggregator.assert_metric_has_tag('kueue.local_queue.pending_workloads', 'namespace:team-a')
    aggregator.assert_metric_has_tag('kueue.local_queue.pending_workloads', 'status:active')
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


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
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.fpga')
    aggregator.assert_metric('kueue.cluster_queue.resource_usage.custom_gpu', count=0)
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'test:tag')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'kueue_cluster_queue:default')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'flavor:on-demand')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'replica_role:leader')
    aggregator.assert_metric_has_tag('kueue.cluster_queue.resource_usage.fpga', 'cohort:default')


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='openmetrics_endpoint\\n  Field required',
    ):
        check = KueueCheck('kueue', {}, [{}])
        dd_run_check(check)
