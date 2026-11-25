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

import re
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

# Badput is tagged with why the Workload waits: `reason` holds one of the general
# categories shared with the other schedulers, and `scheduler_reason` the raw Kueue reason it comes from.
REASON_TAG = 'reason'
SCHEDULER_REASON_TAG = 'scheduler_reason'
# Every series is per workload, tagged like the Workload lifecycle events.
WORKLOAD_TAG = 'kueue_workload'
# Scheduler tags shared by all batch schedulers, as on the Workload events and the pods the Agent tags.
SCHEDULER_TAG = 'job_scheduler'
SCHEDULER_QUEUE_TAG = 'job_scheduler_queue'
SCHEDULER_WORKLOAD_TAG = 'job_scheduler_workload'
# The GPU model, as the Agent tags it on GPU metrics and on pods that Kueue admitted on a GPU flavor.
GPU_TYPE_TAG = 'gpu_type'
# Node label that carries the GPU model, which a Workload can require in the `nodeSelector` or `nodeAffinity` of its
# pods, and a ResourceFlavor in its node labels.
GPU_PRODUCT_LABELS = ('nvidia.com/gpu.product',)

# Badput `reason` values: general categories shared with the other schedulers, whatever the scheduler calls the cause.
QUOTA_OR_CAPACITY = 'quota_or_capacity'
PLACEMENT_OR_TOPOLOGY = 'placement_or_topology'
CONFIGURATION_OR_REQUEST = 'configuration_or_request'
PREEMPTION_OR_RECLAIM = 'preemption_or_reclaim'
STARTUP_OR_SYSTEM = 'startup_or_system'
OTHER_OR_UNKNOWN = 'other_or_unknown'

# The only place that maps Kueue to the categories. Most `QuotaReserved` reasons need the
# `UnadmittedWorkloadsObservability` feature gate; without it Kueue reports `Pending` or `Inadmissible`, and the cause
# is only in the message (`KUEUE_MESSAGE_CATEGORIES`). A reason that is not listed is `other_or_unknown`.
# A Workload evicted by preemption is the `PREEMPTED` state and always `preemption_or_reclaim`.
KUEUE_REASON_CATEGORIES = {
    # Reasons of the design doc.
    'WaitingForQuota': QUOTA_OR_CAPACITY,
    'ExceedsMaxQuota': QUOTA_OR_CAPACITY,
    'NoMatchingFlavor': PLACEMENT_OR_TOPOLOGY,
    'TopologyPlacementFailed': PLACEMENT_OR_TOPOLOGY,
    'WaitingForPreemptedWorkloads': PREEMPTION_OR_RECLAIM,
    'Misconfigured': CONFIGURATION_OR_REQUEST,
    'WaitingForPodsReady': STARTUP_OR_SYSTEM,
    'PendingEvaluation': OTHER_OR_UNKNOWN,
    'Suspended': OTHER_OR_UNKNOWN,
    'DRAResourcesUnresolved': OTHER_OR_UNKNOWN,
    'UnrecordableResourceUsage': OTHER_OR_UNKNOWN,
    # Reasons the check derives itself, closest category. Admission checks are controllers outside Kueue (capacity
    # provisioning, multi-cluster dispatch) that the Workload waits for: system, not a quota decision.
    'UnsatisfiedAdmissionChecks': STARTUP_OR_SYSTEM,
    'UnsatisfiedChecks': STARTUP_OR_SYSTEM,
    'NoReservationUnsatisfiedChecks': STARTUP_OR_SYSTEM,
    'AdmissionCheck': STARTUP_OR_SYSTEM,
    # Admitted, but the pods are not all ready yet, or were not ready in time.
    'WaitForStart': STARTUP_OR_SYSTEM,
    'PodsReadyTimeout': STARTUP_OR_SYSTEM,
    # A stopped queue is an administrator decision on the queue configuration.
    'ClusterQueueStopped': CONFIGURATION_OR_REQUEST,
    'LocalQueueStopped': CONFIGURATION_OR_REQUEST,
}
# Message fragments Kueue writes for `Pending` and `Inadmissible`, checked in order.
KUEUE_MESSAGE_CATEGORIES = (
    ('maximum capacity', QUOTA_OR_CAPACITY),
    ('insufficient unused quota', QUOTA_OR_CAPACITY),
    ('insufficient quota', QUOTA_OR_CAPACITY),
    ('waiting for workloads to be preempted', PREEMPTION_OR_RECLAIM),
    ("couldn't assign flavors", PLACEMENT_OR_TOPOLOGY),
    ("doesn't exist", CONFIGURATION_OR_REQUEST),
    ('is inactive', CONFIGURATION_OR_REQUEST),
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
    """No `PodsReady` condition. Kueue sets it on every Workload, pending ones included, only when `waitForPodsReady`
    is enabled."""
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
    # `reason:preemption_or_reclaim`, `scheduler_reason` telling `Preempted` from the other evictions.
    SchedulingState.PREEMPTED: Category.BADPUT,
    SchedulingState.RUNNABLE: Category.FULLY_ADMITTED,
    # Kueue also reports it while the pods of a completing Workload terminate, which is not a wait.
    SchedulingState.RECOVERING: Category.NONE,
    # Without `waitForPodsReady`, Kueue never reports when the pods are ready, so the Workload is not tracked: see
    # `GoodputTracker.update`.
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
    """General category of the reason, shared across schedulers, submitted as `reason`. Only set for badput states."""
    gpu_type: str | None = None
    """Normalized GPU model, submitted as `gpu_type`, or None when it is not known."""


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
    gpu_type: str | None = None

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

    pods_ready = conditions.get('PodsReady')
    # Kueue sets `PodsReady` on every Workload, from before its admission until after it finishes, only when
    # `waitForPodsReady` is enabled. Checking it per Workload, rather than once for the cluster, also leaves out the
    # Workloads created after it was disabled, while the older ones keep their condition.
    if pods_ready is None:
        return SchedulingState.READINESS_UNKNOWN

    # An evicted Workload is not fully runnable, even while `Admitted` and `PodsReady` are still True for a moment.
    # Kueue sets `Evicted=False` once it admits the Workload again.
    evicted = conditions.get('Evicted')
    if is_true(evicted):
        if evicted.get('reason') == 'Preempted' or is_true(conditions.get('Preempted')):
            return SchedulingState.PREEMPTED
        return SchedulingState.WAITING

    admitted = is_true(conditions.get('Admitted'))
    # `PodsReady` can stay True for a moment after the admission is removed, so it is only trusted together with
    # `Admitted`.
    if admitted and is_true(pods_ready):
        return SchedulingState.RUNNABLE

    if admitted and pods_ready.get('reason') == 'WaitForRecovery':
        return SchedulingState.RECOVERING

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
    """Map the blocking condition of a badput state to one of the general categories."""
    if state == SchedulingState.PREEMPTED:
        return PREEMPTION_OR_RECLAIM
    if state != SchedulingState.WAITING:
        return None
    if not condition:
        return OTHER_OR_UNKNOWN
    reason = condition.get('reason') or ''
    if reason in KUEUE_REASON_CATEGORIES:
        return KUEUE_REASON_CATEGORIES[reason]
    message = (condition.get('message') or '').lower()
    for fragment, normalized in KUEUE_MESSAGE_CATEGORIES:
        if fragment in message:
            return normalized
    return OTHER_OR_UNKNOWN


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


GPU_TYPE_PATTERN = re.compile(r'^(?:nvidia|tesla)_(?:geforce_)?(rtx_pro_|rtx_)?([a-z\d]+)')
AMD_GPU_TYPE_PATTERN = re.compile(r'^amd_(?:radeon_)?instinct_([a-z]+\d+[a-z]*)')
GPU_TYPE_VARIANTS = {'a10g': 'a10', 'l40s': 'l40'}


def extract_gpu_type(device_name: str | None) -> str | None:
    """Return the normalized GPU model of a device name or `nvidia.com/gpu.product` label value, such as `a100` for
    `NVIDIA-A100-SXM4-80GB`. It follows the Agent, so that the values match the `gpu_type` tag of its GPU metrics."""
    if not device_name:
        return None
    name = re.sub(r'[^a-z\d]+', '_', device_name.strip().lower()).strip('_')
    if match := GPU_TYPE_PATTERN.match(name):
        gpu_type = (match.group(1) or '') + match.group(2)
        return GPU_TYPE_VARIANTS.get(gpu_type, gpu_type)
    if match := AMD_GPU_TYPE_PATTERN.match(name):
        return match.group(1)
    return None


def _single(types: Iterable[str | None]) -> str | None:
    """Return the only type of a collection, or None when it is empty, has an unknown value, or is ambiguous."""
    types = list(types)
    return types[0] if types and None not in types and len(set(types)) == 1 else None


def pod_gpu_type(pod_spec: dict) -> str | None:
    """Return the GPU model that a pod explicitly requires, or None.

    It comes from a `nodeSelector`, or from a `nodeAffinity` whose terms all require a single GPU model with `In`. A
    pod that does not constrain the model, or that allows several, has no type: it is not guessed.
    """
    selector = pod_spec.get('nodeSelector') or {}
    for label in GPU_PRODUCT_LABELS:
        if label in selector:
            return extract_gpu_type(str(selector[label]))
    required = (
        ((pod_spec.get('affinity') or {}).get('nodeAffinity') or {}).get(
            'requiredDuringSchedulingIgnoredDuringExecution'
        )
    ) or {}
    # Terms are alternatives, so each one must require the same single model.
    term_types = []
    for term in required.get('nodeSelectorTerms') or []:
        values = [
            expression.get('values') or []
            for expression in term.get('matchExpressions') or []
            if expression.get('key') in GPU_PRODUCT_LABELS and expression.get('operator') == 'In'
        ]
        term_types.append(_single(extract_gpu_type(value) for value in values[0]) if values else None)
    return _single(term_types)


def requested_gpu_type(workload: dict) -> str | None:
    """Return the GPU model that the GPU PodSets of a Workload explicitly require, or None."""
    types = []
    for pod_set in (workload.get('spec') or {}).get('podSets') or []:
        pod_spec = (pod_set.get('template') or {}).get('spec') or {}
        if pod_gpus(pod_spec, GPU_RESOURCE_NAMES) > 0:
            types.append(pod_gpu_type(pod_spec))
    return _single(types)


def parse_timestamp(value: str | None) -> float | None:
    if not value:
        return None
    if value.endswith('Z'):
        value = f'{value[:-1]}+00:00'
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def observe(
    workload: dict,
    cluster_queue_resolver: Callable[[str, str], str | None] | None = None,
    gpu_type_resolver: Callable[[str, str], str | None] | None = None,
) -> Observation:
    metadata = workload.get('metadata') or {}
    spec = workload.get('spec') or {}
    namespace = metadata.get('namespace')
    local_queue = spec.get('queueName')
    cluster_queue = ((workload.get('status') or {}).get('admission') or {}).get('clusterQueue')
    if not cluster_queue and cluster_queue_resolver and namespace and local_queue:
        # Unadmitted Workloads have no admission, so their ClusterQueue comes from their LocalQueue.
        cluster_queue = cluster_queue_resolver(namespace, local_queue)

    # Once Kueue assigned a flavor, the Agent knows the GPU model from the flavor's node labels. Before that, the only
    # source is what the Workload explicitly requires.
    gpu_type = None
    if gpu_type_resolver and namespace and metadata.get('name') and (workload.get('status') or {}).get('admission'):
        gpu_type = gpu_type_resolver(namespace, metadata['name'])
    gpu_type = gpu_type or requested_gpu_type(workload)

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
        gpu_type=gpu_type,
    )


def queue_tags(queue: QueueKey) -> list[str]:
    tags = [f'{SCHEDULER_TAG}:{SCHEDULER_TAG_VALUE}']
    if queue.namespace:
        tags.append(f'kube_namespace:{queue.namespace}')
    if queue.local_queue:
        tags.append(f'kueue_local_queue:{queue.local_queue}')
    if queue.cluster_queue:
        tags.append(f'kueue_cluster_queue:{queue.cluster_queue}')
        tags.append(f'{SCHEDULER_QUEUE_TAG}:{queue.cluster_queue}')
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
        # Consecutive polls that saw GPU Workloads without `PodsReady`, which are not counted.
        self.readiness_unknown_polls = 0
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
        gpu_type_resolver: Callable[[str, str], str | None] | None = None,
    ) -> list[Contribution]:
        """Record a successful poll and return the contributions of the interval since the previous one."""
        now = self.monotonic()
        now_wall = self.wall()

        current: dict[str, Observation] = {}
        self.skipped = 0
        readiness_unknown = 0
        for workload in workloads:
            metadata = workload.get('metadata') or {}
            uid = metadata.get('uid')
            if not uid:
                continue
            try:
                observation = observe(workload, cluster_queue_resolver, gpu_type_resolver)
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
            if observation.gpu_type is None and previous is not None and previous.gpu_type:
                # Keep the GPU model once known, so that the series of a Workload do not change when the tagger
                # briefly cannot resolve it.
                observation = observation._replace(gpu_type=previous.gpu_type)
            if observation.state == SchedulingState.READINESS_UNKNOWN and previous is None:
                # Without `PodsReady`, the time the Workload runs cannot be told apart from its waits: counting only
                # the waits would report a goodput of 0, however short the Workload is. Kueue sets no condition at all
                # on a Workload it did not reconcile yet.
                if observation.gpus > 0 and (workload.get('status') or {}).get('conditions'):
                    readiness_unknown += 1
                continue
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
        self.warn_readiness_unknown(readiness_unknown)
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
                    gpu_type=previous.gpu_type,
                )
            )
        return contributions

    def log_transitions(self, current: dict[str, Observation]) -> None:
        for uid, observation in current.items():
            previous = (self.previous or {}).get(uid)
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

    def warn_readiness_unknown(self, readiness_unknown: int) -> None:
        # Kueue may not have set `PodsReady` yet on a Workload it just reconciled, so only a lasting gap warns.
        self.readiness_unknown_polls = self.readiness_unknown_polls + 1 if readiness_unknown else 0
        if self.readiness_unknown_polls >= 2 and not self.warned_readiness_unknown and self.log:
            self.warned_readiness_unknown = True
            self.log.warning(
                'Scheduling goodput: %d GPU Workloads have no PodsReady condition, so their fully admitted time cannot '
                'be measured and they are not counted. Enable waitForPodsReady in the Kueue configuration.',
                readiness_unknown,
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
            sums[contribution.queue][(contribution.cause or OTHER_OR_UNKNOWN, contribution.reason)] += (
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
        name = workload_name(contribution.name)
        tags = [*queue_tags(contribution.queue), f'{WORKLOAD_TAG}:{name}', f'{SCHEDULER_WORKLOAD_TAG}:{name}']
        if contribution.gpu_type:
            tags.append(f'{GPU_TYPE_TAG}:{contribution.gpu_type}')
        hours = contribution.gpu_seconds / SECONDS_PER_HOUR
        if contribution.category == Category.BADPUT:
            reason = contribution.cause or OTHER_OR_UNKNOWN
            points.append((BADPUT_METRIC, hours, [*tags, *reason_tags(reason, contribution.reason)]))
            points.append((FULLY_ADMITTED_METRIC, 0.0, tags))
        else:
            points.append((FULLY_ADMITTED_METRIC, hours, tags))
            points.append((BADPUT_METRIC, 0.0, tags))
    return points


def workload_name(name: str) -> str:
    """Return the workload name of an observation name, which is `<namespace>/<name>`."""
    return name.split('/', 1)[-1]
