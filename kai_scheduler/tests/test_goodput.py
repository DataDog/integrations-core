# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import csv
import os
from collections import defaultdict
from datetime import datetime, timezone

import pytest

from datadog_checks.kai_scheduler import KaiSchedulerCheck
from datadog_checks.kai_scheduler.goodput import (
    BADPUT_METRIC,
    FULLY_ADMITTED_METRIC,
    GPU_FRACTION_ANNOTATION,
    PODGROUP_ANNOTATION,
    GoodputCollector,
    GoodputTracker,
    OwnerStatus,
    QueueKey,
    SchedulingState,
    aggregate,
    badput_by_reason,
    classify,
    job_status,
    normalize_reason,
    pod_gpus,
    queue_tags,
    workload_points,
)
from datadog_checks.kai_scheduler.podgroup_events import LAST_EVICTION_ANNOTATION, LAST_START_ANNOTATION

from .common import get_fixture_path

pytestmark = pytest.mark.unit
ACTIVE_JOB = OwnerStatus(finished_at=None)

START = '2026-11-11T10:00:00Z'
EVICTED = '2026-11-11T10:05:00Z'


def podgroup(
    name='pg', queue='team-a', min_member=1, last_start=None, last_eviction=None, unschedulable=None, owner_job=None
):
    annotations = {}
    if last_start:
        annotations[LAST_START_ANNOTATION] = last_start
    if last_eviction:
        annotations[LAST_EVICTION_ANNOTATION] = last_eviction
    status = {}
    if unschedulable:
        status['schedulingConditions'] = [
            {
                'type': 'UnschedulableOnNodePool',
                'status': 'True',
                'nodePool': 'default',
                'reasons': [{'reason': unschedulable, 'message': 'no room'}],
            }
        ]
    metadata = {'name': name, 'namespace': 'ns', 'uid': f'{name}-uid', 'annotations': annotations}
    if owner_job:
        metadata['ownerReferences'] = [{'apiVersion': 'batch/v1', 'kind': 'Job', 'name': owner_job}]
    return {
        'metadata': metadata,
        'spec': {'queue': queue, 'minMember': min_member},
        'status': status,
    }


def pod(group='pg', phase='Running', gpus=1, deleting=False, finished_at=None, fraction=None, index=0):
    metadata = {'name': f'{group}-{index}', 'namespace': 'ns', 'annotations': {PODGROUP_ANNOTATION: group}}
    if deleting:
        metadata['deletionTimestamp'] = '2026-11-11T10:06:00Z'
    if fraction:
        metadata['annotations'][GPU_FRACTION_ANNOTATION] = fraction
    status = {'phase': phase}
    if finished_at:
        status['containerStatuses'] = [{'state': {'terminated': {'finishedAt': finished_at}}}]
    return {
        'metadata': metadata,
        'spec': {'containers': [{'name': 'main', 'resources': {'limits': {'nvidia.com/gpu': gpus}} if gpus else {}}]},
        'status': status,
    }


class Clock:
    def __init__(self, start=0.0, wall_start=1794391200.0):  # 2026-11-11T10:00:00Z
        self.now = start
        self.wall_start = wall_start

    def monotonic(self):
        return self.now

    def wall(self):
        return self.wall_start + self.now


def tracker():
    clock = Clock()
    return GoodputTracker(monotonic=clock.monotonic, wall=clock.wall), clock


def totals(contributions):
    return {
        queue.queue: (round(t.badput, 3), round(t.fully_admitted, 3)) for queue, t in aggregate(contributions).items()
    }


@pytest.mark.parametrize(
    'pods, min_member, expected',
    [
        pytest.param([pod(phase='Pending')], 1, SchedulingState.WAITING, id='pending'),
        pytest.param([pod(), pod(phase='Pending', index=1)], 1, SchedulingState.WAITING, id='partial_min_member_1'),
        pytest.param([pod(), pod(index=1)], 1, SchedulingState.RUNNABLE, id='all_running'),
        pytest.param([pod()], 2, SchedulingState.WAITING, id='below_min_member'),
        pytest.param([pod(deleting=True)], 1, SchedulingState.WAITING, id='running_but_deleting'),
        pytest.param([pod(phase='Succeeded'), pod(index=1)], 1, SchedulingState.RUNNABLE, id='completed_and_running'),
        pytest.param([pod(phase='Succeeded'), pod(phase='Failed', index=1)], 1, SchedulingState.FINISHED, id='done'),
        pytest.param([], 1, SchedulingState.NO_PODS, id='no_pods'),
    ],
)
def test_classify(pods, min_member, expected):
    assert classify(podgroup(min_member=min_member), pods)[0] == expected


def test_succeeded_pods_do_not_make_a_pending_pod_runnable():
    # Kueue counts succeeded pods as ready; here a pending pod keeps the PodGroup waiting.
    state, reason = classify(podgroup(), [pod(phase='Succeeded'), pod(phase='Pending', index=1)])
    assert state == SchedulingState.WAITING
    assert reason == 'PodsPending'


def test_unschedulable_reason():
    state, reason = classify(podgroup(unschedulable='OverLimit'), [pod(phase='Pending')])
    assert (state, reason) == (SchedulingState.WAITING, 'OverLimit')


def test_evicted_after_last_start_is_preempted():
    pg = podgroup(last_start=START, last_eviction=EVICTED)
    assert classify(pg, [pod(phase='Pending')])[0] == SchedulingState.PREEMPTED
    # Started again after the eviction: back to waiting until its pods run, then runnable.
    restarted = podgroup(last_start='2026-11-11T10:07:00Z', last_eviction=EVICTED)
    assert classify(restarted, [pod(phase='Pending')])[0] == SchedulingState.WAITING
    assert classify(restarted, [pod()])[0] == SchedulingState.RUNNABLE


def test_pod_gpus_counts_requests_init_peak_and_fraction():
    assert pod_gpus(pod(gpus=2)) == 2
    assert pod_gpus(pod(gpus=0, fraction='0.5')) == 0.5
    p = pod(gpus=1)
    p['spec']['initContainers'] = [{'name': 'init', 'resources': {'limits': {'nvidia.com/gpu': 3}}}]
    assert pod_gpus(p) == 3


def test_first_observation_is_a_baseline():
    t, clock = tracker()
    assert t.update([podgroup()], [pod(phase='Pending', gpus=4)]) == []
    clock.now = 15
    assert totals(t.update([podgroup()], [pod(phase='Pending', gpus=4)])) == {'team-a': (60, 0)}


def test_normal_workload():
    t, clock = tracker()
    t.update([podgroup()], [pod(phase='Pending', gpus=2)])
    clock.now = 15
    assert totals(t.update([podgroup()], [pod(gpus=2)])) == {'team-a': (30, 0)}
    clock.now = 30
    assert totals(t.update([podgroup()], [pod(gpus=2)])) == {'team-a': (0, 30)}
    # Finishes 5 seconds into the next interval: only those seconds count, and nothing after.
    clock.now = 45
    done = [pod(phase='Succeeded', gpus=2, finished_at='2026-11-11T10:00:35Z')]
    assert totals(t.update([podgroup()], done)) == {'team-a': (0, 10)}
    clock.now = 60
    assert t.update([podgroup()], done) == []


def test_partial_scheduling_counts_the_whole_request_as_badput():
    t, clock = tracker()
    pg = podgroup(min_member=1)
    partial = [pod(gpus=3), pod(phase='Pending', gpus=3, index=1)]
    t.update([pg], partial)
    clock.now = 15
    assert totals(t.update([pg], partial)) == {'team-a': (90, 0)}
    full = [pod(gpus=3), pod(gpus=3, index=1)]
    clock.now = 30
    assert totals(t.update([pg], full)) == {'team-a': (90, 0)}
    clock.now = 45
    assert totals(t.update([pg], full)) == {'team-a': (0, 90)}


def test_preemption_is_badput_and_keeps_the_request_while_pods_are_missing():
    t, clock = tracker()
    pg = podgroup(last_start=START)
    t.update([pg], [pod(gpus=2)])
    clock.now = 15
    evicted = podgroup(last_start=START, last_eviction=EVICTED)
    # The evicted pod is gone and the replacement is not created yet; the owning Job is still active.
    assert totals(t.update([evicted], [], {'pg-uid': ACTIVE_JOB})) == {'team-a': (0, 30)}
    clock.now = 30
    assert totals(t.update([evicted], [pod(phase='Pending', gpus=2)])) == {'team-a': (30, 0)}


def test_preempted_job_that_gave_up_stops_counting():
    # The Job counted the eviction as a failure and created no replacement pod: the PodGroup has no pod left.
    t, clock = tracker()
    evicted = podgroup(last_start=START, last_eviction=EVICTED)
    t.update([podgroup(last_start=START)], [pod(gpus=2)])
    clock.now = 15
    t.update([evicted], [], {'pg-uid': ACTIVE_JOB})
    clock.now = 30
    assert totals(t.update([evicted], [], {'pg-uid': ACTIVE_JOB})) == {'team-a': (30, 0)}
    clock.now = 45
    # The Job failed 5 seconds into the interval: only those seconds count, and nothing after.
    failed = {'pg-uid': OwnerStatus(finished_at=clock.wall_start + 35)}
    assert totals(t.update([evicted], [], failed)) == {'team-a': (10, 0)}
    clock.now = 60
    assert t.update([evicted], [], failed) == []


def test_podgroup_without_pods_and_unknown_owner_is_not_counted():
    # Such as a PodGroup left behind by a PyTorchJob: nothing says it waits for GPUs, so it must not accrue badput.
    t, clock = tracker()
    t.update([podgroup()], [pod(gpus=2)])
    clock.now = 15
    assert totals(t.update([podgroup()], [])) == {'team-a': (0, 30)}
    clock.now = 30
    assert t.update([podgroup()], []) == []
    assert classify(podgroup(), [])[0] == SchedulingState.NO_PODS


def test_failed_pod_while_the_job_retries_is_waiting_not_finished():
    state, _ = classify(podgroup(), [pod(phase='Failed')], ACTIVE_JOB)
    assert state == SchedulingState.WAITING
    # Without a known owner, a completed pod means the PodGroup is done.
    assert classify(podgroup(), [pod(phase='Failed')])[0] == SchedulingState.FINISHED


def test_completed_ranks_count_towards_min_member():
    # A gang with `minMember` 4 whose first two ranks finished keeps running fully admitted.
    pods = [pod(phase='Succeeded', index=0), pod(phase='Succeeded', index=1), pod(index=2), pod(index=3)]
    assert classify(podgroup(min_member=4), pods)[0] == SchedulingState.RUNNABLE
    # It still needs every active pod to run.
    pods[3] = pod(phase='Pending', index=3)
    assert classify(podgroup(min_member=4), pods)[0] == SchedulingState.WAITING


def test_queues_stay_separate():
    t, clock = tracker()
    pgs = [podgroup('a', queue='team-a'), podgroup('b', queue='team-b')]
    pods = [pod('a', gpus=4), pod('b', phase='Pending', gpus=8)]
    t.update(pgs, pods)
    clock.now = 10
    assert totals(t.update(pgs, pods)) == {'team-a': (0, 40), 'team-b': (80, 0)}


def test_disappeared_podgroup_and_reset():
    t, clock = tracker()
    t.update([podgroup()], [pod(phase='Pending')])
    clock.now = 15
    assert t.update([], []) == []
    t.update([podgroup()], [pod(phase='Pending')])
    t.reset()
    clock.now = 30
    assert t.update([podgroup()], [pod(phase='Pending')]) == []


def test_non_gpu_podgroups_are_ignored():
    t, clock = tracker()
    t.update([podgroup()], [pod(gpus=0)])
    clock.now = 15
    assert t.update([podgroup()], [pod(gpus=0)]) == []


def test_queue_tags():
    assert queue_tags(QueueKey('ns', 'team-a')) == [
        'kube_scheduler:kai',
        'kube_namespace:ns',
        'kai_queue:team-a',
        'kube_scheduler_queue:team-a',
    ]


def test_collector_submits_one_series_per_podgroup(aggregator, instance, mocker):
    # Instance tags, such as the ones Autodiscovery copies from the scraped pods, are not added to the series.
    check = KaiSchedulerCheck('kai_scheduler', {}, [{**instance, 'tags': ['kube_namespace:kai-system', 'pod_name:p']}])
    check.load_configuration_models()
    client = mocker.MagicMock()
    client.list_podgroups.return_value = [podgroup()]
    client.list_pods.return_value = [pod(phase='Pending', gpus=2)]
    client.read_job.side_effect = AssertionError('a PodGroup with pods needs no Job lookup')
    mocker.patch('datadog_checks.kai_scheduler.goodput.KubernetesAPIClient', return_value=client)
    collector = GoodputCollector(check, None, 'kai-scheduler')
    clock = Clock()
    collector.tracker.monotonic, collector.tracker.wall = clock.monotonic, clock.wall
    collector.collect()
    clock.now = 15
    collector.collect()

    client.list_pods.assert_called_with(field_selector='spec.schedulerName=kai-scheduler')
    tags = [
        'kube_scheduler:kai',
        'kube_namespace:ns',
        'kai_queue:team-a',
        'kube_scheduler_queue:team-a',
        'kai_workload:pg',
    ]
    aggregator.assert_metric(BADPUT_METRIC, value=30 / 3600, tags=[*tags, 'reason:waiting_for_pods'], count=1)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=0, tags=tags, count=1)
    # Nothing else: one series per PodGroup and metric.
    assert len(aggregator.metrics(BADPUT_METRIC)) == 1
    assert len(aggregator.metrics(FULLY_ADMITTED_METRIC)) == 1


def test_collector_api_failure_resets_the_baseline(instance, mocker):
    check = KaiSchedulerCheck('kai_scheduler', {}, [instance])
    check.load_configuration_models()
    client = mocker.MagicMock()
    client.list_podgroups.return_value = [podgroup()]
    client.list_pods.return_value = [pod(phase='Pending')]
    mocker.patch('datadog_checks.kai_scheduler.goodput.KubernetesAPIClient', return_value=client)
    collector = GoodputCollector(check, None, 'kai-scheduler')
    collector.collect()
    assert collector.tracker.previous
    client.list_pods.side_effect = Exception('boom')
    collector.collect()
    assert collector.tracker.previous is None


def collector_with(instance, mocker, client):
    mocker.patch('datadog_checks.kai_scheduler.goodput.KubernetesAPIClient', return_value=client)
    check = KaiSchedulerCheck('kai_scheduler', {}, [instance])
    check.load_configuration_models()
    collector = GoodputCollector(check, None, 'kai-scheduler')
    clock = Clock()
    collector.tracker.monotonic, collector.tracker.wall = clock.monotonic, clock.wall
    return check, collector, clock


FAILED_JOB = {
    'status': {'conditions': [{'type': 'Failed', 'status': 'True', 'lastTransitionTime': '2026-11-11T10:00:20Z'}]}
}


@pytest.mark.parametrize(
    'job, expected',
    [
        pytest.param(FAILED_JOB, OwnerStatus(finished_at=1794391220.0), id='failed'),
        pytest.param(
            {
                'status': {
                    'conditions': [{'type': 'Complete', 'status': 'True', 'lastTransitionTime': '2026-11-11T10:00:20Z'}]
                }
            },
            OwnerStatus(finished_at=1794391220.0),
            id='complete',
        ),
        pytest.param({'status': {'active': 1}}, ACTIVE_JOB, id='still_running'),
        pytest.param(None, OwnerStatus(finished_at=1794391200.0), id='deleted'),
    ],
)
def test_collector_reads_the_job_of_a_tracked_podgroup_without_pods(instance, mocker, job, expected):
    client = mocker.MagicMock()
    client.read_job.return_value = job
    _, collector, _ = collector_with(instance, mocker, client)
    pgs = [podgroup(owner_job='train'), podgroup('other', owner_job='other'), podgroup('new', owner_job='new')]
    collector.tracker.update(pgs[:2], [pod(), pod('other')])

    owners = collector.owner_statuses(pgs, {('ns', 'other'): [pod('other')]})

    # Only the tracked PodGroup without an active pod is looked up: `other` has a running pod and `new` is untracked.
    client.read_job.assert_called_once_with('ns', 'train')
    assert owners == {'pg-uid': expected}


def test_collector_warns_once_per_streak_of_job_lookup_failures(instance, mocker, caplog):
    client = mocker.MagicMock()
    client.read_job.side_effect = Exception('forbidden')
    _, collector, _ = collector_with(instance, mocker, client)
    pgs = [podgroup(owner_job='train')]
    collector.tracker.update(pgs, [pod()])
    with caplog.at_level('WARNING'):
        # A failed lookup leaves the owner unknown, so the PodGroup without pods stops counting.
        assert collector.owner_statuses(pgs, {}) == {}
        collector.owner_statuses(pgs, {})
    assert caplog.text.count('cannot read the owning Job of 1 KAI PodGroups') == 1
    client.read_job.side_effect = None
    client.read_job.return_value = {'status': {'active': 1}}
    assert collector.owner_statuses(pgs, {}) == {'pg-uid': ACTIVE_JOB}
    assert not collector.job_lookups_failing


def test_suspended_job_without_pods_is_not_counted():
    suspended = job_status({'spec': {'suspend': True}, 'status': {}}, lambda: 0)
    assert suspended == OwnerStatus(finished_at=None, suspended=True)
    assert classify(podgroup(), [], suspended)[0] == SchedulingState.INACTIVE


def test_collector_does_not_look_up_non_job_owners(instance, mocker):
    client = mocker.MagicMock()
    _, collector, _ = collector_with(instance, mocker, client)
    pg = podgroup()
    pg['metadata']['ownerReferences'] = [{'apiVersion': 'kubeflow.org/v1', 'kind': 'PyTorchJob', 'name': 'train'}]
    collector.tracker.update([pg], [pod()])
    assert collector.owner_statuses([pg], {}) == {}
    client.read_job.assert_not_called()


@pytest.mark.parametrize(
    'state, reason, expected',
    [
        pytest.param(SchedulingState.WAITING, 'OverLimit', 'quota_exhausted', id='over_limit'),
        pytest.param(SchedulingState.WAITING, 'NonPreemptibleOverQuota', 'quota_exhausted', id='over_quota'),
        pytest.param(SchedulingState.WAITING, 'PodSchedulingErrors', 'no_matching_resources', id='no_room'),
        pytest.param(SchedulingState.WAITING, 'PreemptionDelayNotElapsed', 'waiting_for_preemption', id='delay'),
        pytest.param(SchedulingState.WAITING, 'QueueDoesNotExist', 'misconfigured', id='no_queue'),
        pytest.param(SchedulingState.WAITING, 'PodsPending', 'waiting_for_pods', id='pods_pending'),
        pytest.param(SchedulingState.WAITING, 'SomethingNew', 'unknown', id='unknown'),
        pytest.param(SchedulingState.PREEMPTED, 'Evicted', 'preempted', id='preempted'),
        pytest.param(SchedulingState.RUNNABLE, None, None, id='not_badput'),
    ],
)
def test_normalize_reason(state, reason, expected):
    assert normalize_reason(state, reason) == expected


def test_badput_is_split_by_reason_and_derived_reasons_are_not_kai_reasons():
    t, clock = tracker()
    pgs = [
        podgroup('quota', unschedulable='OverLimit'),
        podgroup('huge', unschedulable='PodSchedulingErrors'),
        podgroup('bound'),
    ]
    pods = [pod('quota', phase='Pending', gpus=2), pod('huge', phase='Pending', gpus=32), pod('bound', phase='Pending')]
    t.update(pgs, pods)
    clock.now = 10
    assert badput_by_reason(t.update(pgs, pods)) == {
        QueueKey('ns', 'team-a'): {
            ('quota_exhausted', 'OverLimit'): 20,
            ('no_matching_resources', 'PodSchedulingErrors'): 320,
            ('waiting_for_pods', None): 10,
        }
    }


def test_collector_submits_zero_badput_without_reason(aggregator, instance, mocker):
    check = KaiSchedulerCheck('kai_scheduler', {}, [instance])
    check.load_configuration_models()
    client = mocker.MagicMock()
    client.list_podgroups.return_value = [podgroup()]
    client.list_pods.return_value = [pod(gpus=2)]
    mocker.patch('datadog_checks.kai_scheduler.goodput.KubernetesAPIClient', return_value=client)
    collector = GoodputCollector(check, None, 'kai-scheduler')
    clock = Clock()
    collector.tracker.monotonic, collector.tracker.wall = clock.monotonic, clock.wall
    collector.collect()
    clock.now = 15
    collector.collect()
    tags = [
        'kube_scheduler:kai',
        'kube_namespace:ns',
        'kai_queue:team-a',
        'kube_scheduler_queue:team-a',
        'kai_workload:pg',
    ]
    aggregator.assert_metric(BADPUT_METRIC, value=0, tags=tags, count=1)
    aggregator.assert_metric(FULLY_ADMITTED_METRIC, value=30 / 3600, tags=tags, count=1)


def test_check_runs_goodput_when_the_scrape_fails(dd_run_check, instance, mock_http_response, mocker):
    collect = mocker.patch.object(GoodputCollector, 'collect')
    check = KaiSchedulerCheck('kai_scheduler', {}, [{**instance, 'collect_scheduling_goodput': True}])
    mock_http_response(status_code=500)
    with pytest.raises(Exception):
        dd_run_check(check)
    assert isinstance(check.goodput, GoodputCollector)
    collect.assert_called_once()


def test_check_goodput_failure_resets_and_logs_one_traceback(
    dd_run_check, instance, mock_http_response, mocker, caplog
):
    mocker.patch.object(GoodputCollector, 'collect', side_effect=RuntimeError('bug'))
    reset = mocker.patch('datadog_checks.kai_scheduler.goodput.GoodputTracker.reset')
    check = KaiSchedulerCheck(
        'kai_scheduler', {}, [{**instance, 'collect_scheduling_goodput': True, 'collect_podgroup_events': False}]
    )
    mock_http_response(file_path=get_fixture_path('scheduler.txt'))
    with caplog.at_level('WARNING'):
        dd_run_check(check)
        dd_run_check(check)
    records = [r for r in caplog.records if 'Cannot collect KAI scheduling goodput' in r.getMessage()]
    assert len(records) == 2
    assert records[0].exc_info and not records[1].exc_info
    assert reset.call_count == 2


def test_per_podgroup_series_sum_to_the_right_totals_for_any_grouping():
    """18 PodGroups in 3 queues, some at the same time and some at different times, each waiting then running.

    Summing the per-PodGroup points by queue, by reason, by PodGroup, or all of them, must give the GPU-hours computed
    from each PodGroup's own timeline, as a query that sums the series by any tag would.
    """
    queues = ['team-a', 'team-b', 'team-c']
    # Waiting for quota, as KAI reports it, or bound with its pods not running yet: two different reasons.
    waiting_reasons = {'OverLimit': 'quota_exhausted', None: 'waiting_for_pods'}
    # name -> (queue, GPUs, KAI reason, created poll, running poll, finished poll), in 10-second polls.
    timelines = {
        f'pg{i}': (queues[i % 3], 1 + i % 4, list(waiting_reasons)[i % 2], i % 5, i % 5 + 1 + i % 3, i % 5 + 3 + i % 4)
        for i in range(18)
    }
    t, clock = tracker()
    sums = defaultdict(float)
    for poll in range(12):
        clock.now = poll * 10
        pgs, pods = [], []
        for name, (queue, gpus, reason, created, running, finished) in timelines.items():
            if poll < created:
                continue
            waiting = created <= poll < running
            pgs.append(podgroup(name, queue=queue, unschedulable=reason if waiting else None))
            if poll >= finished:
                done_at = datetime.fromtimestamp(clock.wall_start + finished * 10, timezone.utc)
                pods.append(pod(name, phase='Succeeded', gpus=gpus, finished_at=done_at.strftime('%Y-%m-%dT%H:%M:%SZ')))
            elif poll >= running:
                pods.append(pod(name, gpus=gpus))
            else:
                pods.append(pod(name, phase='Pending', gpus=gpus))
        for metric, value, tags in workload_points(t.update(pgs, pods)):
            assert sum(tag.startswith('kai_workload:') for tag in tags) == 1
            tag = dict(tag.split(':', 1) for tag in tags)
            sums[(metric, 'queue', tag['kai_queue'])] += value
            sums[(metric, 'workload', tag['kai_workload'])] += value
            sums[(metric, 'total', None)] += value
            if 'reason' in tag:
                sums[(metric, 'reason', tag['reason'])] += value

    expected = defaultdict(float)
    for name, (queue, gpus, reason, created, running, finished) in timelines.items():
        badput = gpus * (running - created) * 10 / 3600
        fully_admitted = gpus * (finished - running) * 10 / 3600
        for key in (('queue', queue), ('workload', name), ('total', None)):
            expected[(BADPUT_METRIC, *key)] += badput
            expected[(FULLY_ADMITTED_METRIC, *key)] += fully_admitted
        expected[(BADPUT_METRIC, 'reason', waiting_reasons[reason])] += badput
    assert sums.keys() == expected.keys()
    for key in expected:
        assert sums[key] == pytest.approx(expected[key]), key


def test_failed_attempts_do_not_inflate_the_request():
    # A Job with 1 GPU per pod failed 3 times and waits for its retry: the PodGroup still needs 1 GPU, not 3.
    t, clock = tracker()
    t.update([podgroup()], [pod(gpus=1)])
    clock.now = 15
    failed = [pod(phase='Failed', gpus=1, index=i) for i in range(3)]
    t.update([podgroup()], failed, {'pg-uid': ACTIVE_JOB})
    clock.now = 30
    assert totals(t.update([podgroup()], failed, {'pg-uid': ACTIVE_JOB})) == {'team-a': (15, 0)}


def test_collector_rereads_active_jobs_only_after_the_ttl(instance, mocker):
    from datadog_checks.kai_scheduler.goodput import OWNER_STATUS_TTL

    client = mocker.MagicMock()
    client.read_job.return_value = {'status': {'active': 1}}
    _, collector, clock = collector_with(instance, mocker, client)
    pgs = [podgroup(owner_job='train')]
    # The PodGroup already waits for a retry: its Job status is reused.
    collector.tracker.update(pgs, [pod(phase='Pending')])
    collector.owner_statuses(pgs, {})
    clock.now = OWNER_STATUS_TTL - 1
    collector.owner_statuses(pgs, {})
    assert client.read_job.call_count == 1
    clock.now = OWNER_STATUS_TTL + 1
    collector.owner_statuses(pgs, {})
    assert client.read_job.call_count == 2


def test_collector_warns_once_per_streak_of_api_failures(instance, mocker, caplog):
    client = mocker.MagicMock()
    client.list_podgroups.side_effect = Exception('forbidden')
    _, collector, _ = collector_with(instance, mocker, client)
    with caplog.at_level('WARNING'):
        collector.collect()
        collector.collect()
    assert caplog.text.count('Cannot collect KAI scheduling goodput from the Kubernetes API') == 1


@pytest.mark.parametrize(
    'status, expected', [pytest.param(404, None, id='deleted'), pytest.param(403, 'raise', id='forbidden')]
)
def test_read_job_returns_none_only_for_a_deleted_job(mocker, status, expected):
    from kubernetes.client import ApiException

    from datadog_checks.kai_scheduler.kube_client import KubernetesAPIClient

    mocker.patch('datadog_checks.kai_scheduler.kube_client.config.load_incluster_config')
    client = KubernetesAPIClient()
    mocker.patch.object(client.batch, 'read_namespaced_job', side_effect=ApiException(status=status))
    if expected == 'raise':
        with pytest.raises(ApiException):
            client.read_job('ns', 'train')
    else:
        assert client.read_job('ns', 'train') is None


def test_unknown_pod_is_active_and_keeps_the_podgroup_waiting():
    # The node stopped reporting the pod: it is not known to run, but it still holds its GPUs.
    pods = [pod(gpus=2), pod(phase='Unknown', gpus=2, index=1)]
    assert classify(podgroup(), pods)[0] == SchedulingState.WAITING
    t, clock = tracker()
    t.update([podgroup()], pods)
    clock.now = 15
    assert totals(t.update([podgroup()], pods)) == {'team-a': (60, 0)}


def test_job_failure_time_closes_the_last_retry_wait():
    # The pod failed and the Job waited to retry it, then failed: the wait lasts until the Job failure.
    t, clock = tracker()
    t.update([podgroup()], [pod(gpus=2)])
    clock.now = 15
    failed_pod = [pod(phase='Failed', gpus=2, finished_at='2026-11-11T10:00:10Z')]
    # Running ended when the pod failed, 10 seconds into the interval.
    assert totals(t.update([podgroup()], failed_pod, {'pg-uid': ACTIVE_JOB})) == {'team-a': (0, 20)}
    clock.now = 30
    failed_job = {'pg-uid': OwnerStatus(finished_at=clock.wall_start + 25)}
    assert totals(t.update([podgroup()], failed_pod, failed_job)) == {'team-a': (20, 0)}


def test_cpu_pods_left_after_the_gpu_pods_complete_count_no_gpu_time():
    t, clock = tracker()
    t.update([podgroup()], [pod(gpus=2), pod(gpus=0, index=1)])
    clock.now = 15
    tail = [pod(phase='Succeeded', gpus=2), pod(gpus=0, index=1)]
    # The last GPU interval still counts the GPUs of the previous poll.
    assert totals(t.update([podgroup()], tail)) == {'team-a': (0, 30)}
    clock.now = 30
    assert t.update([podgroup()], tail) == []


def test_collector_metrics_match_the_gpu_metadata(aggregator, instance, mocker):
    # The goodput metrics are shared by the scheduler integrations, so they are documented in the GPU integration.
    check = KaiSchedulerCheck('kai_scheduler', {}, [instance])
    check.load_configuration_models()
    client = mocker.MagicMock()
    client.list_podgroups.return_value = [podgroup()]
    client.list_pods.return_value = [pod(gpus=2)]
    mocker.patch('datadog_checks.kai_scheduler.goodput.KubernetesAPIClient', return_value=client)
    collector = GoodputCollector(check, None, 'kai-scheduler')
    clock = Clock()
    collector.tracker.monotonic, collector.tracker.wall = clock.monotonic, clock.wall
    collector.collect()
    clock.now = 15
    collector.collect()
    gpu_metadata = os.path.join(os.path.dirname(__file__), '..', '..', 'gpu', 'metadata.csv')
    with open(gpu_metadata) as f:
        metadata = {row['metric_name']: row for row in csv.DictReader(f)}
    aggregator.assert_metric(FULLY_ADMITTED_METRIC)
    aggregator.assert_metrics_using_metadata(metadata, check_submission_type=True)


def test_collector_rereads_the_job_after_a_retry_ran(instance, mocker):
    # The Job was active while its first attempt waited to be retried; the retry then ran and failed, and so did the
    # Job: the status read before the retry must not be reused.
    client = mocker.MagicMock()
    client.read_job.return_value = {'status': {'active': 1}}
    _, collector, clock = collector_with(instance, mocker, client)
    pgs = [podgroup(owner_job='train')]
    collector.tracker.update(pgs, [pod()])
    collector.owner_statuses(pgs, {})
    clock.now = 10
    collector.owner_statuses(pgs, {('ns', 'pg'): [pod()]})
    clock.now = 20
    collector.owner_statuses(pgs, {})
    assert client.read_job.call_count == 2


def test_running_ends_with_the_last_pod_not_with_the_job():
    # The pod finished 5 seconds into the interval and the Job controller marked the Job complete 7 seconds later.
    t, clock = tracker()
    t.update([podgroup()], [pod(gpus=2)])
    clock.now = 15
    done = [pod(phase='Succeeded', gpus=2, finished_at='2026-11-11T10:00:05Z')]
    complete = {'pg-uid': OwnerStatus(finished_at=clock.wall_start + 12)}
    assert totals(t.update([podgroup()], done, complete)) == {'team-a': (0, 10)}


def test_failed_init_container_closes_the_last_interval():
    t, clock = tracker()
    t.update([podgroup()], [pod(phase='Pending', gpus=2)])
    clock.now = 15
    failed = pod(phase='Failed', gpus=2)
    failed['status']['initContainerStatuses'] = [{'state': {'terminated': {'finishedAt': '2026-11-11T10:00:05Z'}}}]
    assert totals(t.update([podgroup()], [failed])) == {'team-a': (10, 0)}


def test_job_read_right_after_the_pods_stop_is_read_again(aggregator, instance, mocker):
    # The pod completed 5 seconds into the interval, but the Job controller marked the Job complete only at +16, after
    # the next poll had read it as active.
    client = mocker.MagicMock()
    client.list_podgroups.return_value = [podgroup(owner_job='train')]
    client.list_pods.return_value = [pod(gpus=2)]
    complete = {
        'status': {'conditions': [{'type': 'Complete', 'status': 'True', 'lastTransitionTime': '2026-11-11T10:00:16Z'}]}
    }
    client.read_job.side_effect = [{'status': {'active': 1}}, complete]
    _, collector, clock = collector_with(instance, mocker, client)
    collector.collect()
    client.list_pods.return_value = [pod(phase='Succeeded', gpus=2, finished_at='2026-11-11T10:00:05Z')]
    for now in (15, 30, 45):
        clock.now = now
        collector.collect()

    assert client.read_job.call_count == 2
    # Running ended with the pod, and the wait for the Job to complete lasted 1 second after the poll at 15.
    assert sum(m.value for m in aggregator.metrics(FULLY_ADMITTED_METRIC)) == pytest.approx(2 * 5 / 3600)
    assert sum(m.value for m in aggregator.metrics(BADPUT_METRIC)) == pytest.approx(2 * 1 / 3600)
