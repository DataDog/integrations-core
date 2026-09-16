# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Deadline-aware scheduling for expensive per-database metric collectors.

The scheduler maintains these invariants:

* I1: each task has at most one pending occurrence and runs at most once per window.
* I2: state is bounded by the number of collector/database tasks; missed windows do not queue work.
* I3: windows are anchored to epoch time and a stable phase, never to completion time.
* I4: an intentional idle never exceeds the estimated demand-bound headroom.
* I5: the demand scan includes pending work and near-term releases across collector periods.
* I6: non-positive slack produces no intentional idle, keeping an overloaded worker busy.
* I7: after release, pending work has no additional eligibility gate.

This is a best-effort load-smoothing policy, not a schedulability proof. Runtime estimates are not
proven upper bounds, the demand scan is finite, and SQL queries cannot be preempted. Non-negative
slack therefore means that the scanned deadlines have estimated aggregate headroom; it does not
guarantee that every task will finish on time. The ``slack / pending`` split uses that headroom to
smooth load and collapses to no intentional idle when the worker falls behind.
"""

from __future__ import annotations

import collections
import dataclasses
import math
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datadog_checks.base.utils.db.core import QueryExecutor
    from datadog_checks.sqlserver.database_metrics.base import SqlserverDatabaseMetricsBase


# These are operational starting points, not values derived from theory or production measurements.
# A one-second cold start permits smoothing in the first window; the rolling maximum adapts after
# one run. Four samples retain a spike for three later runs, while the 25% factor absorbs ordinary
# jitter. The duration floor prevents zero-cost observations from hiding real scheduling overhead.
COLD_START_ESTIMATE_S = 1.0
MIN_ESTIMATE_S = 0.05
ESTIMATE_SAMPLES = 4
ESTIMATE_SAFETY_FACTOR = 1.25

# Reserve part of each window for estimation error and scheduler/driver overhead. Ten percent is a
# conservative starting point; the clamps keep it meaningful for short periods without surrendering
# more than 30 seconds of long ones.
MARGIN_FRACTION = 0.1
MARGIN_MIN_S = 1.0
MARGIN_MAX_S = 30.0

# Two longest-period spans include the current and next deadline of every group. The usual three
# equal-period collectors produce at most six candidates; 32 leaves room for heterogeneous periods
# while bounding decision cost for extreme configurations. This bounded lookahead is one reason
# slack is advisory rather than a feasibility guarantee.
DEMAND_HORIZON_FACTOR = 2
MAX_DEADLINE_CANDIDATES = 32

DEFAULT_PERIOD_S = 300.0  # Matches the heavy-collector configuration default for invalid input.
TIE_EPSILON = 1e-9  # Treat insignificant floating-point deadline differences as ties.
# Three collectors across 1,000 databases fit with headroom; older retired estimates are relearned.
RETIRED_ESTIMATE_LIMIT = 4096


class DurationEstimate:
    """Conservative per-task runtime estimate based on recent observations."""

    def __init__(self, cap: float | None) -> None:
        self._samples: collections.deque[float] = collections.deque(maxlen=ESTIMATE_SAMPLES)
        self._cap = max(float(cap), MIN_ESTIMATE_S) if cap is not None else None

    def observe(self, duration: float) -> None:
        self._samples.append(max(float(duration), MIN_ESTIMATE_S))

    def set_cap(self, cap: float | None) -> None:
        self._cap = max(float(cap), MIN_ESTIMATE_S) if cap is not None else None

    @property
    def observed(self) -> bool:
        return bool(self._samples)

    @property
    def value(self) -> float:
        if not self._samples:
            estimate = COLD_START_ESTIMATE_S
        else:
            estimate = max(self._samples) * ESTIMATE_SAFETY_FACTOR
        return min(estimate, self._cap) if self._cap is not None else estimate


class SchedulerLogger(Protocol):
    def warning(self, message: str, *args: object) -> None: ...


@dataclasses.dataclass
class TaskState:
    """Persistent scheduling state for one collector/database pair."""

    collector: str
    database: str
    estimate: DurationEstimate
    metrics: SqlserverDatabaseMetricsBase | None = None
    executor: QueryExecutor | None = None
    last_completed_window: int | None = None
    has_completed: bool = False
    started_window: int | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.collector, self.database)


@dataclasses.dataclass(frozen=True)
class GroupSpec:
    """Configuration and construction hook for one collector group."""

    name: str
    period: float
    estimate_cap: float | None
    task_factory: Callable[[str, DurationEstimate], TaskState]
    eligible_databases: tuple[str, ...] | None = None


@dataclasses.dataclass
class CollectorGroup:
    name: str
    period: float
    margin: float
    tasks: dict[str, TaskState] = dataclasses.field(default_factory=dict)
    window_index: int | None = None
    pending: collections.deque[str] = dataclasses.field(default_factory=collections.deque)
    served_this_window: int = 0
    missed_last_window: int = 0
    coalesced_windows_last_rollover: int = 0

    def window(self, now: float, phase: float) -> int:
        return math.floor((now - phase % self.period) / self.period)

    def window_start(self, index: int, phase: float) -> float:
        return phase % self.period + index * self.period

    def deadline(self, phase: float) -> float:
        assert self.window_index is not None
        return self.window_start(self.window_index, phase) + self.period

    def effective_deadline(self, phase: float) -> float:
        return self.deadline(phase) - self.margin

    def pending_cost(self) -> float:
        return sum(self.tasks[database].estimate.value for database in self.pending)

    def full_cost(self) -> float:
        return sum(task.estimate.value for task in self.tasks.values())


@dataclasses.dataclass(frozen=True)
class Decision:
    """Intentional idle followed by a task, or an idle until more work is due."""

    task: TaskState | None
    wait: float


@dataclasses.dataclass(frozen=True)
class ReconcileResult:
    added: int = 0
    removed: int = 0
    missed: int = 0
    rolled: tuple[str, ...] = ()

    @property
    def invalidates_selection(self) -> bool:
        """Whether a decision made before this reconciliation must be discarded."""
        return bool(self.added or self.removed or self.rolled)


class HeavyCollectorScheduler:
    """Non-preemptive EDF scheduler with bounded slack-based pacing."""

    def __init__(self, phase: float, max_wait: float, log: SchedulerLogger) -> None:
        self._phase = float(phase)
        self._max_wait = max(float(max_wait), 0.0)
        self._log = log
        self._groups: dict[str, CollectorGroup] = {}
        self._group_order: list[str] = []
        self._retired_estimates: collections.OrderedDict[tuple[str, str], DurationEstimate] = collections.OrderedDict()

    @property
    def groups(self) -> tuple[CollectorGroup, ...]:
        return tuple(self._groups[name] for name in self._group_order)

    def reconcile(self, specs: Sequence[GroupSpec], databases: Sequence[str], now: float) -> ReconcileResult:
        """Reconcile collector definitions, task membership, and wall-clock windows.

        Existing tasks retain their estimates and completion history. New tasks join the current
        window; removed tasks are retired without leaving an occurrence in the pending queue.
        """
        added = removed = missed_total = 0
        rolled = []
        spec_names = [spec.name for spec in specs]

        for name in tuple(self._groups):
            if name not in spec_names:
                group = self._groups.pop(name)
                for task in group.tasks.values():
                    self._retire(task)
                    removed += 1

        self._group_order = spec_names
        desired_databases = tuple(sorted(set(databases)))
        for spec in specs:
            period = self._valid_period(spec)
            margin = min(max(MARGIN_FRACTION * period, MARGIN_MIN_S), MARGIN_MAX_S)
            group = self._groups.get(spec.name)
            if group is None:
                group = CollectorGroup(spec.name, period, margin)
                self._groups[spec.name] = group
            else:
                group.period = period
                group.margin = margin

            group_databases = spec.eligible_databases if spec.eligible_databases is not None else desired_databases
            desired = set(group_databases)
            for database in tuple(group.tasks):
                if database not in desired:
                    task = group.tasks.pop(database)
                    self._retire(task)
                    group.pending = collections.deque(item for item in group.pending if item != database)
                    removed += 1

            new_databases = [database for database in group_databases if database not in group.tasks]
            for database in new_databases:
                key = (spec.name, database)
                estimate = self._retired_estimates.pop(key, None) or DurationEstimate(spec.estimate_cap)
                task = spec.task_factory(database, estimate)
                if task.key != key:
                    raise ValueError("task_factory returned a task with a mismatched key")
                group.tasks[database] = task
                added += 1

            window_changed, missed = self._roll_window(group, now)
            missed_total += missed
            if window_changed:
                rolled.append(group.name)
            if not window_changed:
                group.pending.extend(new_databases)
        return ReconcileResult(added=added, removed=removed, missed=missed_total, rolled=tuple(rolled))

    def decide(self, now: float, allow_idle: bool = True) -> Decision:
        """Choose work and pacing without consuming the occurrence.

        Call :meth:`reconcile` first when time or database membership may have changed. Keeping
        selection read-only lets the caller safely reconsider it after an interruptible wait.
        """
        selected = self._select()
        if selected is None:
            return Decision(None, self.seconds_until_next_release(now))

        group, task = selected
        if allow_idle:
            wait = self.slack(now) / max(self.pending_count(), 1)
            wait = min(wait, self.seconds_until_next_release(now), self._max_wait)
            wait = max(wait, 0.0)
        else:
            wait = 0.0

        return Decision(task, wait)

    def start(self, task: TaskState) -> bool:
        """Consume ``task`` if it is still the selected pending head."""
        group = self._groups.get(task.collector)
        if (
            group is None
            or not group.pending
            or group.pending[0] != task.database
            or group.tasks.get(task.database) is not task
        ):
            return False

        group.pending.popleft()
        group.served_this_window += 1
        assert group.window_index is not None
        task.started_window = group.window_index
        return True

    def record_completion(self, task: TaskState, duration: float) -> None:
        """Record runtime and mark the occurrence consumed by :meth:`start` complete."""
        if task.started_window is None:
            raise RuntimeError("cannot complete a task that has not started")
        task.estimate.observe(duration)
        task.last_completed_window = task.started_window
        task.started_window = None
        task.has_completed = True

    def has_pending(self) -> bool:
        return any(group.pending for group in self.groups)

    def pending_count(self) -> int:
        return sum(len(group.pending) for group in self.groups)

    def seconds_until_next_release(self, now: float) -> float:
        """Return the time until the earliest collector enters its next wall-clock window."""
        releases = []
        for group in self.groups:
            if group.window_index is None:
                continue
            releases.append(group.window_start(group.window_index + 1, self._phase) - now)
        return max(min(releases), 0.0) if releases else 0.0

    def slack(self, now: float) -> float:
        """Return the smallest estimated headroom across upcoming effective deadlines."""
        candidates = self._deadline_candidates(now)
        if not candidates:
            return 0.0
        return min(bound - now - self._demand(bound) for bound in candidates)

    def utilization(self) -> float:
        """Return total serial-worker utilization, ``sum(task cost / collector period)``."""
        return sum(group.full_cost() / group.period for group in self.groups)

    def lateness(self, task: TaskState, now: float) -> float:
        group = self._groups.get(task.collector)
        if group is None or task.last_completed_window is None:
            return 0.0
        deadline = group.window_start(task.last_completed_window, self._phase) + group.period
        return max(now - deadline, 0.0)

    def _valid_period(self, spec: GroupSpec) -> float:
        period = float(spec.period)
        if period > 0:
            return period
        self._log.warning("%s has a non-positive collection interval; using %s seconds", spec.name, DEFAULT_PERIOD_S)
        return DEFAULT_PERIOD_S

    def _roll_window(self, group: CollectorGroup, now: float) -> tuple[bool, int]:
        """Coalesce stale work and release exactly one occurrence per task for the new window."""
        window = group.window(now, self._phase)
        if group.window_index == window:
            return False, 0

        previous_window = group.window_index
        missed = 0
        coalesced_windows = 0
        if previous_window is not None and window > previous_window:
            # Finishing every late sweep would preserve each occurrence but allow unbounded
            # staleness. Coalescing keeps backlog bounded; rotating the replacement window's order
            # distributes overload instead of repeatedly sacrificing the same fixed-order tail.
            # Do not report a miss for a newly discovered task that never had a fair chance to run.
            established_tasks = sum(task.has_completed for task in group.tasks.values())
            missed = sum(group.tasks[database].has_completed for database in group.pending)
            skipped_windows = window - previous_window - 1
            missed += skipped_windows * established_tasks
            if missed:
                coalesced_windows = window - previous_window
        group.missed_last_window = missed
        group.coalesced_windows_last_rollover = coalesced_windows
        group.window_index = window
        group.served_this_window = 0
        order = sorted(group.tasks)
        if order:
            offset = window % len(order)
            order = order[offset:] + order[:offset]
        group.pending = collections.deque(order)
        return True, missed

    def _select(self) -> tuple[CollectorGroup, TaskState] | None:
        """Select by effective deadline, then fair service count and rotating group rank."""
        candidates = [group for group in self.groups if group.pending]
        if not candidates:
            return None
        earliest = min(group.effective_deadline(self._phase) for group in candidates)
        tied = [group for group in candidates if group.effective_deadline(self._phase) <= earliest + TIE_EPSILON]
        tied.sort(key=lambda group: (group.served_this_window, self._collector_rank(group)))
        group = tied[0]
        return group, group.tasks[group.pending[0]]

    def _collector_rank(self, group: CollectorGroup) -> int:
        """Rotate equal-deadline collector priority once per window."""
        size = len(self._group_order)
        if not size:
            return 0
        index = self._group_order.index(group.name)
        rotation = (group.window_index or 0) % size
        return (index - rotation) % size

    def _deadline_candidates(self, now: float) -> list[float]:
        """Return bounded future points at which the demand-bound slack can change."""
        if not self._groups:
            return []
        horizon = now + DEMAND_HORIZON_FACTOR * max(group.period for group in self.groups)
        candidates = set()
        for group in self.groups:
            deadline = group.effective_deadline(self._phase)
            while deadline <= horizon:
                if deadline >= now or group.pending:
                    candidates.add(deadline)
                deadline += group.period
        return sorted(candidates)[:MAX_DEADLINE_CANDIDATES]

    def _demand(self, bound: float) -> float:
        """Estimate pending and future work whose effective deadline is at most ``bound``.

        This is a bounded-horizon adaptation of the processor-demand criterion from Baruah,
        Mok, and Rosier, RTSS 1990, doi:10.1109/REAL.1990.128746. Estimated runtimes and
        non-preemptive execution make it a pacing input, not an exact schedulability test.
        """
        total = 0.0
        for group in self.groups:
            current_deadline = group.effective_deadline(self._phase)
            if current_deadline <= bound + TIE_EPSILON:
                total += group.pending_cost()

            future_deadline = current_deadline + group.period
            if future_deadline <= bound + TIE_EPSILON:
                occurrences = math.floor((bound - future_deadline + TIE_EPSILON) / group.period) + 1
                total += occurrences * group.full_cost()
        return total

    def _retire(self, task: TaskState) -> None:
        """Keep an estimate across transient autodiscovery removal without retaining the task."""
        self._retired_estimates[task.key] = task.estimate
        self._retired_estimates.move_to_end(task.key)
        while len(self._retired_estimates) > RETIRED_ESTIMATE_LIMIT:
            self._retired_estimates.popitem(last=False)
