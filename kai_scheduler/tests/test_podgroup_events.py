# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import json
import logging
from datetime import datetime

import pytest
from kubernetes.client.exceptions import ApiException

from datadog_checks.kai_scheduler import KaiSchedulerCheck
from datadog_checks.kai_scheduler.podgroup_events import PodGroupEventCollector

from .common import CHECK_NAME, SCHEDULER_ENDPOINT, get_fixture_path

pytestmark = [pytest.mark.unit]

CREATED_AT = '2026-11-03T10:00:00Z'
PENDING_AT = '2026-11-03T10:00:05Z'
STARTED_AT = '2026-11-03T10:01:00Z'
EVICTED_AT = '2026-11-03T10:05:00Z'
RESTARTED_AT = '2026-11-03T10:06:00Z'

BASE_TAGS = [
    'kube_namespace:team-a',
    'kai_workload:pg-train',
    'kai_workload_uid:pg-uid',
    'kai_queue:research',
    'kai_workload_priority_class:train',
]
PENDING = {
    'type': 'UnschedulableOnNodePool',
    'nodePool': 'cpu-pool',
    'status': 'True',
    'reason': 'Unschedulable',
    'message': 'Queue research is over its GPU limit.',
    'reasons': [{'reason': 'OverLimit', 'message': 'Queue research is over its GPU limit.'}],
    'lastTransitionTime': PENDING_AT,
}
EVICT_EVENT = {
    'involvedObject': {'uid': 'pg-uid'},
    'message': 'Pod team-a/train-0 was preempted by higher priority workload team-b/pg-serve',
    'lastTimestamp': EVICTED_AT,
    'metadata': {
        'annotations': {
            'evictor-action-type': 'preempt',
            'evictor-pod-group-name': 'pg-serve',
            'evictor-pod-group-namespace': 'team-b',
        }
    },
}
# The Kubernetes event recorder combines bursts of similar events into events without KAI's annotations.
COMBINED_EVICT_EVENT = {
    'involvedObject': {'uid': 'pg-uid'},
    'message': '(combined from similar events): Pod team-a/train-9 was preempted by team-b/pg-serve',
    'lastTimestamp': EVICTED_AT,
    'metadata': {},
}
EARLIER_EVICT_EVENT = {
    'involvedObject': {'uid': 'pg-uid'},
    'message': 'Pod team-a/train-0 was reclaimed by team-c/pg-batch',
    'lastTimestamp': STARTED_AT,
    'metadata': {
        'annotations': {
            'evictor-action-type': 'reclaim',
            'evictor-pod-group-name': 'pg-batch',
            'evictor-pod-group-namespace': 'team-c',
        }
    },
}
LATER_EVICT_EVENT = {
    **EARLIER_EVICT_EVENT,
    'lastTimestamp': RESTARTED_AT,
}
# Events of other PodGroups in the same namespace are listed together.
OTHER_PODGROUP_EVICT_EVENT = {
    **EVICT_EVENT,
    'involvedObject': {'uid': 'other-uid'},
    'message': 'Pod team-a/infer-0 was reclaimed by team-c/pg-batch',
    'lastTimestamp': RESTARTED_AT,
    'metadata': {'annotations': {'evictor-action-type': 'reclaim'}},
}


class FakeKubernetesAPIClient:
    def __init__(self, *snapshots, evict_events=None):
        self.snapshots = list(snapshots)
        self.evict_events = evict_events
        self.evict_event_lists = []

    def list_podgroups(self):
        snapshot = self.snapshots.pop(0)
        if isinstance(snapshot, Exception):
            raise snapshot
        return snapshot

    def list_evict_events(self, namespace):
        self.evict_event_lists.append(namespace)
        if isinstance(self.evict_events, Exception):
            raise self.evict_events
        return self.evict_events or []


def podgroup(pending=None, last_start=None, last_eviction=None, uid='pg-uid'):
    annotations = {}
    if last_start:
        annotations['kai.scheduler/last-start-timestamp'] = last_start
    if last_eviction:
        annotations['kai.scheduler/last-eviction-timestamp'] = last_eviction
    return {
        'metadata': {
            'name': 'pg-train',
            'namespace': 'team-a',
            'uid': uid,
            'creationTimestamp': CREATED_AT,
            'labels': {'kai.scheduler/node-pool': 'gpu-pool'},
            'annotations': annotations,
        },
        'spec': {'queue': 'research', 'priorityClassName': 'train'},
        'status': {'schedulingConditions': [pending]} if pending else {},
    }


def make_collector(instance, *snapshots, evict_events=None):
    collector = PodGroupEventCollector(KaiSchedulerCheck(CHECK_NAME, {}, [instance]), None)
    collector.kube_client = FakeKubernetesAPIClient(*snapshots, evict_events=evict_events)
    return collector


def collect(collector, runs):
    for _ in range(runs):
        collector.collect()


def epoch(timestamp):
    return int(datetime.fromisoformat(timestamp).timestamp())


def test_lifecycle_events(aggregator, instance):
    # The instance tags must not reach the events.
    collector = make_collector(
        instance,
        [],
        [podgroup(pending=PENDING)],
        [podgroup(last_start=STARTED_AT)],
        [podgroup(last_start=STARTED_AT, last_eviction=EVICTED_AT)],
        [podgroup(last_start=STARTED_AT, last_eviction=EVICTED_AT)],
        evict_events=[EARLIER_EVICT_EVENT, COMBINED_EVICT_EVENT, EVICT_EVENT, OTHER_PODGROUP_EVICT_EVENT],
    )
    collect(collector, 5)

    expected = [
        ('created', 'info', CREATED_AT, 'PodGroup team-a/pg-train created.', ['kai_nodepool:gpu-pool']),
        (
            'pending',
            'warning',
            PENDING_AT,
            'PodGroup team-a/pg-train pending. Queue research is over its GPU limit.',
            # The node pool of a pending event is the one in its scheduling condition, not the PodGroup label.
            ['kai_nodepool:cpu-pool', 'kai_pending_reason:OverLimit'],
        ),
        (
            'admitted',
            'info',
            STARTED_AT,
            'PodGroup team-a/pg-train admitted. Queued wait time was 60s.',
            ['kai_nodepool:gpu-pool'],
        ),
        (
            'evicted',
            'warning',
            EVICTED_AT,
            'PodGroup team-a/pg-train evicted. Pod team-a/train-0 was preempted by higher priority workload '
            'team-b/pg-serve. Eviction action: preempt.',
            ['kai_nodepool:gpu-pool', 'kai_eviction_action:preempt', 'kai_evicted_by:team-b/pg-serve'],
        ),
    ]
    assert len(aggregator.events) == len(expected)
    for index, (event, (transition, alert_type, timestamp, text, extra_tags)) in enumerate(
        zip(aggregator.events, expected, strict=True)
    ):
        assert event['event_type'] == f'kai.podgroup.{transition}'
        assert event['msg_title'] == f'KAI PodGroup team-a/pg-train {transition}'
        assert event['msg_text'] == text
        assert event['alert_type'] == alert_type
        assert event['timestamp'] == epoch(timestamp)
        assert event['aggregation_key'] == 'pg-uid'
        assert sorted(event['tags']) == sorted(
            [*BASE_TAGS, *extra_tags, f'kai_transition:{transition}', f'kai_workload_event_index:{index}']
        )


def test_first_run_seeds_state(aggregator, instance):
    collector = make_collector(instance, [podgroup(pending=PENDING, last_start=STARTED_AT, last_eviction=EVICTED_AT)])
    collect(collector, 1)

    assert not aggregator.events


def test_unchanged_podgroup_emits_no_events(aggregator, instance):
    # KAI rewrites the message and `lastTransitionTime` of a pending PodGroup whenever its scheduling error changes.
    changed_pending = {**PENDING, 'message': 'No node has enough GPUs.', 'lastTransitionTime': STARTED_AT}
    collector = make_collector(
        instance,
        [],
        [podgroup(pending=PENDING)],
        [podgroup(pending=changed_pending)],
        [podgroup(pending=changed_pending)],
    )
    collect(collector, 4)

    assert [event['event_type'] for event in aggregator.events] == ['kai.podgroup.created', 'kai.podgroup.pending']


def test_failed_poll_keeps_state(aggregator, instance):
    # The next run neither reports the PodGroup as new nor misses what changed during the failure.
    collector = make_collector(
        instance, [podgroup(pending=PENDING)], Exception('API server unavailable'), [podgroup(last_start=STARTED_AT)]
    )
    collect(collector, 3)

    assert [event['event_type'] for event in aggregator.events] == ['kai.podgroup.admitted']


def test_failed_podgroup_keeps_previous_state(aggregator, instance):
    # A PodGroup that cannot be processed once must not be reported as created again afterwards.
    malformed = podgroup()
    malformed['status'] = {'schedulingConditions': ['not a condition']}
    collector = make_collector(instance, [podgroup()], [malformed], [podgroup()])
    collect(collector, 3)

    assert not aggregator.events


def test_repeated_poll_failure_warns_once_per_cause(instance, caplog):
    # Without the RBAC permission on PodGroups, every run fails the same way until the cause changes or a run succeeds.
    forbidden = ApiException(status=403)
    not_found = ApiException(status=404)
    collector = make_collector(instance, forbidden, forbidden, not_found, [], not_found)
    caplog.set_level(logging.DEBUG)
    collect(collector, 5)

    failures = [record for record in caplog.records if 'Cannot collect KAI PodGroup events' in record.getMessage()]
    assert [record.levelname for record in failures] == ['WARNING', 'DEBUG', 'WARNING', 'WARNING']


@pytest.mark.parametrize(
    'evict_events',
    [
        pytest.param([{**EVICT_EVENT, 'lastTimestamp': STARTED_AT}], id='event of an earlier eviction'),
        pytest.param([LATER_EVICT_EVENT], id='event of a later eviction'),
        pytest.param(Exception('events are forbidden'), id='events cannot be listed'),
    ],
)
def test_evicted_without_evict_event(aggregator, instance, evict_events):
    collector = make_collector(
        instance,
        [podgroup(last_start=STARTED_AT)],
        [podgroup(last_start=STARTED_AT, last_eviction=EVICTED_AT)],
        evict_events=evict_events,
    )
    collect(collector, 2)

    aggregator.assert_event(
        'PodGroup team-a/pg-train evicted.',
        count=1,
        tags=[*BASE_TAGS, 'kai_nodepool:gpu-pool', 'kai_transition:evicted', 'kai_workload_event_index:0'],
    )


@pytest.mark.parametrize(
    'evict_events',
    [
        # Another eviction of the PodGroup happened after the PodGroups were listed.
        pytest.param([EVICT_EVENT, LATER_EVICT_EVENT], id='later eviction'),
        # The scheduler can record the event in the second after it stamps the eviction.
        pytest.param([{**EVICT_EVENT, 'lastTimestamp': '2026-11-03T10:05:01Z'}], id='event one second later'),
    ],
)
def test_eviction_details_match_transition(aggregator, instance, evict_events):
    collector = make_collector(
        instance,
        [podgroup(last_start=STARTED_AT)],
        [podgroup(last_start=STARTED_AT, last_eviction=EVICTED_AT)],
        evict_events=evict_events,
    )
    collect(collector, 2)

    aggregator.assert_event(
        'PodGroup team-a/pg-train evicted. Pod team-a/train-0 was preempted by higher priority workload '
        'team-b/pg-serve. Eviction action: preempt.',
        count=1,
        tags=[
            *BASE_TAGS,
            'kai_nodepool:gpu-pool',
            'kai_transition:evicted',
            'kai_eviction_action:preempt',
            'kai_evicted_by:team-b/pg-serve',
            'kai_workload_event_index:0',
        ],
    )


@pytest.mark.parametrize(
    'current, transitions',
    [
        # The PodGroup started and was evicted back to pending, so its condition was recreated after the start.
        pytest.param(
            podgroup(
                pending={**PENDING, 'lastTransitionTime': RESTARTED_AT}, last_start=STARTED_AT, last_eviction=EVICTED_AT
            ),
            ['admitted', 'evicted', 'pending'],
            id='pending again after an eviction',
        ),
        # KAI keeps the condition while the pods bind or while only some of them run.
        pytest.param(
            podgroup(pending=PENDING, last_start=STARTED_AT),
            ['admitted'],
            id='condition kept after the start',
        ),
    ],
)
def test_pending_after_start_between_runs(aggregator, instance, current, transitions):
    collector = make_collector(instance, [podgroup(pending=PENDING)], [current])
    collect(collector, 2)

    assert [event['event_type'] for event in aggregator.events] == [f'kai.podgroup.{name}' for name in transitions]


def test_evict_events_listed_once_per_namespace(aggregator, instance):
    collector = make_collector(
        instance,
        [podgroup(uid='pg-uid', last_start=STARTED_AT), podgroup(uid='other-uid', last_start=STARTED_AT)],
        [
            podgroup(uid='pg-uid', last_start=STARTED_AT, last_eviction=EVICTED_AT),
            podgroup(uid='other-uid', last_start=STARTED_AT, last_eviction=EVICTED_AT),
        ],
        evict_events=[EVICT_EVENT, {**OTHER_PODGROUP_EVICT_EVENT, 'lastTimestamp': EVICTED_AT}],
    )
    collect(collector, 2)

    assert collector.kube_client.evict_event_lists == ['team-a']
    actions = sorted(
        tag for event in aggregator.events for tag in event['tags'] if tag.startswith('kai_eviction_action')
    )
    assert actions == ['kai_eviction_action:preempt', 'kai_eviction_action:reclaim']


def test_transitions_between_runs_are_ordered(aggregator, instance):
    collector = make_collector(
        instance,
        [podgroup(last_start=STARTED_AT)],
        [podgroup(last_start=RESTARTED_AT, last_eviction=EVICTED_AT)],
    )
    collect(collector, 2)

    assert [(event['event_type'], event['msg_text']) for event in aggregator.events] == [
        ('kai.podgroup.evicted', 'PodGroup team-a/pg-train evicted.'),
        # The wait time counts from the eviction, not from the previous start.
        ('kai.podgroup.admitted', 'PodGroup team-a/pg-train admitted. Queued wait time was 60s.'),
    ]


@pytest.mark.parametrize(
    'previous, current, text',
    [
        # KAI stamps a new start when a PodGroup whose pods all finished gets new ones, such as the next pod of a Job.
        pytest.param(
            podgroup(last_start=STARTED_AT),
            podgroup(last_start=RESTARTED_AT),
            'PodGroup team-a/pg-train admitted.',
            id='next pod without eviction',
        ),
        pytest.param(
            podgroup(last_start=STARTED_AT, last_eviction=PENDING_AT),
            podgroup(last_start=RESTARTED_AT, last_eviction=PENDING_AT),
            'PodGroup team-a/pg-train admitted.',
            id='next pod after an earlier eviction',
        ),
        # The PodGroup started, was evicted, and started again between two runs, so the wait counts from the eviction.
        pytest.param(
            podgroup(pending=PENDING),
            podgroup(last_start=RESTARTED_AT, last_eviction=EVICTED_AT),
            'PodGroup team-a/pg-train admitted. Queued wait time was 60s.',
            id='start and eviction between runs',
        ),
        # The PodGroup started and was then evicted between two runs, so the wait counts from its creation to the start.
        pytest.param(
            podgroup(pending=PENDING),
            podgroup(last_start=STARTED_AT, last_eviction=EVICTED_AT),
            'PodGroup team-a/pg-train admitted. Queued wait time was 60s.',
            id='eviction after the start between runs',
        ),
    ],
)
def test_admitted_wait_time(aggregator, instance, previous, current, text):
    collector = make_collector(instance, [previous], [current])
    collect(collector, 2)

    aggregator.assert_event(text, count=1)


def test_event_index_persists_across_restart(aggregator, instance):
    collect(make_collector(instance, [], [podgroup(pending=PENDING)]), 2)
    aggregator.reset()

    # A restarted Agent creates a new check and seeds its state again, but continues the sequence of each PodGroup.
    collect(make_collector(instance, [podgroup(pending=PENDING)], [podgroup(last_start=STARTED_AT)]), 2)

    assert [event['event_type'] for event in aggregator.events] == ['kai.podgroup.admitted']
    assert 'kai_workload_event_index:2' in aggregator.events[0]['tags']


@pytest.mark.parametrize(
    'cache',
    [
        pytest.param('not json', id='invalid json'),
        pytest.param('[1]', id='not a mapping'),
        pytest.param(json.dumps({'pg-uid': -1}), id='invalid index'),
    ],
)
def test_corrupt_event_index_cache(aggregator, instance, cache):
    # The cache survives Agent restarts, so a corrupt one must not stop events or skew their index.
    collector = make_collector(instance, [], [podgroup(pending=PENDING)])
    collector.check.write_persistent_cache('podgroup_event_index', cache)
    collect(collector, 2)

    assert [tag for event in aggregator.events for tag in event['tags'] if 'event_index' in tag] == [
        'kai_workload_event_index:0',
        'kai_workload_event_index:1',
    ]


def test_event_index_drops_deleted_podgroups(instance):
    collector = make_collector(instance, [], [podgroup(uid='kept'), podgroup(uid='deleted')], [podgroup(uid='kept')])
    collect(collector, 3)

    assert json.loads(collector.check.read_persistent_cache('podgroup_event_index')) == {'kept': 1}


@pytest.mark.parametrize('enabled', [True, False])
def test_collect_podgroup_events_option(dd_run_check, instance, mock_http_response, enabled, monkeypatch):
    # Events come from the Kubernetes API, so they are collected even when the metrics endpoint fails.
    mock_http_response(status_code=500)
    collected = []
    monkeypatch.setattr(PodGroupEventCollector, 'collect', lambda self: collected.append(self))

    check = KaiSchedulerCheck(CHECK_NAME, {}, [{**copy.deepcopy(instance), 'collect_podgroup_events': enabled}])
    with pytest.raises(Exception, match='500'):
        dd_run_check(check)

    assert bool(collected) is enabled


def test_event_failure_does_not_fail_metrics_run(dd_run_check, aggregator, mock_http_response, monkeypatch, caplog):
    mock_http_response(file_path=get_fixture_path('scheduler.txt'))

    def collect(self):
        raise RuntimeError('broken event index')

    monkeypatch.setattr(PodGroupEventCollector, 'collect', collect)
    dd_run_check(
        KaiSchedulerCheck(CHECK_NAME, {}, [{'scheduler_endpoint': SCHEDULER_ENDPOINT, 'collect_podgroup_events': True}])
    )

    assert 'Cannot collect KAI PodGroup events: broken event index' in caplog.text
    assert aggregator.metric_names
