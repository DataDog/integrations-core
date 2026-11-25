# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import csv
import json
import os
from collections import defaultdict

import pytest

from datadog_checks.base.stubs import datadog_agent, tagger
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kueue import KueueCheck
from datadog_checks.kueue.goodput import (
    BADPUT_METRIC,
    FULLY_ADMITTED_METRIC,
    KUEUE_MESSAGE_CATEGORIES,
    KUEUE_REASON_CATEGORIES,
    Category,
    GoodputTracker,
    QueueKey,
    SchedulingState,
    aggregate,
    badput_by_reason,
    blocking_condition,
    classify,
    extract_gpu_type,
    normalize_reason,
    observe,
    pod_gpu_type,
    queue_tags,
    requested_gpu_type,
    requested_gpus,
    workload_points,
)

from .common import get_fixture_path
from .goodput_scenarios import A100, H100, SCENARIOS, Clock, markdown_tables, run, workload

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def reset_persistent_cache():
    datadog_agent.reset()


@pytest.mark.parametrize(
    ('state', 'expected'),
    [
        ('pending_quota', SchedulingState.WAITING),
        ('quota_reserved', SchedulingState.WAITING),
        ('admitted_pods_pending', SchedulingState.WAITING),
        ('admitted_no_podsready', SchedulingState.READINESS_UNKNOWN),
        ('pending_no_podsready', SchedulingState.READINESS_UNKNOWN),
        ('running', SchedulingState.RUNNABLE),
        ('recovering', SchedulingState.RECOVERING),
        ('preempted', SchedulingState.PREEMPTED),
        ('finished', SchedulingState.FINISHED),
    ],
)
def test_classify(state, expected):
    assert classify(workload('w', state, 1, finished_at=0)) == expected


def test_classify_inactive():
    assert classify(workload('w', 'pending_quota', 1, active=False)) == SchedulingState.INACTIVE


def test_pods_ready_without_admission_is_not_runnable():
    w = workload('w', 'running', 1)
    for condition in w['status']['conditions']:
        if condition['type'] == 'Admitted':
            condition['status'] = 'False'
    assert classify(w) == SchedulingState.WAITING


def test_requested_gpus_sums_pod_sets_and_uses_requests_or_limits():
    w = workload('w', 'running', 4, pods=2)
    w['spec']['podSets'].append(
        {
            'name': 'workers',
            'count': 3,
            'template': {
                'spec': {
                    'containers': [
                        {'name': 'a', 'resources': {'requests': {'nvidia.com/gpu': '2'}}},
                        {'name': 'b', 'resources': {'requests': {'cpu': '1'}}},
                    ],
                    # A regular init container only raises the request if it needs more than the app containers.
                    'initContainers': [{'name': 'init', 'resources': {'limits': {'nvidia.com/gpu': 1}}}],
                }
            },
        }
    )
    assert requested_gpus(w) == 2 * 4 + 3 * 2


def test_requested_gpus_skips_reclaimable_pods():
    # Kueue counts completed pods as ready; their GPUs are released, so only the pods still needed count.
    w = workload('w', 'running', 3, pods=2)
    w['status']['reclaimablePods'] = [{'name': 'main', 'count': 1}]
    assert requested_gpus(w) == 3
    w['status']['reclaimablePods'] = [{'name': 'other', 'count': 2}]
    assert requested_gpus(w) == 6
    w['status']['reclaimablePods'] = [{'name': 'main', 'count': 5}]
    assert requested_gpus(w) == 0


def test_completing_workload_is_not_badput():
    # Kueue reports `WaitForRecovery` for a few seconds while the pods of a completing Workload terminate.
    clock = Clock()
    tracker = GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)
    tracker.update([workload('w', 'running', 2)])
    clock.t = 15
    contributions = tracker.update([workload('w', 'recovering', 2)])
    assert [(c.category, c.gpu_seconds) for c in contributions] == [(Category.FULLY_ADMITTED, 30)]
    clock.t = 30
    assert tracker.update([workload('w', 'finished', 2, finished_at=17)]) == []


def test_finished_workload_with_all_pods_reclaimable_closes_its_last_interval():
    clock = Clock()
    tracker = GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)
    tracker.update([workload('w', 'running', 2, pods=2)])
    clock.t = 15
    done = workload('w', 'finished', 2, pods=2, finished_at=7)
    done['status']['reclaimablePods'] = [{'name': 'main', 'count': 2}]
    contributions = tracker.update([done])
    assert [(c.category, c.gpu_seconds) for c in contributions] == [(Category.FULLY_ADMITTED, 4 * 7)]


def test_requested_gpus_counts_sidecars_and_init_peak():
    w = workload('w', 'running', 1)
    w['spec']['podSets'][0]['template']['spec']['initContainers'] = [
        {'name': 'sidecar', 'restartPolicy': 'Always', 'resources': {'limits': {'nvidia.com/gpu': 1}}},
        {'name': 'warmup', 'resources': {'limits': {'nvidia.com/gpu': 4}}},
    ]
    # max(app 1 + sidecar 1, sidecar 1 + warmup 4)
    assert requested_gpus(w) == 5


def test_requested_gpus_rejects_unparseable_quantity():
    w = workload('w', 'running', '1k')
    with pytest.raises(ValueError):
        requested_gpus(w)


def make_tracker():
    clock = Clock()
    return clock, GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)


def test_first_observation_is_only_a_baseline():
    clock, tracker = make_tracker()
    clock.t = 1000
    assert tracker.update([workload('w', 'pending_quota', 4)]) == []


def test_unparseable_workload_is_skipped_not_guessed():
    clock, tracker = make_tracker()
    bad = workload('bad', 'pending_quota', 'many')
    tracker.update([bad, workload('ok', 'pending_quota', 1)])
    clock.t = 10
    contributions = tracker.update([bad, workload('ok', 'pending_quota', 1)])
    assert [c.name for c in contributions] == ['team-a/ok']


def test_non_gpu_workloads_are_ignored():
    clock, tracker = make_tracker()
    tracker.update([workload('cpu', 'pending_quota', 0)])
    clock.t = 10
    assert tracker.update([workload('cpu', 'pending_quota', 0)]) == []


def test_disappeared_workload_is_dropped_without_contribution():
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'running', 4)])
    clock.t = 10
    assert tracker.update([]) == []
    assert tracker.previous == {}
    clock.t = 20
    # Reappearing (for example with the same UID after a restore) is a new baseline.
    assert tracker.update([workload('w', 'running', 4)]) == []


def test_finished_workload_stops_contributing():
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'running', 4)])
    clock.t = 10
    assert [c.gpu_seconds for c in tracker.update([workload('w', 'finished', 4, finished_at=10)])] == [40]
    clock.t = 20
    assert tracker.update([workload('w', 'finished', 4, finished_at=10)]) == []


def test_finished_time_is_clamped_to_the_interval():
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'running', 1)])
    clock.t = 10
    # A Finished time in the future (clock skew) does not extend the interval,
    # and one in the past does not make it negative.
    assert tracker.update([workload('w', 'finished', 1, finished_at=30)])[0].seconds == 10
    tracker.update([workload('v', 'running', 1)])
    clock.t = 20
    assert tracker.update([workload('v', 'finished', 1, finished_at=-50)])[0].seconds == 0


def test_non_positive_interval_is_skipped():
    clock, tracker = make_tracker()
    clock.t = 10
    tracker.update([workload('w', 'pending_quota', 4)])
    clock.t = 10
    assert tracker.update([workload('w', 'pending_quota', 4)]) == []


def test_reset_forces_a_new_baseline():
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'pending_quota', 4)])
    tracker.reset()
    clock.t = 600
    assert tracker.update([workload('w', 'pending_quota', 4)]) == []
    clock.t = 610
    assert [c.gpu_seconds for c in tracker.update([workload('w', 'pending_quota', 4)])] == [40]


def test_contribution_uses_the_state_at_the_start_of_the_interval():
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'admitted_pods_pending', 2)])
    clock.t = 10
    [contribution] = tracker.update([workload('w', 'running', 2)])
    # The Workload only became ready during the interval, so it is still badput.
    assert contribution.category == Category.BADPUT


def test_queue_tags_reuse_existing_tags():
    assert queue_tags(QueueKey('team-a', 'gpu', 'a100-cq')) == [
        'job_scheduler:kueue',
        'kube_namespace:team-a',
        'kueue_local_queue:gpu',
        'kueue_cluster_queue:a100-cq',
        'job_scheduler_queue:a100-cq',
    ]
    assert queue_tags(QueueKey('team-a', 'gpu', None)) == [
        'job_scheduler:kueue',
        'kube_namespace:team-a',
        'kueue_local_queue:gpu',
    ]


def test_aggregate_reports_both_totals_per_queue():
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'pending_quota', 4)])
    clock.t = 10
    totals = aggregate(tracker.update([workload('w', 'pending_quota', 4)]))
    assert totals[QueueKey('team-a', 'gpu', None)] == (40, 0)
    assert totals[QueueKey('team-a', 'gpu', None)].goodput == 0


@pytest.mark.parametrize('scenario', SCENARIOS, ids=[s.name for s in SCENARIOS])
def test_scenario(scenario):
    rows, totals = run(scenario)
    failed = [row for row in rows if not row.passed]
    assert not failed, failed
    assert totals == scenario.expected_queues


def test_scenario_goodput_ratios():
    totals = {s.name: run(s)[1] for s in SCENARIOS}
    assert totals['multiple_workloads_one_queue'][A100] == (60, 100)
    assert totals['multiple_workloads_one_queue'][A100][1] / sum(totals['multiple_workloads_one_queue'][A100]) == 0.625
    assert set(totals['multiple_queues']) == {A100, H100}
    assert totals['multiple_queues'][A100] == (40, 40)
    assert totals['multiple_queues'][H100] == (80, 0)


def test_quota_exhausted_goodput_decreases_as_waiting_grows():
    scenario = next(s for s in SCENARIOS if s.name == 'kueue_quota_exhausted')
    clock, tracker = make_tracker()
    ratios = []
    cumulative = [0.0, 0.0]
    for poll in scenario.polls:
        clock.t = poll.t
        totals = aggregate(tracker.update(poll.workloads, lambda ns, lq: 'a100-cq'))
        if A100 in totals:
            cumulative[0] += totals[A100].badput
            cumulative[1] += totals[A100].fully_admitted
            ratios.append(cumulative[1] / sum(cumulative))
    assert ratios == [80 / 120, 160 / 280]
    assert ratios[1] < ratios[0]


def test_scenario_tables():
    # Prints the validation tables with `-s`.
    tables = markdown_tables()
    print(tables)
    assert 'FAIL' not in tables


def test_preempted_time_is_badput():
    # A preempted Workload goes back to waiting for quota, so it contributes badput until it runs again.
    clock, tracker = make_tracker()
    tracker.update([workload('w', 'running', 4)])
    clock.t = 10
    [running] = tracker.update([workload('w', 'preempted', 4)])
    clock.t = 20
    [preempted] = tracker.update([workload('w', 'running', 4)])
    clock.t = 30
    [resumed] = tracker.update([workload('w', 'running', 4)])

    assert (running.category, running.gpu_seconds) == (Category.FULLY_ADMITTED, 40)
    assert (preempted.state, preempted.category, preempted.gpu_seconds) == (
        SchedulingState.PREEMPTED,
        Category.BADPUT,
        40,
    )
    assert (resumed.category, resumed.gpu_seconds) == (Category.FULLY_ADMITTED, 40)


class FakeKubernetesAPIClient:
    def __init__(self, *snapshots):
        self.snapshots = list(snapshots)

    def list_workloads(self, namespace=None):
        snapshot = self.snapshots.pop(0)
        if isinstance(snapshot, Exception):
            raise snapshot
        return snapshot


def goodput_check(instance, *snapshots, **config):
    check = KueueCheck('kueue', {}, [{**instance, 'collect_scheduling_goodput': True, **config}])
    check.kube_client = FakeKubernetesAPIClient(*snapshots)
    clock = Clock()
    check.goodput.monotonic = clock.monotonic
    check.goodput.wall = clock.wall
    return check, clock


A100_TAGS = [
    'job_scheduler:kueue',
    'kube_namespace:team-a',
    'kueue_local_queue:gpu',
    'kueue_cluster_queue:a100-cq',
    'job_scheduler_queue:a100-cq',
]


def test_check_submits_one_series_per_workload(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    # The pending Workload has no admission, so its ClusterQueue comes from the tagger.
    tagger.set_tags(
        {
            'kubernetes_kueue_queue://localqueue/team-a/gpu': [
                'kueue_local_queue:gpu',
                'kueue_cluster_queue:a100-cq',
            ]
        }
    )
    snapshot = [workload('run', 'running', 8), workload('wait', 'pending_quota', 4)]
    check, clock = goodput_check(instance, snapshot, snapshot)

    dd_run_check(check)
    aggregator.assert_metric(BADPUT_METRIC, count=0)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, count=0)

    clock.t = 15
    dd_run_check(check)
    # One series per Workload, in GPU-hours: 4 GPUs waiting and 8 GPUs running over 15 seconds. Each Workload also
    # submits the other metric as 0, so that the goodput of any group is defined.
    wait_tags = [*A100_TAGS, 'kueue_workload:wait', 'job_scheduler_workload:wait']
    run_tags = [*A100_TAGS, 'kueue_workload:run', 'job_scheduler_workload:run']
    badput_tags = [*wait_tags, 'reason:quota_or_capacity', 'scheduler_reason:WaitingForQuota']
    aggregator.assert_metric(BADPUT_METRIC, value=60 / 3600, tags=badput_tags, metric_type=aggregator.COUNT, count=1)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=0, tags=wait_tags, count=1)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=120 / 3600, tags=run_tags, count=1)
    aggregator.assert_metric(BADPUT_METRIC, value=0, tags=run_tags, count=1)
    # Nothing else: one series per Workload and metric.
    assert len(aggregator.metrics(BADPUT_METRIC)) == 2
    assert len(aggregator.metrics(FULLY_ADMITTED_METRIC)) == 2


def test_check_goodput_is_off_by_default(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    check = KueueCheck('kueue', {}, [instance])
    snapshot = [workload('run', 'running', 8)]
    check.kube_client = FakeKubernetesAPIClient(snapshot, snapshot)
    dd_run_check(check)
    dd_run_check(check)
    aggregator.assert_metric(BADPUT_METRIC, count=0)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, count=0)


def test_check_goodput_without_workload_events(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, snapshot, collect_workload_events=False)
    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=120 / 3600, count=1)
    assert not aggregator.events


def test_check_api_failure_resets_baseline(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, RuntimeError('API down'), snapshot, snapshot)

    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    clock.t = 600
    dd_run_check(check)
    # The 585s around the failed poll were not observed and are not attributed.
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, count=0)
    clock.t = 615
    dd_run_check(check)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=120 / 3600, count=1)


def test_check_follower_tracks_state_without_submitting(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics_follower.txt'))
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, snapshot, snapshot)

    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, count=0)

    # Once promoted, the first poll submits the interval since the last follower poll, not since its own baseline.
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    clock.t = 30
    dd_run_check(check)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=120 / 3600, count=1)


@pytest.mark.parametrize(
    'state, condition, expected',
    [
        pytest.param(
            SchedulingState.WAITING, {'reason': 'WaitingForQuota'}, 'quota_or_capacity', id='structured_quota'
        ),
        pytest.param(SchedulingState.WAITING, {'reason': 'ExceedsMaxQuota'}, 'quota_or_capacity', id='structured_max'),
        pytest.param(SchedulingState.WAITING, {'reason': 'WaitForStart'}, 'startup_or_system', id='pods_not_ready'),
        pytest.param(
            SchedulingState.WAITING,
            {'reason': 'UnsatisfiedAdmissionChecks'},
            'startup_or_system',
            id='admission_checks',
        ),
        # Without the UnadmittedWorkloadsObservability feature gate, Kueue v0.18 only reports `Pending`.
        pytest.param(
            SchedulingState.WAITING,
            {
                'reason': 'Pending',
                'message': "couldn't assign flavors to pod set main: insufficient unused quota for nvidia.com/gpu in "
                'flavor a100, 2 more needed',
            },
            'quota_or_capacity',
            id='pending_quota_message',
        ),
        pytest.param(
            SchedulingState.WAITING,
            {
                'reason': 'Pending',
                'message': "couldn't assign flavors to pod set main: insufficient quota for nvidia.com/gpu in flavor "
                'a100, previously considered podsets requests (0) + current podset request (16) > maximum capacity (4)',
            },
            'quota_or_capacity',
            id='pending_max_capacity_message',
        ),
        pytest.param(
            SchedulingState.WAITING,
            {'reason': 'Pending', 'message': 'something new'},
            'other_or_unknown',
            id='other_or_unknown',
        ),
        pytest.param(SchedulingState.WAITING, {'reason': 'UnsatisfiedChecks'}, 'startup_or_system', id='checks'),
        pytest.param(
            SchedulingState.WAITING,
            {'reason': 'NoReservationUnsatisfiedChecks'},
            'startup_or_system',
            id='checks_without_reservation',
        ),
        pytest.param(SchedulingState.WAITING, None, 'other_or_unknown', id='no_condition'),
        pytest.param(SchedulingState.PREEMPTED, {'reason': 'InClusterQueue'}, 'preemption_or_reclaim', id='preempted'),
        pytest.param(SchedulingState.RUNNABLE, None, None, id='not_badput'),
    ],
)
def test_normalize_reason(state, condition, expected):
    assert normalize_reason(state, condition) == expected


def test_badput_is_split_by_reason():
    clock = Clock()
    tracker = GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)
    snapshot = [
        workload('quota', 'pending_quota', 4),
        workload('max', 'pending_max_quota', 16),
        workload('pods', 'admitted_pods_pending', 2),
        workload('run', 'running', 8),
    ]
    tracker.update(snapshot)
    clock.t = 10
    reasons = badput_by_reason(tracker.update(snapshot))
    assert reasons[QueueKey('team-a', 'gpu', None)] == {
        ('quota_or_capacity', 'WaitingForQuota'): 40,
        ('quota_or_capacity', 'ExceedsMaxQuota'): 160,
    }
    assert reasons[QueueKey('team-a', 'gpu', 'a100-cq')] == {('startup_or_system', 'WaitForStart'): 20}


def test_check_submits_zero_badput_without_reason(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, snapshot)
    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    run_tags = [*A100_TAGS, 'kueue_workload:run', 'job_scheduler_workload:run']
    aggregator.assert_metric(BADPUT_METRIC, value=0, tags=run_tags, count=1)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=120 / 3600, tags=run_tags, count=1)


def test_evicted_workload_is_not_runnable_while_pods_are_still_ready():
    # Kueue evicts before it removes the admission, so `Admitted` and `PodsReady` can still be True for a moment.
    w = workload('w', 'running', 1)
    w['status']['conditions'].append({'type': 'Evicted', 'status': 'True', 'reason': 'Preempted'})
    assert classify(w) == SchedulingState.PREEMPTED
    w['status']['conditions'][-1]['reason'] = 'PodsReadyTimeout'
    assert classify(w) == SchedulingState.WAITING
    # Kueue sets `Evicted=False` when it admits the Workload again.
    w['status']['conditions'][-1]['status'] = 'False'
    assert classify(w) == SchedulingState.RUNNABLE


def test_check_scrape_failure_resets_the_baseline(dd_run_check, aggregator, instance, mock_http_response):
    snapshot = [workload('wait', 'pending_quota', 4)]
    check, clock = goodput_check(instance, snapshot, snapshot)
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    dd_run_check(check)
    clock.t = 15
    mock_http_response(status_code=500)
    with pytest.raises(Exception):
        dd_run_check(check)
    assert check.goodput.previous is None
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    clock.t = 600
    dd_run_check(check)
    # The run after the outage only sets a new baseline instead of attributing the whole outage.
    aggregator.assert_metric(BADPUT_METRIC, count=0)


def test_check_goodput_failure_does_not_fail_the_run(
    dd_run_check, aggregator, instance, mock_http_response, caplog, mocker
):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('wait', 'pending_quota', 4)]
    check, clock = goodput_check(instance, snapshot, snapshot, snapshot)
    dd_run_check(check)
    assert check.goodput.previous

    clock.t = 15
    original_update = check.goodput.update
    check.goodput.update = mocker.Mock(side_effect=RuntimeError('bug'))
    events = mocker.spy(check, 'collect_workload_events_from_api')
    with caplog.at_level('WARNING'):
        dd_run_check(check)
    assert check.goodput.previous is None
    assert 'Cannot collect Kueue scheduling goodput: bug' in caplog.text
    # Workload events still ran on the same run.
    events.assert_called_once()

    check.goodput.update = original_update
    clock.t = 30
    dd_run_check(check)
    # After the failure the next run only sets a new baseline.
    aggregator.assert_metric(BADPUT_METRIC, count=0)


def test_evicted_workload_reason_comes_from_the_eviction():
    w = workload('w', 'running', 1)
    w['status']['conditions'].append({'type': 'Evicted', 'status': 'True', 'reason': 'PodsReadyTimeout'})
    condition = blocking_condition(w, SchedulingState.WAITING)
    assert condition['reason'] == 'PodsReadyTimeout'
    assert normalize_reason(SchedulingState.WAITING, condition) == 'startup_or_system'
    w['status']['conditions'][-1]['reason'] = 'ClusterQueueStopped'
    assert (
        normalize_reason(SchedulingState.WAITING, blocking_condition(w, SchedulingState.WAITING))
        == 'configuration_or_request'
    )


def test_per_workload_series_sum_to_the_right_totals_for_any_grouping():
    """18 Workloads in 3 queues, some at the same time and some at different times, each waiting then running.

    Summing the per-Workload points by queue, by reason, by Workload, or all of them, must give the GPU-hours computed
    from each Workload's own timeline, as a query that sums the series by any tag would.
    """
    queues = ['a100-cq', 'h100-cq', 'l4-cq']
    # Waiting for admission checks, or admitted with pods not ready yet: two different reasons.
    waiting_states = {'quota_reserved': 'startup_or_system', 'admitted_pods_pending': 'startup_or_system'}
    # name -> (queue, GPUs, waiting state, created poll, admitted poll, finished poll), in 10-second polls.
    timelines = {
        f'w{i}': (queues[i % 3], 1 + i % 4, list(waiting_states)[i % 2], i % 5, i % 5 + 1 + i % 3, i % 5 + 3 + i % 4)
        for i in range(18)
    }
    clock = Clock()
    tracker = GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)
    sums = defaultdict(float)
    for poll in range(12):
        clock.t = poll * 10
        snapshot = []
        for name, (queue, gpus, waiting, created, admitted, finished) in timelines.items():
            if poll < created:
                continue
            if poll >= finished:
                # Finished exactly at the poll: the last interval runs until then.
                snapshot.append(workload(name, 'finished', gpus, cluster_queue=queue, finished_at=finished * 10))
            elif poll >= admitted:
                snapshot.append(workload(name, 'running', gpus, cluster_queue=queue))
            else:
                snapshot.append(workload(name, waiting, gpus, cluster_queue=queue))
        for metric, value, tags in workload_points(tracker.update(snapshot)):
            assert sum(t.startswith('kueue_workload:') for t in tags) == 1
            tag = dict(t.split(':', 1) for t in tags)
            sums[(metric, 'queue', tag['kueue_cluster_queue'])] += value
            assert tag['job_scheduler_workload'] == tag['kueue_workload']
            sums[(metric, 'workload', tag['kueue_workload'])] += value
            sums[(metric, 'total', None)] += value
            if 'reason' in tag:
                sums[(metric, 'reason', tag['reason'])] += value

    expected = defaultdict(float)
    for name, (queue, gpus, waiting, created, admitted, finished) in timelines.items():
        badput = gpus * (admitted - created) * 10 / 3600
        fully_admitted = gpus * (finished - admitted) * 10 / 3600
        for key in (('queue', queue), ('workload', name), ('total', None)):
            expected[(BADPUT_METRIC, *key)] += badput
            expected[(FULLY_ADMITTED_METRIC, *key)] += fully_admitted
        expected[(BADPUT_METRIC, 'reason', waiting_states[waiting])] += badput
    assert sums.keys() == expected.keys()
    for key in expected:
        assert sums[key] == pytest.approx(expected[key]), key


def test_cluster_queue_is_kept_once_known():
    clock = Clock()
    tracker = GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)
    tracker.update([workload('w', 'running', 2)])
    clock.t = 10
    # Requeued: no admission any longer, and the tagger cannot resolve the LocalQueue.
    tracker.update([workload('w', 'pending_quota', 2)])
    clock.t = 20
    contributions = tracker.update([workload('w', 'pending_quota', 2)])
    assert [c.queue for c in contributions] == [QueueKey('team-a', 'gpu', 'a100-cq')]


def test_check_warns_once_when_the_cluster_queue_is_unknown(
    dd_run_check, aggregator, instance, mock_http_response, caplog
):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('wait', 'pending_quota', 4)]
    check, clock = goodput_check(instance, *[snapshot] * 4)
    with caplog.at_level('WARNING'):
        # Right after the Agent starts the tagger may not know the LocalQueue yet, so the first polls don't warn.
        for t in (0, 15):
            clock.t = t
            dd_run_check(check)
        assert 'is unknown' not in caplog.text
        for t in (30, 45):
            clock.t = t
            dd_run_check(check)
    assert caplog.text.count('the ClusterQueue of 1 GPU Workloads that are not admitted yet is unknown') == 1
    # Its badput is still submitted, with the LocalQueue but without a ClusterQueue tag.
    aggregator.assert_metric_has_tag(BADPUT_METRIC, 'kueue_local_queue:gpu')
    assert not any(
        tag.startswith('kueue_cluster_queue:') for stub in aggregator.metrics(BADPUT_METRIC) for tag in stub.tags
    )


def test_requeued_workload_reason_comes_from_quota_once_it_waits_for_it():
    # Kueue keeps `Evicted=True` until it admits the Workload again; once it waits for quota, that is the reason.
    w = workload('w', 'pending_quota', 1)
    w['status']['conditions'].append({'type': 'Evicted', 'status': 'True', 'reason': 'PodsReadyTimeout'})
    assert (
        normalize_reason(SchedulingState.WAITING, blocking_condition(w, SchedulingState.WAITING)) == 'quota_or_capacity'
    )


def test_check_warns_once_without_pods_ready(dd_run_check, instance, mock_http_response, caplog):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('w', 'admitted_no_podsready', 2)]
    check, clock = goodput_check(instance, snapshot, snapshot)
    with caplog.at_level('WARNING'):
        dd_run_check(check)
        clock.t = 15
        dd_run_check(check)
    assert caplog.text.count('Enable waitForPodsReady') == 1


def test_cpu_tail_after_gpu_pods_complete_counts_no_gpu_time():
    # The GPU pods completed and are reclaimable while a CPU-only PodSet still runs: the Workload needs no GPU.
    def with_cpu_pod_set(state, reclaimable):
        w = workload('w', state, 2, pods=2, finished_at=40 if state == 'finished' else None)
        w['spec']['podSets'].append(
            {'name': 'cpu', 'count': 1, 'template': {'spec': {'containers': [{'name': 'c', 'resources': {}}]}}}
        )
        if reclaimable:
            w['status']['reclaimablePods'] = [{'name': 'main', 'count': 2}]
        return w

    clock, tracker = make_tracker()
    tracker.update([with_cpu_pod_set('running', False)])
    clock.t = 15
    # The last GPU interval still counts the GPUs of the previous poll.
    contributions = tracker.update([with_cpu_pod_set('running', True)])
    assert [(c.category, c.gpu_seconds) for c in contributions] == [(Category.FULLY_ADMITTED, 4 * 15)]
    clock.t = 30
    assert tracker.update([with_cpu_pod_set('running', True)]) == []
    clock.t = 45
    assert tracker.update([with_cpu_pod_set('finished', True)]) == []


def test_check_metrics_match_the_gpu_metadata(dd_run_check, aggregator, instance, mock_http_response):
    # The goodput metrics are shared by the scheduler integrations, so they are documented in the GPU integration.
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, snapshot)
    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    gpu_metadata = os.path.join(os.path.dirname(__file__), '..', '..', 'gpu', 'metadata.csv')
    with open(gpu_metadata) as f:
        metadata = {row['metric_name']: row for row in csv.DictReader(f)}
    aggregator.assert_metric(FULLY_ADMITTED_METRIC)
    aggregator.assert_metrics_using_metadata({**get_metadata_metrics(), **metadata}, check_submission_type=True)


def test_requested_gpus_uses_the_admitted_pods_with_partial_admission():
    # Kueue admitted 4 of the 8 pods the spec asks for, and the Workload runs with those.
    w = workload('w', 'running', 2, pods=8)
    w['status']['admission']['podSetAssignments'] = [{'name': 'main', 'count': 4}]
    assert requested_gpus(w) == 8
    w['status']['reclaimablePods'] = [{'name': 'main', 'count': 1}]
    assert requested_gpus(w) == 6


def test_check_submits_nothing_without_pods_ready(dd_run_check, aggregator, instance, mock_http_response):
    # Without `waitForPodsReady`, Workloads never get `PodsReady`: only the waits could be counted, and every group
    # that ever waited would report a goodput of 0.
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    without_pods_ready = [workload('run', 'admitted_no_podsready', 2), workload('wait', 'pending_no_podsready', 2)]
    with_pods_ready = [workload('run', 'running', 2), workload('wait', 'pending_quota', 2)]
    check, clock = goodput_check(instance, without_pods_ready, without_pods_ready, with_pods_ready, with_pods_ready)
    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    aggregator.assert_metric(BADPUT_METRIC, count=0)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, count=0)

    # Once a Workload reports `PodsReady`, the check submits again.
    for t in (30, 45):
        clock.t = t
        dd_run_check(check)
    aggregator.assert_metric(
        FULLY_ADMITTED_METRIC, value=30 / 3600, tags=[*A100_TAGS, 'kueue_workload:run', 'job_scheduler_workload:run']
    )


def test_check_submits_nothing_for_short_workloads_without_pods_ready(
    dd_run_check, aggregator, instance, mock_http_response, caplog
):
    # Without `waitForPodsReady`, a Workload that waits, then runs and finishes within one poll interval is never
    # seen admitted twice in a row, but its waits must not be submitted as a goodput of 0 either.
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    finished = workload('w', 'admitted_no_podsready', 2)
    finished['status']['conditions'].append(workload('w', 'finished', 2, finished_at=40)['status']['conditions'][-1])
    polls = [
        [workload('w', 'pending_no_podsready', 2)],
        [workload('w', 'pending_no_podsready', 2)],
        [workload('w', 'admitted_no_podsready', 2)],
        [finished],
    ]
    check, clock = goodput_check(instance, *polls)
    with caplog.at_level('WARNING'):
        for t in (0, 15, 30, 45):
            clock.t = t
            dd_run_check(check)
    aggregator.assert_metric(BADPUT_METRIC, count=0)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, count=0)
    assert caplog.text.count('Enable waitForPodsReady') == 1


def test_workloads_created_after_pods_ready_is_disabled_are_not_counted():
    # Disabling `waitForPodsReady` leaves the condition on the Workloads that already had it, but not on new ones.
    clock, tracker = make_tracker()
    snapshot = [workload('old', 'running', 2), workload('new', 'pending_no_podsready', 2)]
    tracker.update(snapshot)
    clock.t = 15
    contributions = tracker.update(snapshot)
    assert [(c.name, c.category, c.gpu_seconds) for c in contributions] == [
        ('team-a/old', Category.FULLY_ADMITTED, 2 * 15)
    ]


def test_check_leaves_instance_tags_off(dd_run_check, aggregator, instance, mock_http_response):
    # Autodiscovery copies the tags of the controller pod into the instance tags, such as its `kube_namespace`.
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, snapshot, tags=['kube_namespace:kueue-system', 'pod_name:kueue-0'])
    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)
    aggregator.assert_metric(
        FULLY_ADMITTED_METRIC,
        value=120 / 3600,
        tags=[*A100_TAGS, 'kueue_workload:run', 'job_scheduler_workload:run'],
        count=1,
    )


# The Workloads below are the ones of a kind cluster running Kueue v0.20.7 with `waitForPodsReady`, with GPU requests
# instead of the CPU ones of the cluster. `job-r-high` is admitted and waits for its pod; `job-r-low` was preempted
# and waits for quota again (`Evicted=True`, `QuotaReserved=False` with `WaitingForQuota`).
def kind_workloads():
    with open(get_fixture_path('workloads/kind_v0_20.json')) as f:
        return {w['metadata']['name'].rsplit('-', 1)[0]: w for w in json.load(f)}


def badput_tags(contributions):
    """Return the tags of the badput points, which hold the reason and GPU type."""
    return [tags for metric, value, tags in workload_points(contributions) if metric == BADPUT_METRIC and value]


def test_kind_admitted_but_unable_to_run_keeps_badput_until_the_pods_are_ready():
    # Kueue admitted the Workload, but its pod is not ready yet: `Admitted=True`, `PodsReady=False/WaitForStart`.
    clock, tracker = make_tracker()
    admitted = kind_workloads()['job-r-high']
    assert classify(admitted) == SchedulingState.WAITING
    tracker.update([admitted])
    clock.t = 10
    [contribution] = tracker.update([admitted])

    assert (contribution.category, contribution.gpu_seconds) == (Category.BADPUT, 40)
    [tags] = badput_tags([contribution])
    assert 'reason:startup_or_system' in tags
    assert 'scheduler_reason:WaitForStart' in tags

    ready = copy.deepcopy(admitted)
    ready['status']['conditions'] = [
        c if c['type'] != 'PodsReady' else {**c, 'status': 'True', 'reason': 'Started'}
        for c in ready['status']['conditions']
    ]
    clock.t = 20
    [still_waiting] = tracker.update([ready])
    clock.t = 30
    [running] = tracker.update([ready])
    assert still_waiting.category == Category.BADPUT
    assert (running.category, running.gpu_seconds) == (Category.FULLY_ADMITTED, 40)


def test_kind_preemption_is_tagged_preempted_until_the_scheduler_admits_again():
    clock, tracker = make_tracker()
    preempted = kind_workloads()['job-r-low']
    assert classify(preempted) == SchedulingState.PREEMPTED
    tracker.update([preempted])
    clock.t = 10
    [contribution] = tracker.update([preempted])
    [tags] = badput_tags([contribution])
    # The raw reason is the one of the `Preempted` condition, not the `WaitingForQuota` of the requeue.
    assert {'reason:preemption_or_reclaim', 'scheduler_reason:InClusterQueue'} <= set(tags)

    # Kueue admits it again: `Evicted` becomes False, and the pods are not ready yet, so the badput continues, but it
    # is not a preemption wait any longer.
    readmitted = copy.deepcopy(preempted)
    readmitted['status']['admission'] = {'clusterQueue': 'cq-main', 'podSetAssignments': []}
    readmitted['status']['conditions'] = [
        {'type': 'QuotaReserved', 'status': 'True', 'reason': 'QuotaReserved'},
        {'type': 'Evicted', 'status': 'False', 'reason': 'QuotaReserved'},
        {'type': 'Admitted', 'status': 'True', 'reason': 'Admitted'},
        {'type': 'PodsReady', 'status': 'False', 'reason': 'WaitForStart'},
    ]
    clock.t = 20
    [wait] = tracker.update([readmitted])
    clock.t = 30
    [after_admission] = tracker.update([readmitted])
    assert wait.cause == 'preemption_or_reclaim'
    assert (after_admission.category, after_admission.cause) == (Category.BADPUT, 'startup_or_system')


def test_kind_quota_exhausted_is_tagged_with_the_reason_and_the_gpu_type():
    clock, tracker = make_tracker()
    pending = copy.deepcopy(kind_workloads()['job-r-low'])
    # A new Workload, not an evicted one: Kueue only reports that it cannot reserve quota.
    pending['status']['conditions'] = [
        c for c in pending['status']['conditions'] if c['type'] in ('QuotaReserved', 'PodsReady')
    ]
    tracker.update([pending])
    clock.t = 10
    [contribution] = tracker.update([pending])

    [tags] = badput_tags([contribution])
    assert {'reason:quota_or_capacity', 'scheduler_reason:WaitingForQuota', 'gpu_type:a100'} <= set(tags)


@pytest.mark.parametrize(
    ('label', 'expected'),
    [
        ('NVIDIA-A100-SXM4-80GB', 'a100'),
        ('NVIDIA-H100-80GB-HBM3', 'h100'),
        ('NVIDIA-A10G', 'a10'),
        ('NVIDIA-L40S', 'l40'),
        ('Tesla-T4', 't4'),
        ('NVIDIA-GeForce-RTX-4090', 'rtx_4090'),
        ('AMD-Instinct-MI300X', 'mi300x'),
        ('something-else', None),
        ('', None),
        (None, None),
    ],
)
def test_extract_gpu_type(label, expected):
    assert extract_gpu_type(label) == expected


def affinity(*terms):
    return {
        'affinity': {
            'nodeAffinity': {
                'requiredDuringSchedulingIgnoredDuringExecution': {
                    'nodeSelectorTerms': [
                        {'matchExpressions': [{'key': 'nvidia.com/gpu.product', 'operator': 'In', 'values': values}]}
                        for values in terms
                    ]
                }
            }
        }
    }


@pytest.mark.parametrize(
    ('pod_spec', 'expected'),
    [
        pytest.param({}, None, id='unconstrained'),
        pytest.param({'nodeSelector': {'nvidia.com/gpu.product': 'NVIDIA-A100-SXM4-80GB'}}, 'a100', id='selector'),
        pytest.param({'nodeSelector': {'disktype': 'ssd'}}, None, id='other_selector'),
        pytest.param(affinity(['NVIDIA-H100-80GB-HBM3']), 'h100', id='affinity'),
        pytest.param(affinity(['NVIDIA-A100-SXM4-40GB', 'NVIDIA-A100-SXM4-80GB']), 'a100', id='same_model_values'),
        pytest.param(affinity(['NVIDIA-A100-SXM4-80GB'], ['NVIDIA-A100-SXM4-40GB']), 'a100', id='same_model_terms'),
        pytest.param(affinity(['NVIDIA-A100-SXM4-80GB', 'NVIDIA-H100-80GB-HBM3']), None, id='several_models'),
        pytest.param(affinity(['NVIDIA-A100-SXM4-80GB'], ['NVIDIA-H100-80GB-HBM3']), None, id='different_terms'),
    ],
)
def test_pod_gpu_type(pod_spec, expected):
    assert pod_gpu_type(pod_spec) == expected


def test_requested_gpu_type_ignores_non_gpu_pod_sets():
    gpu = {
        'containers': [{'resources': {'limits': {'nvidia.com/gpu': 1}}}],
        'nodeSelector': {'nvidia.com/gpu.product': 'NVIDIA-H100'},
    }
    cpu = {'containers': [{'resources': {'requests': {'cpu': 1}}}]}
    other = {
        'containers': [{'resources': {'limits': {'nvidia.com/gpu': 1}}}],
        'nodeSelector': {'nvidia.com/gpu.product': 'NVIDIA-A100'},
    }

    def with_pod_sets(*specs):
        return {
            'spec': {'podSets': [{'name': f'ps{i}', 'count': 1, 'template': {'spec': s}} for i, s in enumerate(specs)]}
        }

    assert requested_gpu_type(with_pod_sets(gpu, cpu)) == 'h100'
    assert requested_gpu_type(with_pod_sets(gpu, other)) is None
    assert requested_gpu_type(with_pod_sets(cpu)) is None


def test_gpu_type_comes_from_the_tagger_once_admitted_and_is_kept():
    workload_without_constraint = workload('w', 'running', 4)
    resolved = {}
    clock, tracker = make_tracker()
    # Pending: nothing says the model, so the tag is unset.
    pending = workload('w', 'pending_quota', 4)
    tracker.update([pending], None, lambda namespace, name: resolved.get((namespace, name)))
    clock.t = 10
    [unset] = tracker.update([pending], None, lambda namespace, name: resolved.get((namespace, name)))
    assert unset.gpu_type is None
    assert not any(tag.startswith('gpu_type:') for tag in badput_tags([unset])[0])

    # Admitted on an A100 flavor: the tagger knows the model from the flavor.
    resolved[('team-a', 'w')] = 'a100'
    clock.t = 20
    tracker.update([workload_without_constraint], None, lambda namespace, name: resolved.get((namespace, name)))
    clock.t = 30
    [admitted] = tracker.update(
        [workload_without_constraint], None, lambda namespace, name: resolved.get((namespace, name))
    )
    assert admitted.gpu_type == 'a100'

    # The tagger briefly loses it: the series keep the model.
    resolved.clear()
    clock.t = 40
    [kept] = tracker.update(
        [workload_without_constraint], None, lambda namespace, name: resolved.get((namespace, name))
    )
    assert kept.gpu_type == 'a100'
    fully_admitted = [
        tags for metric, value, tags in workload_points([kept]) if metric == FULLY_ADMITTED_METRIC and value
    ]
    assert 'gpu_type:a100' in fully_admitted[0]


def test_check_tags_the_series_with_the_gpu_type_from_the_tagger(
    dd_run_check, aggregator, instance, mock_http_response
):
    mock_http_response(file_path=get_fixture_path('metrics.txt'))
    tagger.set_tags({'kueue_workload://team-a/run': ['kueue_workload:run', 'gpu_type:a100']})
    snapshot = [workload('run', 'running', 8)]
    check, clock = goodput_check(instance, snapshot, snapshot)
    dd_run_check(check)
    clock.t = 15
    dd_run_check(check)

    run_tags = [*A100_TAGS, 'kueue_workload:run', 'job_scheduler_workload:run', 'gpu_type:a100']
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=120 / 3600, tags=run_tags, count=1)
    aggregator.assert_metric(BADPUT_METRIC, value=0, tags=run_tags, count=1)


@pytest.mark.parametrize(
    ('reason', 'expected'),
    [
        ('WaitingForQuota', 'quota_or_capacity'),
        ('ExceedsMaxQuota', 'quota_or_capacity'),
        ('NoMatchingFlavor', 'placement_or_topology'),
        ('TopologyPlacementFailed', 'placement_or_topology'),
        ('WaitingForPreemptedWorkloads', 'preemption_or_reclaim'),
        ('Misconfigured', 'configuration_or_request'),
        ('Suspended', 'other_or_unknown'),
        ('PendingEvaluation', 'other_or_unknown'),
        ('WaitingForPodsReady', 'startup_or_system'),
        ('DRAResourcesUnresolved', 'other_or_unknown'),
        ('UnrecordableResourceUsage', 'other_or_unknown'),
        ('SomethingNew', 'other_or_unknown'),
    ],
)
def test_every_quota_reserved_reason_of_the_design_doc_is_normalized(reason, expected):
    assert (
        normalize_reason(SchedulingState.WAITING, {'type': 'QuotaReserved', 'status': 'False', 'reason': reason})
        == expected
    )


# Every reason of the design doc, with its category, plus the reasons the check derives itself and one unknown.
KUEUE_CATEGORY_CASES = [
    ('WaitingForQuota', 'quota_or_capacity'),
    ('ExceedsMaxQuota', 'quota_or_capacity'),
    ('NoMatchingFlavor', 'placement_or_topology'),
    ('TopologyPlacementFailed', 'placement_or_topology'),
    ('WaitingForPreemptedWorkloads', 'preemption_or_reclaim'),
    ('Misconfigured', 'configuration_or_request'),
    ('WaitingForPodsReady', 'startup_or_system'),
    ('PendingEvaluation', 'other_or_unknown'),
    ('Suspended', 'other_or_unknown'),
    ('DRAResourcesUnresolved', 'other_or_unknown'),
    ('UnrecordableResourceUsage', 'other_or_unknown'),
    ('UnsatisfiedAdmissionChecks', 'startup_or_system'),
    ('UnsatisfiedChecks', 'startup_or_system'),
    ('NoReservationUnsatisfiedChecks', 'startup_or_system'),
    ('ClusterQueueStopped', 'configuration_or_request'),
    ('LocalQueueStopped', 'configuration_or_request'),
    ('PodsReadyTimeout', 'startup_or_system'),
    ('AdmissionCheck', 'startup_or_system'),
    ('WaitForStart', 'startup_or_system'),
    ('SomethingNewInAFutureKueue', 'other_or_unknown'),
]
GENERAL_CATEGORIES = {
    'quota_or_capacity',
    'placement_or_topology',
    'configuration_or_request',
    'preemption_or_reclaim',
    'startup_or_system',
    'other_or_unknown',
}


@pytest.mark.parametrize(('reason', 'category'), KUEUE_CATEGORY_CASES)
def test_badput_is_tagged_with_the_category_and_keeps_the_raw_kueue_reason(reason, category):
    clock, tracker = make_tracker()
    w = workload('w', 'pending_quota', 4)
    for c in w['status']['conditions']:
        if c['type'] == 'QuotaReserved':
            c['reason'] = reason
    tracker.update([w])
    clock.t = 10
    [contribution] = tracker.update([w])
    [tags] = badput_tags([contribution])
    assert f'reason:{category}' in tags
    assert f'scheduler_reason:{reason}' in tags
    assert len([t for t in tags if t.startswith('reason:')]) == 1


def test_the_reason_mapping_only_uses_the_six_general_categories():
    assert set(KUEUE_REASON_CATEGORIES.values()) <= GENERAL_CATEGORIES
    assert {category for _, category in KUEUE_MESSAGE_CATEGORIES} <= GENERAL_CATEGORIES
    assert {category for _, category in KUEUE_CATEGORY_CASES} == GENERAL_CATEGORIES


def test_observe_without_a_resolver_uses_only_the_workload():
    assert observe(workload('w', 'running', 4)).gpu_type is None
