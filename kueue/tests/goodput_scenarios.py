# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Synthetic scheduling scenarios for the scheduling goodput.

Each scenario is a sequence of Workload List snapshots taken at known times, with the GPU-seconds every Workload is
expected to contribute at each poll. `test_goodput.py` asserts them, and running this module prints one validation
table per scenario:

    ddev test kueue -- -k scenario_tables -s
"""

from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from datadog_checks.kueue.goodput import Category, GoodputTracker, QueueKey, SchedulingState, aggregate, classify

WALL_START = 1_781_604_000.0  # 2026-06-16T10:00:00Z


def iso(t: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(WALL_START + t, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def condition(type_, status, reason, t=0):
    return {'type': type_, 'status': status, 'reason': reason, 'lastTransitionTime': iso(t), 'message': ''}


# Condition sets for the Kueue states used in the scenarios, as Kueue reports them with `waitForPodsReady`.
STATES = {
    'pending_quota': [condition('QuotaReserved', 'False', 'WaitingForQuota')],
    'pending_max_quota': [condition('QuotaReserved', 'False', 'ExceedsMaxQuota')],
    'quota_reserved': [
        condition('QuotaReserved', 'True', 'QuotaReserved'),
        condition('Admitted', 'False', 'UnsatisfiedAdmissionChecks'),
    ],
    'admitted_pods_pending': [
        condition('QuotaReserved', 'True', 'QuotaReserved'),
        condition('Admitted', 'True', 'Admitted'),
        condition('PodsReady', 'False', 'WaitForStart'),
    ],
    'admitted_no_podsready': [
        condition('QuotaReserved', 'True', 'QuotaReserved'),
        condition('Admitted', 'True', 'Admitted'),
    ],
    'running': [
        condition('QuotaReserved', 'True', 'QuotaReserved'),
        condition('Admitted', 'True', 'Admitted'),
        condition('PodsReady', 'True', 'Started'),
    ],
    # Kueue reports it when a ready pod stops being ready, and for a few seconds while completing pods terminate.
    'recovering': [
        condition('QuotaReserved', 'True', 'QuotaReserved'),
        condition('Admitted', 'True', 'Admitted'),
        condition('PodsReady', 'False', 'WaitForRecovery'),
    ],
    'preempted': [
        condition('QuotaReserved', 'False', 'Pending'),
        condition('Admitted', 'False', 'NoReservation'),
        condition('PodsReady', 'False', 'WaitForStart'),
        condition('Evicted', 'True', 'Preempted'),
        condition('Preempted', 'True', 'InClusterQueue'),
    ],
}


def workload(
    name,
    state,
    gpus_per_pod,
    pods=1,
    namespace='team-a',
    local_queue='gpu',
    cluster_queue='a100-cq',
    finished_at=None,
    active=True,
):
    """Build a Kueue Workload. The ClusterQueue is only in the admission once quota is reserved, as in Kueue."""
    # `finished` is `running` plus a `Finished` condition; any other unknown state is a typo in the test.
    conditions = [dict(c) for c in STATES['running' if state == 'finished' else state]]
    if state == 'finished':
        conditions.append(condition('Finished', 'True', 'Succeeded', finished_at))
    status = {'conditions': conditions}
    if state in (
        'quota_reserved',
        'admitted_pods_pending',
        'admitted_no_podsready',
        'running',
        'recovering',
        'finished',
    ):
        status['admission'] = {'clusterQueue': cluster_queue}
    spec = {
        'queueName': local_queue,
        'podSets': [
            {
                'name': 'main',
                'count': pods,
                'template': {
                    'spec': {
                        'containers': [{'name': 'trainer', 'resources': {'limits': {'nvidia.com/gpu': gpus_per_pod}}}]
                    }
                },
            }
        ],
    }
    if not active:
        spec['active'] = False
    return {
        'metadata': {'name': name, 'namespace': namespace, 'uid': f'{namespace}-{name}-uid'},
        'spec': spec,
        'status': status,
    }


class Poll(NamedTuple):
    t: float
    workloads: list[dict]
    # Expected (badput, fully_admitted) GPU-seconds per Workload name for the interval ending at this poll.
    expected: dict[str, tuple[float, float]]


class Scenario(NamedTuple):
    name: str
    description: str
    polls: list[Poll]
    # Expected (badput, fully_admitted) GPU-seconds per (namespace, local_queue, cluster_queue) over the whole run.
    expected_queues: dict[QueueKey, tuple[float, float]]


class Row(NamedTuple):
    scenario: str
    poll: float
    workload: str
    state: str
    gpus: float
    interval: float
    expected: tuple[float, float]
    actual: tuple[float, float]
    queue: QueueKey

    @property
    def passed(self) -> bool:
        return self.expected == self.actual


class Clock:
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def wall(self):
        return WALL_START + self.t


def cluster_queue_from_tagger(namespace, local_queue):
    """What the Agent tagger returns for the LocalQueues of the scenarios."""
    return {('team-a', 'gpu'): 'a100-cq', ('team-b', 'research'): 'h100-cq'}.get((namespace, local_queue))


def run(scenario: Scenario) -> tuple[list[Row], dict[QueueKey, tuple[float, float]]]:
    clock = Clock()
    tracker = GoodputTracker(monotonic=clock.monotonic, wall=clock.wall)
    rows = []
    totals: dict[QueueKey, list[float]] = defaultdict(lambda: [0.0, 0.0])
    previous_t = None
    for poll in scenario.polls:
        clock.t = poll.t
        held = dict(tracker.previous or {})
        contributions = tracker.update(poll.workloads, cluster_queue_from_tagger)
        for queue, queue_totals in aggregate(contributions).items():
            totals[queue][0] += queue_totals.badput
            totals[queue][1] += queue_totals.fully_admitted

        actual = {}
        for c in contributions:
            actual[c.name.split('/', 1)[1]] = (
                c.gpu_seconds if c.category == Category.BADPUT else 0.0,
                c.gpu_seconds if c.category == Category.FULLY_ADMITTED else 0.0,
            )
        names = {w['metadata']['name'] for w in poll.workloads} | set(poll.expected)
        names |= {obs.name.split('/', 1)[1] for obs in held.values()}
        for name in sorted(names):
            obs = next((o for o in held.values() if o.name.endswith(f'/{name}')), None)
            current = next((w for w in poll.workloads if w['metadata']['name'] == name), None)
            if obs:
                state = f'{obs.state.value} (held)'
            elif current is not None and classify(current) == SchedulingState.FINISHED:
                state = 'finished, no longer tracked'
            else:
                state = 'baseline'
            if current is None:
                state += ', gone'
            rows.append(
                Row(
                    scenario.name,
                    poll.t,
                    name,
                    state,
                    obs.gpus if obs else _gpus(current),
                    poll.t - previous_t if previous_t is not None else 0.0,
                    poll.expected.get(name, (0.0, 0.0)),
                    actual.get(name, (0.0, 0.0)),
                    obs.queue if obs else None,
                )
            )
        previous_t = poll.t
    return rows, {queue: tuple(values) for queue, values in totals.items()}


def _gpus(workload):
    from datadog_checks.kueue.goodput import requested_gpus

    return requested_gpus(workload) if workload else 0.0


A100 = QueueKey('team-a', 'gpu', 'a100-cq')
H100 = QueueKey('team-b', 'research', 'h100-cq')

SCENARIOS = [
    Scenario(
        'normal',
        'A satisfiable 4-GPU Workload waits, is admitted, becomes ready, runs and finishes at t=45.',
        [
            Poll(0, [workload('train', 'pending_quota', 4)], {}),
            Poll(10, [workload('train', 'pending_quota', 4)], {'train': (40, 0)}),
            Poll(20, [workload('train', 'admitted_pods_pending', 4)], {'train': (40, 0)}),
            Poll(30, [workload('train', 'running', 4)], {'train': (40, 0)}),
            Poll(40, [workload('train', 'running', 4)], {'train': (0, 40)}),
            Poll(50, [workload('train', 'finished', 4, finished_at=45)], {'train': (0, 20)}),
            Poll(60, [workload('train', 'finished', 4, finished_at=45)], {}),
        ],
        {A100: (120, 60)},
    ),
    Scenario(
        'insufficient_resources',
        'A 16-GPU Workload exceeds the maximum quota and never starts.',
        [
            Poll(t, [workload('huge', 'pending_max_quota', 8, pods=2)], {} if t == 0 else {'huge': (160, 0)})
            for t in (0, 10, 20, 30)
        ],
        {A100: (480, 0)},
    ),
    Scenario(
        'partial_scheduling',
        'An admitted 2x4-GPU Workload with one pod running: Kueue keeps PodsReady=False until both are ready.',
        [
            Poll(0, [workload('dist', 'admitted_pods_pending', 4, pods=2)], {}),
            Poll(10, [workload('dist', 'admitted_pods_pending', 4, pods=2)], {'dist': (80, 0)}),
            Poll(20, [workload('dist', 'running', 4, pods=2)], {'dist': (80, 0)}),
            Poll(30, [workload('dist', 'running', 4, pods=2)], {'dist': (0, 80)}),
        ],
        {A100: (160, 80)},
    ),
    Scenario(
        'admitted_unable_to_run',
        'Quota reserved, then admitted, with pods pending for two polls before running.',
        [
            Poll(0, [workload('job', 'quota_reserved', 2)], {}),
            Poll(10, [workload('job', 'admitted_pods_pending', 2)], {'job': (20, 0)}),
            Poll(20, [workload('job', 'admitted_pods_pending', 2)], {'job': (20, 0)}),
            Poll(30, [workload('job', 'running', 2)], {'job': (20, 0)}),
            Poll(40, [workload('job', 'running', 2)], {'job': (0, 20)}),
        ],
        {A100: (60, 20)},
    ),
    Scenario(
        'kueue_quota_exhausted',
        'An 8-GPU Workload runs while 4-GPU Workloads wait for A100 quota; a second one arrives at t=10.',
        [
            Poll(0, [workload('running', 'running', 8), workload('wait-1', 'pending_quota', 4)], {}),
            Poll(
                10,
                [
                    workload('running', 'running', 8),
                    workload('wait-1', 'pending_quota', 4),
                    workload('wait-2', 'pending_quota', 4),
                ],
                {'running': (0, 80), 'wait-1': (40, 0)},
            ),
            Poll(
                20,
                [
                    workload('running', 'running', 8),
                    workload('wait-1', 'pending_quota', 4),
                    workload('wait-2', 'pending_quota', 4),
                ],
                {'running': (0, 80), 'wait-1': (40, 0), 'wait-2': (40, 0)},
            ),
        ],
        {A100: (120, 160)},
    ),
    Scenario(
        'multiple_workloads_one_queue',
        'Six Workloads in different states in one queue, over one 10s interval.',
        [
            Poll(
                0,
                [
                    workload('w1-running', 'running', 8),
                    workload('w2-pending', 'pending_quota', 2),
                    workload('w3-not-ready', 'admitted_pods_pending', 2, pods=2),
                    workload('w4-no-podsready', 'admitted_no_podsready', 2),
                    workload('w5-finishing', 'running', 4),
                    workload('w6-inactive', 'pending_quota', 4, active=False),
                ],
                {},
            ),
            Poll(
                10,
                [
                    workload('w1-running', 'running', 8),
                    workload('w2-pending', 'pending_quota', 2),
                    workload('w3-not-ready', 'admitted_pods_pending', 2, pods=2),
                    workload('w4-no-podsready', 'admitted_no_podsready', 2),
                    workload('w5-finishing', 'finished', 4, finished_at=5),
                    workload('w6-inactive', 'pending_quota', 4, active=False),
                ],
                {'w1-running': (0, 80), 'w2-pending': (20, 0), 'w3-not-ready': (40, 0), 'w5-finishing': (0, 20)},
            ),
        ],
        {A100: (60, 100)},
    ),
    Scenario(
        'multiple_queues',
        'team-a/gpu runs one Workload and waits on another; team-b/research only waits.',
        [
            Poll(
                0,
                [
                    workload('a-run', 'running', 4),
                    workload('a-wait', 'pending_quota', 4),
                    workload('b-wait', 'pending_quota', 8, namespace='team-b', local_queue='research'),
                ],
                {},
            ),
            Poll(
                10,
                [
                    workload('a-run', 'running', 4),
                    workload('a-wait', 'pending_quota', 4),
                    workload('b-wait', 'pending_quota', 8, namespace='team-b', local_queue='research'),
                ],
                {'a-run': (0, 40), 'a-wait': (40, 0), 'b-wait': (80, 0)},
            ),
        ],
        {A100: (40, 40), H100: (80, 0)},
    ),
]


def goodput(badput, fully_admitted):
    total = badput + fully_admitted
    return fully_admitted / total if total else None


def markdown_tables() -> str:
    lines = []
    for scenario in SCENARIOS:
        rows, totals = run(scenario)
        lines += [f'### {scenario.name}', '', scenario.description, '']
        lines.append(
            '| Poll | Workload | State during interval | GPUs | Interval (s) | Expected badput | '
            'Expected fully admitted | Actual (badput, fully) | Queue | Result |'
        )
        lines.append('|---|---|---|---|---|---|---|---|---|---|')
        for row in rows:
            queue = '/'.join(str(part) for part in row.queue) if row.queue else '-'
            lines.append(
                f'| t={row.poll:g} | {row.workload} | {row.state} | {row.gpus:g} | {row.interval:g} | '
                f'{row.expected[0]:g} | {row.expected[1]:g} | ({row.actual[0]:g}, {row.actual[1]:g}) | {queue} | '
                f'{"PASS" if row.passed else "FAIL"} |'
            )
        lines.append('')
        for queue, (badput, fully) in sorted(totals.items()):
            expected = scenario.expected_queues.get(queue)
            ratio = goodput(badput, fully)
            lines.append(
                f'Queue {"/".join(queue)}: badput={badput:g} GPU-s, fully_admitted={fully:g} GPU-s, '
                f'goodput={fully:g}/({fully:g}+{badput:g})={ratio:.3f} '
                f'({"PASS" if expected == (badput, fully) else f"FAIL, expected {expected}"})'
            )
        lines.append('')
    return '\n'.join(lines)


if __name__ == '__main__':
    print(markdown_tables())
