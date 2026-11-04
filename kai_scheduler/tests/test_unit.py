# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.stubs import datadog_agent
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

    metadata_metrics, config_gated, distributions = live_metadata_metrics()
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_symmetric_inclusion=True, exclude=config_gated
    )
    # Every histogram also submits its `.sum` counter, which identifies the submitted distributions.
    submitted_distributions = {
        name.removesuffix('.sum')
        for name in aggregator.metric_names
        if name.endswith('.sum') and aggregator.histogram_bucket(name.removesuffix('.sum'))
    }
    assert submitted_distributions == set(distributions)

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


def evictions_payload(series: dict[str, int]) -> str:
    """Render `kai_pod_group_evicted_pods_total`, keyed by `<podgroup>` or `<podgroup>/<action>` (default `preempt`)."""
    lines = ['# TYPE kai_pod_group_evicted_pods_total counter']
    for key, value in series.items():
        podgroup, _, action = key.partition('/')
        labels = (
            f'action="{action or "preempt"}",namespace="default",nodepool="default",'
            f'podgroup="{podgroup}",uid="{podgroup}-uid"'
        )
        lines.append(f'kai_pod_group_evicted_pods_total{{{labels}}} {value}')
    return '\n'.join(lines) + '\n'


def submitted_evictions(aggregator, instance_tags: list[str]) -> dict[str, float]:
    """Return the submitted `kai.evicted_pods.count` values by action, asserting one context per action."""
    submitted: dict[str, float] = {}
    for metric in aggregator.metrics('kai.evicted_pods.count'):
        action = next(tag.removeprefix('action:') for tag in metric.tags if tag.startswith('action:'))
        assert action not in submitted, f'more than one context for action `{action}`'
        assert sorted(metric.tags) == sorted(
            [
                f'endpoint:{SCHEDULER_ENDPOINT}',
                'kai_component:scheduler',
                *instance_tags,
                f'action:{action}',
                'kai_nodepool:default',
                'kube_namespace:default',
            ]
        )
        submitted[action] = metric.value
    return submitted


# Each case is a list of check runs: the scrape served to the run (`None` for a failed request) and the evictions
# that run must submit, by action. Cases with a cache size of 2 exercise the fallback to summed counters.
@pytest.mark.parametrize(
    'cache_size, runs',
    [
        pytest.param(10, [({'a': 3}, {'preempt': 0})], id='first scrape is a baseline'),
        pytest.param(10, [({'a': 1}, {'preempt': 0}), ({'a': 3}, {'preempt': 2})], id='increase since last scrape'),
        pytest.param(
            10, [({'a': 1}, {'preempt': 0}), ({'a': 1, 'b': 2}, {'preempt': 2})], id='new series counts from zero'
        ),
        pytest.param(
            10,
            [
                ({'a': 1, 'b': 1, 'c/reclaim': 1}, {'preempt': 0, 'reclaim': 0}),
                ({'a': 2, 'b': 3, 'c/reclaim': 2}, {'preempt': 3, 'reclaim': 1}),
            ],
            id='pod groups summed per action',
        ),
        pytest.param(10, [({'a': 3}, {'preempt': 0}), ({'a': 1}, {'preempt': 1})], id='counter reset'),
        pytest.param(
            10,
            [({'a': 2, 'b': 2}, {'preempt': 0}), ({'b': 3}, {'preempt': 1})],
            id='removed series does not decrease the sum',
        ),
        # KAI releases after v0.18.6 create each series at zero before the first eviction.
        pytest.param(10, [({'a': 0}, {'preempt': 0}), ({'a': 2}, {'preempt': 2})], id='zero series then evicted'),
        pytest.param(
            10,
            [({'a': 1}, {'preempt': 0}), (None, {}), ({'a': 3, 'b': 2}, {'preempt': 4})],
            id='failed scrape keeps the previous values',
        ),
        pytest.param(
            10,
            [(None, {}), ({'a': 3}, {'preempt': 0}), ({'a': 4}, {'preempt': 1})],
            id='first successful scrape is a baseline',
        ),
        pytest.param(
            2,
            [({'a': 1, 'b': 1, 'c': 1}, {'preempt': 0}), ({'a': 2, 'b': 1, 'c': 1, 'd': 1}, {'preempt': 2})],
            id='overflow on the first scrape is a baseline',
        ),
        pytest.param(
            2,
            [
                ({'a': 1, 'b': 1}, {'preempt': 0}),
                ({'a': 2, 'b': 1, 'c': 1}, {'preempt': 2}),
                ({'a': 3, 'b': 1, 'c': 1}, {'preempt': 1}),
            ],
            id='overflow reports the increase of the sums',
        ),
        pytest.param(
            2,
            [({'a': 1, 'b': 1, 'c': 5}, {'preempt': 0}), ({'a': 1, 'b': 1, 'd': 1, 'e': 1}, {'preempt': 0})],
            id='overflow never reports a decrease',
        ),
        # The second run fits again but its cache was cleared, so it still reports the sums while rebuilding the
        # cache; counting its series as new would report 3. The third run is exact; reusing values cached before the
        # overflow, or not caching during the second run, would report 3 or 5 instead of 2.
        pytest.param(
            2,
            [
                ({'a': 1, 'b': 1, 'c': 1}, {'preempt': 0}),
                ({'a': 2, 'b': 1}, {'preempt': 0}),
                ({'a': 3, 'b': 2}, {'preempt': 2}),
            ],
            id='exact counting resumes once the cache is rebuilt',
        ),
        # Zero series do not use the cache, so both runs are exact. Counting them would overflow the first run, and
        # the sums would hide the increase of `b` behind the removal of `c`.
        pytest.param(
            2,
            [({'a': 0, 'b': 1, 'c': 1}, {'preempt': 0}), ({'a': 0, 'b': 2}, {'preempt': 1})],
            id='zero series do not count toward the cache size',
        ),
        # `b` disappears and `c` is scraped before `a`. Caching `c` while `b` is still cached must not evict `a`, or
        # its whole counter would be reported again.
        pytest.param(
            2,
            [({'a': 1, 'b': 1}, {'preempt': 0}), ({'c': 1, 'a': 1}, {'preempt': 1})],
            id='new series do not evict current ones',
        ),
    ],
)
def test_evicted_pods(dd_run_check, aggregator, mock_http_response_per_endpoint, monkeypatch, cache_size, runs):
    monkeypatch.setattr('datadog_checks.kai_scheduler.evictions.CACHE_SIZE', cache_size)
    mock_http_response_per_endpoint(
        {
            SCHEDULER_ENDPOINT: [
                MockResponse(status_code=500) if series is None else MockResponse(content=evictions_payload(series))
                for series, _ in runs
            ]
        }
    )
    check = KaiSchedulerCheck(CHECK_NAME, {}, [{'scheduler_endpoint': SCHEDULER_ENDPOINT, 'tags': ['test:tag']}])

    for run, (series, expected) in enumerate(runs):
        aggregator.reset()
        if series is None:
            with pytest.raises(Exception):
                dd_run_check(check)
        else:
            dd_run_check(check)
        assert submitted_evictions(aggregator, ['test:tag']) == expected, f'run {run}'


def test_evicted_pods_keep_configured_tags(dd_run_check, aggregator, mock_http_response_per_endpoint):
    # A configured tag that shares its name with a dropped pod group label must not be dropped with it.
    mock_http_response_per_endpoint({SCHEDULER_ENDPOINT: [MockResponse(content=evictions_payload({'a': 1}))]})
    check = KaiSchedulerCheck(CHECK_NAME, {}, [{'scheduler_endpoint': SCHEDULER_ENDPOINT, 'tags': ['podgroup:mine']}])

    dd_run_check(check)

    assert submitted_evictions(aggregator, ['podgroup:mine']) == {'preempt': 0}


def test_queue_controller_only(dd_run_check, aggregator, mock_endpoints):
    dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [{'queue_controller_endpoint': QUEUE_CONTROLLER_ENDPOINT}]))

    aggregator.assert_metric_has_tag('kai.queue.quota.cpu', 'kai_component:queue_controller')


@pytest.mark.parametrize(
    'instance, error',
    [
        pytest.param({}, 'Must specify at least one of the following', id='no endpoint'),
        pytest.param(
            {'scheduler_endpoint': SCHEDULER_ENDPOINT, 'binder_endpoint': SCHEDULER_ENDPOINT},
            '`scheduler_endpoint`, `binder_endpoint` must be different endpoints',
            id='shared endpoint',
        ),
    ],
)
def test_invalid_endpoints_raise(dd_run_check, instance, error):
    with pytest.raises(Exception, match=error):
        dd_run_check(KaiSchedulerCheck(CHECK_NAME, {}, [instance]))


def test_skipped_when_gpu_monitoring_disabled(instance):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            KaiSchedulerCheck(CHECK_NAME, {}, [instance])
