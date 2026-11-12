# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Scheduling goodput for KAI PodGroups.

On each successful poll every GPU PodGroup is classified into one `SchedulingState`, and the GPU-time of the interval
since the previous poll is attributed to exactly one category:

    contribution = elapsed_seconds x requested_gpus

The category is the one of the state observed at the *start* of the interval (sample and hold), as in the Kueue check.
Each PodGroup submits its contributions as its own count series in GPU-hours, the unit of the design doc. The
goodput ratio is left to the query layer:

    fully_admitted_time / (fully_admitted_time + badput_time)

KAI has no equivalent of Kueue's `PodsReady`: a PodGroup only records when the scheduler last allocated or evicted its
pods, and it keeps its `UnschedulableOnNodePool` condition while only some of its pods run. Whether a PodGroup is fully
runnable is therefore read from its pods, which carry the PodGroup name in the `pod-group-name` annotation.

This module only depends on the PodGroup and pod JSON, so it can be tested without the Kubernetes API.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import TYPE_CHECKING, Any, NamedTuple

from .kube_client import KubernetesAPIClient
from .podgroup_events import LAST_EVICTION_ANNOTATION, LAST_START_ANNOTATION, UNSCHEDULABLE_CONDITION

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck

BADPUT_METRIC = 'gpu.scheduling.badput_time'
SECONDS_PER_HOUR = 3600
FULLY_ADMITTED_METRIC = 'gpu.scheduling.fully_admitted_time'

# Extended resources counted as whole GPUs. MIG profiles and other partitions are not counted.
GPU_RESOURCE_NAMES = ('nvidia.com/gpu', 'amd.com/gpu')
# KAI GPU sharing: a pod requesting a fraction of a GPU carries it in this annotation instead of a resource request.
GPU_FRACTION_ANNOTATION = 'gpu-fraction'
PODGROUP_ANNOTATION = 'pod-group-name'

SCHEDULER_TAG_VALUE = 'kai'

# Badput is tagged with why the PodGroup waits: `reason` holds a value shared with the other schedulers, and
# `scheduler_reason` the raw KAI reason it comes from, when KAI reports one.
REASON_TAG = 'reason'
SCHEDULER_REASON_TAG = 'scheduler_reason'
# Every series is per PodGroup, tagged like the PodGroup lifecycle events.
WORKLOAD_TAG = 'kai_workload'
UNKNOWN_REASON = 'unknown'
KAI_REASONS = {
    'OverLimit': 'quota_exhausted',
    'NonPreemptibleOverQuota': 'quota_exhausted',
    'PodSchedulingErrors': 'no_matching_resources',
    'PreemptionDelayNotElapsed': 'waiting_for_preemption',
    'QueueDoesNotExist': 'misconfigured',
}
# Reasons the check derives itself when KAI reports none. They are normalized but not submitted as KAI reasons.
DERIVED_REASONS = {'PodsPending': 'waiting_for_pods', 'NoPods': 'waiting_for_pods', 'Evicted': 'preempted'}
# `Unknown` means the node stopped reporting the pod, which still holds its GPUs and is not running as far as we know.
ACTIVE_PHASES = ('Pending', 'Running', 'Unknown')
# Seconds an active or suspended owning Job status is reused before it is read again.
OWNER_STATUS_TTL = 60
TERMINAL_PHASES = ('Succeeded', 'Failed')


class SchedulingState(str, Enum):
    WAITING = 'waiting'
    """Not fully runnable: some active pods are pending, or fewer than `minMember` run."""
    PREEMPTED = 'preempted'
    """Evicted after its last start and not fully running again. It waits for GPUs again, so it is badput."""
    RUNNABLE = 'runnable'
    """Every active pod is running, and at least `minMember` of them."""
    INACTIVE = 'inactive'
    """No active pod and the owning Job is suspended: it is held on purpose, not waiting for GPUs."""
    NO_PODS = 'no_pods'
    """No pod at all and no owning batch Job known to recreate them. Nothing says the PodGroup waits for GPUs, so it is
    not counted rather than accruing badput forever, such as a PodGroup left behind by a PyTorchJob."""
    FINISHED = 'finished'
    """No active pod left, and the owning Job completed or failed, or, without a known owner, a pod completed."""


class Category(str, Enum):
    BADPUT = 'badput'
    FULLY_ADMITTED = 'fully_admitted'
    NONE = 'none'


STATE_CATEGORY = {
    SchedulingState.WAITING: Category.BADPUT,
    # As for Kueue, a preempted PodGroup waits for GPUs again: its own state tags that badput with `reason:preempted`.
    SchedulingState.PREEMPTED: Category.BADPUT,
    SchedulingState.RUNNABLE: Category.FULLY_ADMITTED,
    SchedulingState.INACTIVE: Category.NONE,
    SchedulingState.NO_PODS: Category.NONE,
    SchedulingState.FINISHED: Category.NONE,
}


class QueueKey(NamedTuple):
    namespace: str | None
    queue: str | None


class OwnerStatus(NamedTuple):
    """The owning batch Job of a PodGroup, read only for PodGroups without an active pod."""

    finished_at: float | None
    """Unix time the Job completed or failed, or None while it is still active and will create pods again."""
    suspended: bool = False
    """The Job is suspended (`spec.suspend`), so it creates no pods until it is resumed."""


class Observation(NamedTuple):
    name: str
    state: SchedulingState
    gpus: float | None
    """GPUs requested by the active pods, or None without an active pod."""
    queue: QueueKey
    finished_at: float | None
    """Unix time the last pod terminated, once no pod is active: running stops then, even if the Job retries."""
    reason: str | None
    """Raw reason the PodGroup waits, as KAI reports it, or derived by the check (see `DERIVED_REASONS`)."""
    cause: str | None = None
    """Reason normalized across schedulers, submitted as `reason`. Only set for badput states."""
    owner_finished_at: float | None = None
    """Unix time the owner Job completed or failed, which can be later than its last pod, such as when it fails while
    waiting to retry."""


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


def parse_gpu_quantity(value) -> float:
    """Parse a GPU quantity, a count or a KAI GPU fraction. Kubernetes suffixes are rejected instead of guessed."""
    if isinstance(value, bool):
        raise ValueError(f'invalid GPU quantity {value!r}')
    quantity = float(value) if isinstance(value, (int, float)) else float(str(value).strip())
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


def pod_gpus(pod: dict, resource_names: Iterable[str] = GPU_RESOURCE_NAMES) -> float:
    """Return the effective GPU request of one pod, as the kube-scheduler computes it, plus a KAI GPU fraction."""
    resource_names = tuple(resource_names)
    spec = pod.get('spec') or {}
    running = sum(container_gpus(c, resource_names) for c in spec.get('containers') or [])
    init_peak = 0.0
    sidecars = 0.0
    for container in spec.get('initContainers') or []:
        gpus = container_gpus(container, resource_names)
        if container.get('restartPolicy') == 'Always':
            sidecars += gpus
        else:
            init_peak = max(init_peak, sidecars + gpus)
    total = max(running + sidecars, init_peak)
    fraction = ((pod.get('metadata') or {}).get('annotations') or {}).get(GPU_FRACTION_ANNOTATION)
    if fraction:
        total += parse_gpu_quantity(fraction)
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


def is_active(pod: dict) -> bool:
    return (pod.get('status') or {}).get('phase') in ACTIVE_PHASES


def is_running(pod: dict) -> bool:
    # A pod being deleted, such as an evicted one, is on its way out and does not count as running.
    return (pod.get('status') or {}).get('phase') == 'Running' and not (pod.get('metadata') or {}).get(
        'deletionTimestamp'
    )


def pod_finished_at(pod: dict) -> float | None:
    status = pod.get('status') or {}
    # Init containers count too: a pod whose init container failed has no other termination, and a native sidecar
    # can terminate after the app containers.
    finished = [
        t
        for container in [*(status.get('initContainerStatuses') or []), *(status.get('containerStatuses') or [])]
        if (t := parse_timestamp(((container.get('state') or {}).get('terminated') or {}).get('finishedAt')))
        is not None
    ]
    return max(finished) if finished else None


def waiting_reason(podgroup: dict, pods: list[dict]) -> str | None:
    """Return the raw KAI reason a PodGroup waits, or `PodsPending` when KAI scheduled it but pods are not running."""
    for condition in (podgroup.get('status') or {}).get('schedulingConditions') or []:
        if condition.get('type') == UNSCHEDULABLE_CONDITION and condition.get('status') == 'True':
            for explanation in condition.get('reasons') or []:
                if explanation.get('reason'):
                    return explanation['reason']
            return condition.get('reason') or UNSCHEDULABLE_CONDITION
    return 'PodsPending' if pods else 'NoPods'


def classify(podgroup: dict, pods: list[dict], owner: OwnerStatus | None = None) -> tuple[SchedulingState, str | None]:
    """Classify a PodGroup from its pods, and from its owning Job when it has no active pod.

    `owner` is None when the owner is unknown: it is not a batch Job, or it was not or could not be read.
    """
    active = [pod for pod in pods if is_active(pod)]
    if not active:
        if owner is not None and owner.finished_at is not None:
            return SchedulingState.FINISHED, None
        if owner is not None and owner.suspended:
            return SchedulingState.INACTIVE, None
        if owner is None:
            if any((pod.get('status') or {}).get('phase') in TERMINAL_PHASES for pod in pods):
                return SchedulingState.FINISHED, None
            if not pods:
                return SchedulingState.NO_PODS, None
        # Otherwise the Job is still active, so it will create pods again: after an eviction or a failed pod, the
        # PodGroup waits for its replacement.

    running = [pod for pod in active if is_running(pod)]
    succeeded = [pod for pod in pods if (pod.get('status') or {}).get('phase') == 'Succeeded']
    min_member = max(int((podgroup.get('spec') or {}).get('minMember') or 1), 1)
    # Every active pod must run, not only `minMember` of them: a Job whose PodGroup has the default `minMember` of 1
    # would otherwise be fully admitted with one of its pods running and the others pending. Pods that already
    # completed count towards `minMember`, so a gang whose first ranks finished keeps running fully admitted.
    if active and len(running) == len(active) and len(running) + len(succeeded) >= min_member:
        return SchedulingState.RUNNABLE, None

    annotations = (podgroup.get('metadata') or {}).get('annotations') or {}
    last_start = parse_timestamp(annotations.get(LAST_START_ANNOTATION))
    last_eviction = parse_timestamp(annotations.get(LAST_EVICTION_ANNOTATION))
    if last_eviction is not None and (last_start is None or last_eviction >= last_start):
        return SchedulingState.PREEMPTED, 'Evicted'

    return SchedulingState.WAITING, waiting_reason(podgroup, active)


def normalize_reason(state: SchedulingState, reason: str | None) -> str | None:
    """Map the reason of a badput state to a value shared with the other schedulers."""
    if state == SchedulingState.PREEMPTED:
        return 'preempted'
    if state != SchedulingState.WAITING:
        return None
    return KAI_REASONS.get(reason or '') or DERIVED_REASONS.get(reason or '') or UNKNOWN_REASON


def group_pods(pods: Iterable[dict]) -> dict[tuple[str | None, str | None], list[dict]]:
    groups: dict[tuple[str | None, str | None], list[dict]] = defaultdict(list)
    for pod in pods:
        metadata = pod.get('metadata') or {}
        name = (metadata.get('annotations') or {}).get(PODGROUP_ANNOTATION)
        if name:
            groups[(metadata.get('namespace'), name)].append(pod)
    return groups


def observe(podgroup: dict, pods: list[dict], owner: OwnerStatus | None = None) -> Observation:
    metadata = podgroup.get('metadata') or {}
    namespace = metadata.get('namespace')
    state, reason = classify(podgroup, pods, owner)
    active = [pod for pod in pods if is_active(pod)]
    finished_at = None
    if not active:
        finished_at = max((t for t in map(pod_finished_at, pods) if t is not None), default=None)
    owner_finished_at = owner.finished_at if state == SchedulingState.FINISHED and owner is not None else None
    return Observation(
        name=f'{namespace}/{metadata.get("name")}',
        state=state,
        # Only active pods hold GPUs. Without one, such as between a failed attempt and its retry, the request is
        # unknown and the tracker keeps the one of the previous poll, instead of summing every pod that already failed.
        gpus=sum(pod_gpus(pod) for pod in active) if active else None,
        queue=QueueKey(namespace, (podgroup.get('spec') or {}).get('queue')),
        finished_at=finished_at,
        reason=reason,
        cause=normalize_reason(state, reason),
        owner_finished_at=owner_finished_at,
    )


def queue_tags(queue: QueueKey) -> list[str]:
    tags = [f'kube_scheduler:{SCHEDULER_TAG_VALUE}']
    if queue.namespace:
        tags.append(f'kube_namespace:{queue.namespace}')
    if queue.queue:
        tags.append(f'kai_queue:{queue.queue}')
        tags.append(f'kube_scheduler_queue:{queue.queue}')
    return tags


class GoodputTracker:
    """Keep the PodGroup observations of the previous successful poll and compute the contributions of the next one.

    Clocks are injectable for tests: `monotonic` measures the interval, so wall clock changes cannot make it negative,
    and `wall` only places the completion of a PodGroup inside the interval.
    """

    def __init__(
        self, log=None, monotonic: Callable[[], float] = time.monotonic, wall: Callable[[], float] = time.time
    ):
        self.log = log
        self.monotonic = monotonic
        self.wall = wall
        self.previous: dict[str, Observation] | None = None
        self.previous_monotonic: float | None = None
        self.previous_wall: float | None = None
        # PodGroups of the last poll that could not be parsed, which the check reports.
        self.skipped = 0

    def reset(self) -> None:
        """Forget the baseline, so that the next poll does not attribute an interval whose state was not observed."""
        if self.previous is not None:
            self.debug('Scheduling goodput: resetting the baseline of %d PodGroups', len(self.previous))
        self.previous = None
        self.previous_monotonic = None
        self.previous_wall = None

    def update(
        self,
        podgroups: Iterable[dict],
        pods: Iterable[dict],
        owners: Mapping[str, OwnerStatus] | None = None,
        pods_by_group: Mapping[tuple[str | None, str | None], list[dict]] | None = None,
    ) -> list[Contribution]:
        """Record a successful poll and return the contributions of the interval since the previous one.

        `owners` maps PodGroup uids to the status of their owning batch Job, for the PodGroups without an active pod.
        `pods_by_group` can pass `group_pods(pods)` when the caller already computed it.
        """
        owners = owners or {}
        now = self.monotonic()
        now_wall = self.wall()
        if pods_by_group is None:
            pods_by_group = group_pods(pods)

        current: dict[str, Observation] = {}
        self.skipped = 0
        for podgroup in podgroups:
            metadata = podgroup.get('metadata') or {}
            uid = metadata.get('uid')
            if not uid:
                continue
            previous = (self.previous or {}).get(uid)
            try:
                observation = observe(
                    podgroup,
                    pods_by_group.get((metadata.get('namespace'), metadata.get('name')), []),
                    owners.get(uid),
                )
            except Exception as e:
                # Not tracking it means it re-baselines once it can be parsed, instead of contributing a guess.
                self.skipped += 1
                if self.log:
                    self.log.debug(
                        'Scheduling goodput: skipping PodGroup %s/%s: %s',
                        metadata.get('namespace'),
                        metadata.get('name'),
                        e,
                        exc_info=True,
                    )
                continue
            gpus = observation.gpus
            if gpus is None:
                # Pods can be briefly missing, such as between an eviction and the replacement pod: keep the request.
                gpus = previous.gpus if previous is not None and previous.gpus is not None else 0.0
                observation = observation._replace(gpus=gpus)
            if gpus <= 0 and previous is None:
                continue
            # A tracked PodGroup whose active pods need no GPU, such as CPU pods still running after the GPU ones
            # completed, keeps 0 GPUs as its baseline: its last interval uses the GPUs of the previous poll, and the
            # next ones count no GPU time.
            if observation.state == SchedulingState.FINISHED and previous is None:
                # Already finished when first seen: there is no interval to attribute.
                continue
            current[uid] = observation

        contributions = []
        if self.previous is not None and self.previous_monotonic is not None:
            elapsed = now - self.previous_monotonic
            if elapsed <= 0:
                self.debug('Scheduling goodput: non-positive interval %.3fs, skipping it', elapsed)
            else:
                contributions = self.contributions(current, elapsed)

        self.log_transitions(current)
        # Finished PodGroups contributed their last interval and are not tracked any longer. PodGroups that
        # disappeared are dropped without a contribution, as when they were deleted is unknown.
        self.previous = {uid: obs for uid, obs in current.items() if obs.state != SchedulingState.FINISHED}
        self.previous_monotonic = now
        self.previous_wall = now_wall
        return contributions

    def contributions(self, current: dict[str, Observation], elapsed: float) -> list[Contribution]:
        contributions: list[Contribution] = []
        for uid, observation in current.items():
            previous = (self.previous or {}).get(uid)
            if previous is None:
                continue
            category = STATE_CATEGORY[previous.state]
            if category == Category.NONE or not previous.gpus:
                continue
            seconds = elapsed
            if previous.state == SchedulingState.RUNNABLE:
                # Running ends with the last pod, whether the Job then retries or completes: the time the Job
                # controller takes to mark the Job complete is not GPU time.
                cutoff = observation.finished_at
                if cutoff is None:
                    cutoff = observation.owner_finished_at
            elif observation.state == SchedulingState.FINISHED:
                # A wait, such as for a retry, lasts until the Job gives up, which can be after its last pod.
                times = [t for t in (observation.finished_at, observation.owner_finished_at) if t is not None]
                cutoff = max(times) if times else None
            else:
                cutoff = None
            if cutoff is not None and self.previous_wall is not None:
                seconds = min(max(cutoff - self.previous_wall, 0.0), elapsed)
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
        for uid, observation in current.items():
            previous = (self.previous or {}).get(uid)
            if previous is None or previous.state != observation.state:
                self.debug(
                    'Scheduling goodput: PodGroup %s (%g GPUs, queue %s) %s -> %s (reason: %s, scheduler_reason: %s)',
                    observation.name,
                    observation.gpus,
                    observation.queue.queue,
                    previous.state.value if previous else 'new',
                    observation.state.value,
                    observation.cause,
                    observation.reason,
                )

    def debug(self, *args) -> None:
        if self.log:
            self.log.debug(*args)


def aggregate(contributions: Iterable[Contribution]) -> dict[QueueKey, QueueTotals]:
    """Sum contributions per queue, for the debug logs and tests: the metrics are submitted per workload, and queries
    sum them. Each queue gets both totals, so the goodput ratio is 0 rather than missing when
    all of its PodGroups wait."""
    sums: dict[QueueKey, dict[Category, float]] = defaultdict(lambda: defaultdict(float))
    for contribution in contributions:
        sums[contribution.queue][contribution.category] += contribution.gpu_seconds
    return {
        queue: QueueTotals(totals[Category.BADPUT], totals[Category.FULLY_ADMITTED]) for queue, totals in sums.items()
    }


def badput_by_reason(contributions: Iterable[Contribution]) -> dict[QueueKey, dict[tuple[str, str | None], float]]:
    """Sum the badput GPU-seconds per queue and (normalized reason, raw KAI reason), for the debug logs."""
    sums: dict[QueueKey, dict[tuple[str, str | None], float]] = defaultdict(lambda: defaultdict(float))
    for contribution in contributions:
        if contribution.category == Category.BADPUT:
            # Reasons the check derived itself are not KAI reasons, so only the normalized one is kept.
            raw = None if contribution.reason in DERIVED_REASONS else contribution.reason
            sums[contribution.queue][(contribution.cause or UNKNOWN_REASON, raw)] += contribution.gpu_seconds
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
            points.append(
                (
                    BADPUT_METRIC,
                    hours,
                    [
                        *tags,
                        *reason_tags(reason, None if contribution.reason in DERIVED_REASONS else contribution.reason),
                    ],
                )
            )
            points.append((FULLY_ADMITTED_METRIC, 0.0, tags))
        else:
            points.append((FULLY_ADMITTED_METRIC, hours, tags))
            points.append((BADPUT_METRIC, 0.0, tags))
    return points


def workload_name(name: str) -> str:
    """Return the workload name of an observation name, which is `<namespace>/<name>`."""
    return name.split('/', 1)[-1]


class GoodputCollector:
    """Poll KAI PodGroups and their pods, and submit the scheduling goodput metrics per PodGroup.

    Every enabled instance counts the whole cluster, so only one instance must enable it.
    """

    def __init__(self, check: AgentCheck, kube_config_dict: Mapping[str, Any] | None, scheduler_name: str):
        self.check = check
        self.kube_config_dict = kube_config_dict
        self.scheduler_name = scheduler_name
        self.tracker = GoodputTracker(log=check.log)
        self.job_lookups_failing = False
        self.api_failing = False
        self.skipping = False
        # Owning Job statuses by PodGroup uid, with the monotonic time they were read: a finished Job is read once,
        # an active or suspended one at most every `OWNER_STATUS_TTL` seconds.
        self.owner_cache: dict[str, tuple[OwnerStatus, float]] = {}

    @cached_property
    def kube_client(self) -> KubernetesAPIClient:
        return KubernetesAPIClient(self.kube_config_dict)

    def collect(self) -> None:
        try:
            podgroups = self.kube_client.list_podgroups()
            pods = self.kube_client.list_pods(field_selector=f'spec.schedulerName={self.scheduler_name}')
        except Exception as e:
            # Without a complete poll the next interval cannot be attributed, so it starts a new baseline. Only the
            # first failure of a streak warns, such as while `list` on pods is not granted.
            self.tracker.reset()
            log = self.check.log.debug if self.api_failing else self.check.log.warning
            log('Cannot collect KAI scheduling goodput from the Kubernetes API: %s', e)
            self.api_failing = True
            return
        self.api_failing = False

        pods_by_group = group_pods(pods)
        owners = self.owner_statuses(podgroups, pods_by_group)
        contributions = self.tracker.update(podgroups, pods, owners, pods_by_group=pods_by_group)
        if self.tracker.skipped and not self.skipping:
            self.check.log.warning(
                'Scheduling goodput: %d KAI PodGroups could not be parsed and are not counted; enable debug logs for '
                'details',
                self.tracker.skipped,
            )
        self.skipping = bool(self.tracker.skipped)
        # Instance tags stay off, as on events: they include the tags Autodiscovery copies from the scraped KAI pods,
        # such as their `kube_namespace`, which would collide with the tags of the PodGroup.
        for metric, value, tags in workload_points(contributions):
            self.check.count(metric, value, tags=tags, raw=True)

        if not self.check.log.isEnabledFor(logging.DEBUG):
            return
        reasons = badput_by_reason(contributions)
        for queue, queue_totals in aggregate(contributions).items():
            queue_reasons = reasons.get(queue) or {}
            self.check.log.debug(
                'Scheduling goodput for %s: badput=%.1f GPU-s, fully_admitted=%.1f GPU-s, goodput=%s, '
                'badput by reason=%s',
                queue,
                queue_totals.badput,
                queue_totals.fully_admitted,
                queue_totals.goodput,
                {f'{r}/{sr}': round(v, 1) for (r, sr), v in queue_reasons.items()},
            )

    def owner_statuses(
        self, podgroups: list[dict], pods_by_group: Mapping[tuple[str | None, str | None], list[dict]]
    ) -> dict[str, OwnerStatus]:
        """Return the status of the owning batch Job of the tracked PodGroups without an active pod, by uid.

        Only those PodGroups need it, to tell a Job that will create pods again from one that is done, so a cluster
        normally makes no extra request. A finished Job is read once, and an active or suspended one at most every
        `OWNER_STATUS_TTL` seconds, so that many PodGroups waiting for a retry do not read their Job on every run.
        PodGroups owned by something else than a batch Job are not looked up, and are treated as having an unknown
        owner.
        """
        tracked = self.tracker.previous or {}
        now = self.tracker.monotonic()
        owners: dict[str, OwnerStatus] = {}
        present = set()
        failures = 0
        for podgroup in podgroups:
            metadata = podgroup.get('metadata') or {}
            namespace, uid = metadata.get('namespace'), metadata.get('uid')
            if not namespace or not uid:
                continue
            present.add(uid)
            if uid not in tracked:
                continue
            if any(is_active(pod) for pod in pods_by_group.get((namespace, metadata.get('name')), [])):
                # A status read before these pods ran says nothing about how the Job ended once they stop.
                self.owner_cache.pop(uid, None)
                continue
            cached = self.owner_cache.get(uid)
            if cached and (cached[0].finished_at is not None or now - cached[1] < OWNER_STATUS_TTL):
                owners[uid] = cached[0]
                continue
            job_name = owner_job_name(metadata)
            if not job_name:
                continue
            try:
                job = self.kube_client.read_job(namespace, job_name)
            except Exception as e:
                failures += 1
                self.check.log.debug('Scheduling goodput: cannot read Job %s/%s: %s', namespace, job_name, e)
                continue
            owners[uid] = job_status(job, self.tracker.wall)
            if tracked[uid].state != SchedulingState.RUNNABLE:
                # Right after its pods stop, the Job controller may not have marked the Job finished yet, so that
                # first read is not reused: the next poll reads the Job again.
                self.owner_cache[uid] = (owners[uid], now)
        if failures and not self.job_lookups_failing:
            # Those PodGroups are treated as having an unknown owner, so they stop counting rather than guessing. Only
            # the first poll of a streak warns, such as while `get` on `jobs` is not granted.
            self.check.log.warning(
                'Scheduling goodput: cannot read the owning Job of %d KAI PodGroups without pods', failures
            )
        self.job_lookups_failing = bool(failures)
        self.owner_cache = {uid: entry for uid, entry in self.owner_cache.items() if uid in present}
        return owners


def owner_job_name(metadata: dict) -> str | None:
    for ref in metadata.get('ownerReferences') or []:
        if ref.get('kind') == 'Job' and str(ref.get('apiVersion', '')).startswith('batch/') and ref.get('name'):
            return ref['name']
    return None


def job_status(job: dict | None, wall: Callable[[], float]) -> OwnerStatus:
    """Return whether a batch Job completed or failed, and when. A deleted Job will never recreate pods."""
    if job is None:
        return OwnerStatus(finished_at=wall())
    for condition in (job.get('status') or {}).get('conditions') or []:
        if condition.get('type') in ('Complete', 'Failed') and condition.get('status') == 'True':
            return OwnerStatus(finished_at=parse_timestamp(condition.get('lastTransitionTime')) or wall())
    return OwnerStatus(finished_at=None, suspended=bool((job.get('spec') or {}).get('suspend')))
