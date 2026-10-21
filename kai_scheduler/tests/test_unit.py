# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.kai_scheduler import KaiSchedulerCheck

from .common import (
    BINDER_ENDPOINT,
    CHECK_NAME,
    QUEUE_CONTROLLER_ENDPOINT,
    SCHEDULER_ENDPOINT,
    get_fixture_path,
    live_metadata_metrics,
)

pytestmark = [pytest.mark.unit]

COMPONENT_BY_ENDPOINT = {
    SCHEDULER_ENDPOINT: 'scheduler',
    QUEUE_CONTROLLER_ENDPOINT: 'queue_controller',
    BINDER_ENDPOINT: 'binder',
}


@pytest.fixture
def mock_endpoints(mock_http_response_per_endpoint):
    mock_http_response_per_endpoint(
        {
            SCHEDULER_ENDPOINT: [MockResponse(file_path=get_fixture_path('scheduler.txt'))],
            QUEUE_CONTROLLER_ENDPOINT: [MockResponse(file_path=get_fixture_path('queue_controller.txt'))],
            BINDER_ENDPOINT: [MockResponse(file_path=get_fixture_path('binder.txt'))],
        }
    )


def endpoint_tags(endpoint: str) -> list[str]:
    return [f'endpoint:{endpoint}', f'kai_component:{COMPONENT_BY_ENDPOINT[endpoint]}', 'test:tag']


def test_check(dd_run_check, aggregator, instance, mock_endpoints):
    dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [instance]))

    metadata_metrics, config_gated = live_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_symmetric_inclusion=True, exclude=config_gated
    )

    for metric_name in aggregator.metric_names:
        for metric in aggregator.metrics(metric_name):
            endpoint = next(tag.removeprefix('endpoint:') for tag in metric.tags if tag.startswith('endpoint:'))
            components = [tag for tag in metric.tags if tag.startswith('kai_component:')]
            assert components == [f'kai_component:{COMPONENT_BY_ENDPOINT[endpoint]}'], (metric_name, metric.tags)


def test_unprefixed_scheduler_duplicates_are_ignored(dd_run_check, aggregator, instance, mock_endpoints):
    # The scheduler fixture has both `kai_e2e_scheduling_latency_milliseconds 2` and a stale
    # `e2e_scheduling_latency_milliseconds 0`; only the prefixed series must be reported.
    dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [instance]))

    aggregator.assert_metric(
        'kai.scheduling_cycle.latency.milliseconds', value=2, count=1, tags=endpoint_tags(SCHEDULER_ENDPOINT)
    )
    aggregator.assert_metric('kai.preemption.attempts.count', count=1)


def test_queue_metrics_share_units_and_tags(dd_run_check, aggregator, instance, mock_endpoints):
    dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [instance]))

    team_a = ['kai_queue:team-a', 'kai_queue_display_name:Team A']
    # The scheduler reports fair share memory in GB (0.067108864), while the queue-controller reports bytes.
    aggregator.assert_metric(
        'kai.queue.fair_share.memory', value=67108864, tags=[*endpoint_tags(SCHEDULER_ENDPOINT), *team_a]
    )
    aggregator.assert_metric('kai.queue.quota.cpu', value=1, tags=[*endpoint_tags(QUEUE_CONTROLLER_ENDPOINT), *team_a])
    # `team-b` has no display name, and `queue_name` is never reported.
    aggregator.assert_metric(
        'kai.queue.quota.cpu', value=0.5, tags=[*endpoint_tags(QUEUE_CONTROLLER_ENDPOINT), 'kai_queue:team-b']
    )


def evictions_payload(series: dict[tuple[str, str], int]) -> str:
    lines = ['# TYPE kai_pod_group_evicted_pods_total counter']
    for (podgroup, action), value in series.items():
        labels = f'action="{action}",namespace="default",nodepool="default",podgroup="{podgroup}",uid="{podgroup}-uid"'
        lines.append(f'kai_pod_group_evicted_pods_total{{{labels}}} {value}')
    return '\n'.join(lines) + '\n'


@pytest.mark.parametrize(
    'cache_size, scrapes, expected',
    [
        pytest.param(10, [{('a', 'preempt'): 3}], {'preempt': 0}, id='first scrape is a baseline'),
        pytest.param(
            10, [{('a', 'preempt'): 1}, {('a', 'preempt'): 3}], {'preempt': 2}, id='increase since last scrape'
        ),
        pytest.param(
            10,
            [{('a', 'preempt'): 1}, {('a', 'preempt'): 1, ('b', 'preempt'): 2}],
            {'preempt': 2},
            id='new series counts from zero',
        ),
        pytest.param(
            10,
            [
                {('a', 'preempt'): 1, ('b', 'preempt'): 1, ('c', 'reclaim'): 1},
                {('a', 'preempt'): 2, ('b', 'preempt'): 3, ('c', 'reclaim'): 2},
            ],
            {'preempt': 3, 'reclaim': 1},
            id='pod groups summed per action',
        ),
        pytest.param(10, [{('a', 'preempt'): 3}, {('a', 'preempt'): 1}], {'preempt': 1}, id='counter reset'),
        pytest.param(
            10,
            [{('a', 'preempt'): 2, ('b', 'preempt'): 2}, {('b', 'preempt'): 3}],
            {'preempt': 1},
            id='removed series does not decrease the sum',
        ),
        pytest.param(
            1,
            [
                {('a', 'preempt'): 1},
                {('a', 'preempt'): 1, ('b', 'preempt'): 1},
                {('a', 'preempt'): 2, ('b', 'preempt'): 1},
            ],
            {'preempt': 0},
            id='series evicted from a full cache are not counted again',
        ),
    ],
)
def test_evicted_pods(
    dd_run_check, aggregator, mock_http_response_per_endpoint, monkeypatch, cache_size, scrapes, expected
):
    monkeypatch.setattr('datadog_checks.kai_scheduler.evictions.CACHE_SIZE', cache_size)
    mock_http_response_per_endpoint(
        {SCHEDULER_ENDPOINT: [MockResponse(content=evictions_payload(series)) for series in scrapes]}
    )
    check = KaiSchedulerCheck(CHECK_NAME, {}, [{'scheduler_endpoint': SCHEDULER_ENDPOINT, 'tags': ['test:tag']}])

    for _ in scrapes:
        aggregator.reset()
        dd_run_check(check)

    for action, value in expected.items():
        tags = [
            *endpoint_tags(SCHEDULER_ENDPOINT),
            f'action:{action}',
            'kai_nodepool:default',
            'kube_namespace:default',
        ]
        aggregator.assert_metric('kai.evicted_pods.count', value=value, count=1, tags=tags)
    assert len(aggregator.metrics('kai.evicted_pods.count')) == len(expected)


def test_queue_controller_only(dd_run_check, aggregator, mock_endpoints):
    dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [{'queue_controller_endpoint': QUEUE_CONTROLLER_ENDPOINT}]))

    aggregator.assert_metric_has_tag('kai.queue.quota.cpu', 'kai_component:queue_controller')


def test_no_endpoint_raises(dd_run_check):
    with pytest.raises(Exception, match='Must specify at least one of the following'):
        dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [{}]))
