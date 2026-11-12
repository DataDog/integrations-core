# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Scheduling goodput for Kueue Workloads.

On each successful poll every GPU Workload is classified into one `SchedulingState`, and the GPU-time of the interval
since the previous poll is attributed to exactly one category:

    contribution = elapsed_seconds x requested_gpus

The category is the one of the state observed at the *start* of the interval (sample and hold): a Workload only
contributes fully admitted time for an interval that began with Kueue reporting all its pods ready, so badput never
stops before the Workload is observed fully runnable. Each Workload submits its contributions as its own count series
in GPU-hours, the unit of the design doc. The goodput ratio is left to the query layer:

    fully_admitted_time / (fully_admitted_time + badput_time)

This module only depends on the Workload JSON, so it can be tested without the Kubernetes API.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import datetime
from enum import Enum
from typing import NamedTuple

BADPUT_METRIC = 'gpu.scheduling.badput_time'
SECONDS_PER_HOUR = 3600
FULLY_ADMITTED_METRIC = 'gpu.scheduling.fully_admitted_time'

# Extended resources counted as whole GPUs. MIG profiles and other partitions are not counted.
GPU_RESOURCE_NAMES = ('nvidia.com/gpu', 'amd.com/gpu')

SCHEDULER_TAG_VALUE = 'kueue'

# Badput is tagged with why the Workload waits: `reason` holds a value shared with the other schedulers, and
# `scheduler_reason` the raw Kueue reason it comes from.
REASON_TAG = 'reason'
SCHEDULER_REASON_TAG = 'scheduler_reason'
# Every series is per workload, tagged like the Workload lifecycle events.
WORKLOAD_TAG = 'kueue_workload'
UNKNOWN_REASON = 'unknown'

# Structured Kueue reasons. Most `QuotaReserved` ones need the `UnadmittedWorkloadsObservability` feature gate;
# without it Kueue reports `Pending` or `Inadmissible`, and the cause is only in the message.
KUEUE_REASONS = {
    'WaitingForQuota': 'quota_exhausted',
    'ExceedsMaxQuota': 'exceeds_max_quota',
    'NoMatchingFlavor': 'no_matching_resources',
    'TopologyPlacementFailed': 'no_matching_resources',
    'DRAResourcesUnresolved': 'no_matching_resources',
    'WaitingForPreemptedWorkloads': 'waiting_for_preemption',
    'UnsatisfiedAdmissionChecks': 'admission_checks',
    # Without `UnadmittedWorkloadsObservability`, Kueue reports the admission checks on `Admitted` with these reasons.
    'UnsatisfiedChecks': 'admission_checks',
    'NoReservationUnsatisfiedChecks': 'admission_checks',
    'PendingEvaluation': 'admission_checks',
    'WaitForStart': 'waiting_for_pods',
    'WaitingForPodsReady': 'waiting_for_pods',
    'Misconfigured': 'misconfigured',
    # `Evicted` reasons other than preemption: the Workload is requeued and waits again.
    'PodsReadyTimeout': 'waiting_for_pods',
    'AdmissionCheck': 'admission_checks',
    'ClusterQueueStopped': 'queue_stopped',
    'LocalQueueStopped': 'queue_stopped',
}
# Message fragments Kueue writes for `Pending` and `Inadmissible`, checked in order.
KUEUE_MESSAGE_REASONS = (
    ('maximum capacity', 'exceeds_max_quota'),
    ('insufficient unused quota', 'quota_exhausted'),
    ('insufficient quota', 'quota_exhausted'),
    ('waiting for workloads to be preempted', 'waiting_for_preemption'),
    ("couldn't assign flavors", 'no_matching_resources'),
    ("doesn't exist", 'misconfigured'),
    ('is inactive', 'misconfigured'),
)


class SchedulingState(str, Enum):
    WAITING = 'waiting'
    """Not fully runnable yet: no quota reserved, admission checks pending, or admitted with pods not all ready."""
    PREEMPTED = 'preempted'
    """Evicted by preemption and not running again. It waits for GPUs again, so it is badput."""
    RUNNABLE = 'runnable'
    """Admitted, and Kueue reports `PodsReady=True`: at least `podSets[*].count` pods are ready or succeeded."""
    RECOVERING = 'recovering'
    """Was ready, and Kueue reports `PodsReady=False` with `WaitForRecovery`: some pods stopped being ready. Kueue
    also reports it for a few seconds when the pods complete, before `Finished`, so it is not counted as waiting."""
    READINESS_UNKNOWN = 'readiness_unknown'
    """Admitted without a `PodsReady` condition. Kueue only maintains it when `waitForPodsReady` is enabled."""
    INACTIVE = 'inactive'
    """Deactivated with `spec.active: false`. It is not waiting for resources."""
    FINISHED = 'finished'


class Category(str, Enum):
    BADPUT = 'badput'
    FULLY_ADMITTED = 'fully_admitted'
    NONE = 'none'


STATE_CATEGORY = {
    SchedulingState.WAITING: Category.BADPUT,
    # A preempted Workload waits for GPUs again, like any other wait. Its own state tags that badput with
    # `reason:preempted`, so that queries can separate it from the other waits.
    SchedulingState.PREEMPTED: Category.BADPUT,
    SchedulingState.RUNNABLE: Category.FULLY_ADMITTED,
    # Kueue also reports it while the pods of a completing Workload terminate, which is not a wait.
    SchedulingState.RECOVERING: Category.NONE,
    # Without `waitForPodsReady`, Kueue never reports when the pods are ready: see `GoodputTracker.pods_ready_missing`.
    SchedulingState.READINESS_UNKNOWN: Category.NONE,
    SchedulingState.INACTIVE: Category.NONE,
    SchedulingState.FINISHED: Category.NONE,
}


class QueueKey(NamedTuple):
    namespace: str | None
    local_queue: str | None
    cluster_queue: str | None


class Observation(NamedTuple):
    name: str
    state: SchedulingState
    gpus: float
    queue: QueueKey
    finished_at: float | None
    """Unix time of the `Finished` transition, used to stop the last interval at completion."""
    reason: str | None
    """Raw reason of the blocking condition, submitted as `scheduler_reason`."""
    cause: str | None = None
    """Reason normalized across schedulers, submitted as `reason`. Only set for badput states."""


class Contribution(NamedTuple):
    uid: str
    name: str
    queue: QueueKey
    state: SchedulingState
    category: Category
    gpus: float
    seconds: float
    cause: str | None = None
    reason: str | None = None

    @property
    def gpu_seconds(self) -> float:
        return self.gpus * self.seconds


class QueueTotals(NamedTuple):
    badput: float
    fully_admitted: float

    @property
    def goodput(self) -> float | None:
        total = self.badput + self.fully_admitted
        return self.fully_admitted / total if total else None


def conditions_by_type(workload: dict) -> dict[str, dict]:
    return {
        condition['type']: condition
        for condition in (workload.get('status') or {}).get('conditions') or []
        if condition.get('type')
    }


def is_true(condition: dict | None) -> bool:
    return bool(condition) and condition.get('status') == 'True'


def classify(workload: dict) -> SchedulingState:
    conditions = conditions_by_type(workload)

    if is_true(conditions.get('Finished')):
        return SchedulingState.FINISHED
    if (workload.get('spec') or {}).get('active') is False:
        return SchedulingState.INACTIVE

    # An evicted Workload is not fully runnable, even while `Admitted` and `PodsReady` are still True for a moment.
    # Kueue sets `Evicted=False` once it admits the Workload again.
    evicted = conditions.get('Evicted')
    if is_true(evicted):
        if evicted.get('reason') == 'Preempted' or is_true(conditions.get('Preempted')):
            return SchedulingState.PREEMPTED
        return SchedulingState.WAITING

    admitted = is_true(conditions.get('Admitted'))
    pods_ready = conditions.get('PodsReady')
    # `PodsReady` can stay True for a moment after the admission is removed, so it is only trusted together with
    # `Admitted`.
    if admitted and is_true(pods_ready):
        return SchedulingState.RUNNABLE

    if admitted and pods_ready is not None and pods_ready.get('reason') == 'WaitForRecovery':
        return SchedulingState.RECOVERING

    if admitted and pods_ready is None:
        return SchedulingState.READINESS_UNKNOWN

    return SchedulingState.WAITING


def blocking_condition(workload: dict, state: SchedulingState) -> dict | None:
    """Return the condition that explains a badput state: the preemption or eviction, or the first of
    `QuotaReserved`, `Admitted` and `PodsReady` that is False."""
    conditions = conditions_by_type(workload)
    if state == SchedulingState.PREEMPTED:
        return conditions.get('Preempted') or conditions.get('Evicted')
    if state != SchedulingState.WAITING:
        return None
    # An evicted Workload keeps `Evicted=True` until it is admitted again. Once it waits for quota again, the
    # `QuotaReserved=False` reason is the current one; until then, such as while `Admitted` and `PodsReady` are still
    # True for a moment, the eviction explains the wait.
    if is_true(conditions.get('Evicted')):
        quota = conditions.get('QuotaReserved')
        if quota and quota.get('status') == 'False':
            return quota
        return conditions['Evicted']
    for condition_type in ('QuotaReserved', 'Admitted', 'PodsReady'):
        condition = conditions.get(condition_type)
        if condition and condition.get('status') == 'False':
            return condition
    return None


def blocking_reason(workload: dict, state: SchedulingState) -> str | None:
    """Return the raw scheduler reason for a badput state, without normalizing it."""
    return (blocking_condition(workload, state) or {}).get('reason')


def normalize_reason(state: SchedulingState, condition: dict | None) -> str | None:
    """Map the blocking condition of a badput state to a reason shared with the other schedulers."""
    if state == SchedulingState.PREEMPTED:
        return 'preempted'
    if state != SchedulingState.WAITING:
        return None
    if not condition:
        return UNKNOWN_REASON
    reason = condition.get('reason') or ''
    if reason in KUEUE_REASONS:
        return KUEUE_REASONS[reason]
    message = (condition.get('message') or '').lower()
    for fragment, normalized in KUEUE_MESSAGE_REASONS:
        if fragment in message:
            return normalized
    return UNKNOWN_REASON


def parse_gpu_quantity(value) -> float:
    """Parse a GPU count. Kubernetes suffixes are rejected instead of guessed."""
    if isinstance(value, bool):
        raise ValueError(f'invalid GPU quantity {value!r}')
    if isinstance(value, (int, float)):
        quantity = float(value)
    else:
        quantity = float(str(value).strip())
    if quantity < 0:
        raise ValueError(f'negative GPU quantity {value!r}')
    return quantity


def container_gpus(container: dict, resource_names: Iterable[str]) -> float:
    resources = container.get('resources') or {}
    requested = resources.get('requests') or {}
    limits = resources.get('limits') or {}
    total = 0.0
    for name in resource_names:
        # Kubernetes defaults the request of an extended resource to its limit, and requires them to match.
        value = requested.get(name, limits.get(name))
        if value is not None:
            total += parse_gpu_quantity(value)
    return total


def pod_gpus(pod_spec: dict, resource_names: Iterable[str]) -> float:
    """Return the effective GPU request of one pod, as the kube-scheduler computes it."""
    resource_names = tuple(resource_names)
    running = sum(container_gpus(c, resource_names) for c in pod_spec.get('containers') or [])
    init_peak = 0.0
    sidecars = 0.0
    for container in pod_spec.get('initContainers') or []:
        gpus = container_gpus(container, resource_names)
        if container.get('restartPolicy') == 'Always':
            # Sidecars keep running next to the app containers and the later init containers.
            sidecars += gpus
        else:
            init_peak = max(init_peak, sidecars + gpus)
    return max(running + sidecars, init_peak)


def requested_gpus(workload: dict, resource_names: Iterable[str] = GPU_RESOURCE_NAMES) -> float:
    """Return the GPUs the Workload still needs: `sum((pods - reclaimable) x GPUs per pod)` over its PodSets.

    The pods of a PodSet are the ones of its spec, or the ones Kueue admitted once it reserved quota: with partial
    admission, Kueue can admit fewer pods than the spec asks for, and the Workload runs with those. Pods that Kueue
    reports in `status.reclaimablePods`, such as pods that already completed, no longer hold GPUs, so they are not
    counted: Kueue counts completed pods as ready, and the Workload would otherwise keep its whole request as fully
    admitted while only some of its pods run.
    """
    status = workload.get('status') or {}
    reclaimable = {entry.get('name'): entry.get('count') or 0 for entry in status.get('reclaimablePods') or []}
    admitted = {
        assignment.get('name'): assignment['count']
        for assignment in (status.get('admission') or {}).get('podSetAssignments') or []
        if isinstance(assignment.get('count'), int)
    }
    total = 0.0
    for pod_set in (workload.get('spec') or {}).get('podSets') or []:
        pods = admitted.get(pod_set.get('name'), pod_set.get('count', 1))
        count = max(pods - reclaimable.get(pod_set.get('name'), 0), 0)
        pod_spec = (pod_set.get('template') or {}).get('spec') or {}
        total += count * pod_gpus(pod_spec, resource_names)
    return total


def parse_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    if value.endswith('Z'):
        value = f'{value[:-1]}+00:00'
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def observe(workload: dict, cluster_queue_resolver: Callable[[str, str], str | None] | None = None) -> Observation:
    metadata = workload.get('metadata') or {}
    spec = workload.get('spec') or {}
    namespace = metadata.get('namespace')
    local_queue = spec.get('queueName')
    cluster_queue = ((workload.get('status') or {}).get('admission') or {}).get('clusterQueue')
    if not cluster_queue and cluster_queue_resolver and namespace and local_queue:
        # Unadmitted Workloads have no admission, so their ClusterQueue comes from their LocalQueue.
        cluster_queue = cluster_queue_resolver(namespace, local_queue)

    state = classify(workload)
    finished = conditions_by_type(workload).get('Finished')
    return Observation(
        name=f'{namespace}/{metadata.get("name")}',
        state=state,
        gpus=requested_gpus(workload),
        queue=QueueKey(namespace, local_queue, cluster_queue),
        finished_at=parse_timestamp(finished.get('lastTransitionTime')) if is_true(finished) else None,
        reason=blocking_reason(workload, state),
        cause=normalize_reason(state, blocking_condition(workload, state)),
    )


def queue_tags(queue: QueueKey) -> list[str]:
    tags = [f'kube_scheduler:{SCHEDULER_TAG_VALUE}']
    if queue.namespace:
        tags.append(f'kube_namespace:{queue.namespace}')
    if queue.local_queue:
        tags.append(f'kueue_local_queue:{queue.local_queue}')
    if queue.cluster_queue:
        tags.append(f'kueue_cluster_queue:{queue.cluster_queue}')
        tags.append(f'kube_scheduler_queue:{queue.cluster_queue}')
    return tags


class GoodputTracker:
    """Keep the Workload observations of the previous successful poll and compute the contributions of the next one.

    Clocks are injectable for tests: `monotonic` measures the interval, so wall clock changes cannot make it negative,
    and `wall` only places a `Finished` transition inside the interval.
    """

    def __init__(
        self,
        log=None,
        monotonic: Callable[[], float] = time.monotonic,
        wall: Callable[[], float] = time.time,
    ):
        self.log = log
        self.monotonic = monotonic
        self.wall = wall
        self.previous: dict[str, Observation] | None = None
        self.previous_monotonic: float | None = None
        self.previous_wall: float | None = None
        self.warned_readiness_unknown = False
        self.pods_ready_missing = False
        """Whether Kueue runs without `waitForPodsReady`, so that fully admitted time cannot be measured."""
        # GPU Workloads of the last poll whose ClusterQueue was unknown, and Workloads that could not be parsed, which
        # the check reports.
        self.unresolved_cluster_queues = 0
        self.skipped = 0

    def reset(self) -> None:
        """Forget the baseline, so that the next poll does not attribute an interval whose state was not observed."""
        if self.previous is not None and self.log:
            self.log.debug('Scheduling goodput: resetting the baseline of %d Workloads', len(self.previous))
        self.previous = None
        self.previous_monotonic = None
        self.previous_wall = None

    def update(
        self,
        workloads: Iterable[dict],
        cluster_queue_resolver: Callable[[str, str], str | None] | None = None,
    ) -> list[Contribution]:
        """Record a successful poll and return the contributions of the interval since the previous one."""
        now = self.monotonic()
        now_wall = self.wall()

        current: dict[str, Observation] = {}
        self.skipped = 0
        for workload in workloads:
            metadata = workload.get('metadata') or {}
            uid = metadata.get('uid')
            if not uid:
                continue
            try:
                observation = observe(workload, cluster_queue_resolver)
            except Exception as e:
                # Not tracking it means it re-baselines once it can be parsed, instead of contributing a guess.
                self.skipped += 1
                if self.log:
                    self.log.debug(
                        'Scheduling goodput: skipping Workload %s/%s: %s',
                        metadata.get('namespace'),
                        metadata.get('name'),
                        e,
                        exc_info=True,
                    )
                continue
            previous = (self.previous or {}).get(uid)
            if (
                observation.queue.cluster_queue is None
                and previous is not None
                and previous.queue.cluster_queue
                and previous.queue.local_queue == observation.queue.local_queue
            ):
                # Keep the ClusterQueue once known, so that the series of a Workload keep the same queue tags when the
                # tagger briefly cannot resolve its LocalQueue.
                observation = observation._replace(queue=previous.queue)
            if observation.gpus <= 0 and previous is None:
                continue
            # A tracked Workload whose GPU PodSets are all reclaimable, such as when its GPU pods completed but CPU
            # ones still run, keeps 0 GPUs as its baseline: its last interval uses the GPUs of the previous poll, and
            # the next ones count no GPU time.
            if observation.state == SchedulingState.FINISHED and (self.previous is None or uid not in self.previous):
                # Already finished when first seen: there is no interval to attribute.
                continue
            current[uid] = observation

        self.unresolved_cluster_queues = sum(1 for obs in current.values() if obs.queue.cluster_queue is None)
        contributions = []
        if self.previous is not None and self.previous_monotonic is not None:
            elapsed = now - self.previous_monotonic
            if elapsed <= 0:
                self.debug('Scheduling goodput: non-positive interval %.3fs, skipping it', elapsed)
            else:
                contributions = self.contributions(current, elapsed, now_wall)

        self.log_transitions(current)
        # Finished Workloads contributed their last interval and are not tracked any longer. Workloads that
        # disappeared are dropped without a contribution, as when they were deleted is unknown.
        self.previous = {uid: obs for uid, obs in current.items() if obs.state != SchedulingState.FINISHED}
        self.previous_monotonic = now
        self.previous_wall = now_wall
        return contributions

    def contributions(self, current: dict[str, Observation], elapsed: float, now_wall: float) -> list[Contribution]:
        contributions = []
        for uid, observation in current.items():
            previous = self.previous.get(uid)
            if previous is None:
                # First observation: it only sets the baseline.
                continue
            category = STATE_CATEGORY[previous.state]
            if category == Category.NONE or previous.gpus <= 0:
                continue

            seconds = elapsed
            if observation.finished_at is not None and self.previous_wall is not None:
                # Stop at completion, clamped to the interval in case the API server and Agent clocks disagree.
                seconds = min(max(observation.finished_at - self.previous_wall, 0.0), elapsed)

            contributions.append(
                Contribution(
                    uid=uid,
                    name=previous.name,
                    queue=previous.queue,
                    state=previous.state,
                    category=category,
                    gpus=previous.gpus,
                    seconds=seconds,
                    cause=previous.cause,
                    reason=previous.reason,
                )
            )
        return contributions

    def log_transitions(self, current: dict[str, Observation]) -> None:
        unknown = 0
        pods_ready_reported = False
        for uid, observation in current.items():
            previous = (self.previous or {}).get(uid)
            # A Workload admitted for a whole interval without `PodsReady` means `waitForPodsReady` is off, and one
            # that is ready or recovering means it is on.
            if observation.state == SchedulingState.READINESS_UNKNOWN and (
                previous is not None and previous.state == SchedulingState.READINESS_UNKNOWN
            ):
                unknown += 1
            if observation.state in (SchedulingState.RUNNABLE, SchedulingState.RECOVERING):
                pods_ready_reported = True
            if previous is None or previous.state != observation.state:
                self.debug(
                    'Scheduling goodput: Workload %s (%g GPUs, queue %s) %s -> %s (reason: %s, scheduler_reason: %s)',
                    observation.name,
                    observation.gpus,
                    observation.queue,
                    previous.state.value if previous else 'new',
                    observation.state.value,
                    observation.cause,
                    observation.reason,
                )
        if pods_ready_reported:
            self.pods_ready_missing = False
        elif unknown:
            self.pods_ready_missing = True
        if self.pods_ready_missing and not self.warned_readiness_unknown and self.log:
            self.warned_readiness_unknown = True
            self.log.warning(
                'Scheduling goodput: %d admitted GPU Workloads have no PodsReady condition, so the fully admitted time '
                'cannot be measured and no goodput metric is submitted. Enable waitForPodsReady in the Kueue '
                'configuration.',
                unknown,
            )

    def debug(self, *args) -> None:
        if self.log:
            self.log.debug(*args)


def aggregate(contributions: Iterable[Contribution]) -> dict[QueueKey, QueueTotals]:
    """Sum contributions per queue, for the debug logs and tests: the metrics are submitted per workload, and queries
    sum them. Each queue gets both totals, so the goodput ratio is 0 rather than missing when
    all of its Workloads wait."""
    sums: dict[QueueKey, dict[Category, float]] = defaultdict(lambda: defaultdict(float))
    for contribution in contributions:
        sums[contribution.queue][contribution.category] += contribution.gpu_seconds
    return {
        queue: QueueTotals(totals[Category.BADPUT], totals[Category.FULLY_ADMITTED]) for queue, totals in sums.items()
    }


def badput_by_reason(contributions: Iterable[Contribution]) -> dict[QueueKey, dict[tuple[str, str | None], float]]:
    """Sum the badput GPU-seconds per queue and (normalized reason, raw scheduler reason), for the debug logs."""
    sums: dict[QueueKey, dict[tuple[str, str | None], float]] = defaultdict(lambda: defaultdict(float))
    for contribution in contributions:
        if contribution.category == Category.BADPUT:
            sums[contribution.queue][(contribution.cause or UNKNOWN_REASON, contribution.reason)] += (
                contribution.gpu_seconds
            )
    return {queue: dict(reasons) for queue, reasons in sums.items()}


def reason_tags(reason: str, scheduler_reason: str | None) -> list[str]:
    tags = [f'{REASON_TAG}:{reason}']
    if scheduler_reason:
        tags.append(f'{SCHEDULER_REASON_TAG}:{scheduler_reason}')
    return tags


def workload_points(contributions: Iterable[Contribution]) -> list[tuple[str, float, list[str]]]:
    """Return the `(metric, GPU-hours, tags)` points of the interval, one series per workload and metric.

    Both metrics are submitted per workload, tagged with its queue, so that summing the series by any tag, such as the
    queue, the cluster or the reason, gives the right GPU-hours. The other metric is submitted as 0, so that the
    goodput of a group whose workloads all wait, or all run, is 0 or 1 rather than missing.
    """
    points: list[tuple[str, float, list[str]]] = []
    for contribution in contributions:
        tags = [*queue_tags(contribution.queue), f'{WORKLOAD_TAG}:{workload_name(contribution.name)}']
        hours = contribution.gpu_seconds / SECONDS_PER_HOUR
        if contribution.category == Category.BADPUT:
            reason = contribution.cause or UNKNOWN_REASON
            points.append((BADPUT_METRIC, hours, [*tags, *reason_tags(reason, contribution.reason)]))
            points.append((FULLY_ADMITTED_METRIC, 0.0, tags))
        else:
            points.append((FULLY_ADMITTED_METRIC, hours, tags))
            points.append((BADPUT_METRIC, 0.0, tags))
    return points


def workload_name(name: str) -> str:
    """Return the workload name of an observation name, which is `<namespace>/<name>`."""
    return name.split('/', 1)[-1]
