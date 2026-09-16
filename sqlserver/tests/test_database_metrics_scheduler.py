# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import itertools
import logging
import math
from collections.abc import Mapping, Sequence

import pytest

from datadog_checks.sqlserver.database_metrics.scheduler import (
    ESTIMATE_SAFETY_FACTOR,
    MAX_PACING_WAIT_S,
    CollectorGroup,
    DurationEstimate,
    GroupSpec,
    HeavyCollectorScheduler,
    TaskState,
)

TraceRow = tuple[float, float, str, str]


def make_spec(name: str, period: float, estimates: Mapping[str, float] | None = None) -> GroupSpec:
    estimates = estimates or {}

    def make_task(database: str, estimate: DurationEstimate) -> TaskState:
        if database in estimates:
            estimate.observe(estimates[database] / ESTIMATE_SAFETY_FACTOR)
        return TaskState(name, database, estimate)

    return GroupSpec(name, period, 10_000, make_task)


def make_scheduler(phase: float = 0, max_wait: float = 1_000) -> HeavyCollectorScheduler:
    return HeavyCollectorScheduler(phase, max_wait, logging.getLogger(__name__))


def simulate(
    scheduler: HeavyCollectorScheduler,
    specs: Sequence[GroupSpec],
    databases: Sequence[str],
    durations: Mapping[tuple[str, str], float],
    until: float,
    now: float = 0.0,
) -> tuple[list[TraceRow], int]:
    """Drive the scheduler with a fake clock and return its observable execution trace."""
    trace = []
    misses = 0
    misses += scheduler.reconcile(specs, databases, now).missed
    while now < until:
        decision = scheduler.decide(now)
        now += decision.wait
        if decision.task is None:
            if decision.wait == 0:
                break
            misses += scheduler.reconcile(specs, databases, now).missed
            continue
        if decision.wait:
            result = scheduler.reconcile(specs, databases, now)
            misses += result.missed
            if result.rolled:
                continue
        assert scheduler.start(decision.task)
        start = now
        duration = durations[decision.task.key]
        now += duration
        scheduler.record_completion(decision.task, duration)
        trace.append((start, now, *decision.task.key))
        misses += scheduler.reconcile(specs, databases, now).missed
    return trace, misses


@pytest.mark.unit
@pytest.mark.parametrize('order', itertools.permutations((1.0, 10.0, 1.0)))
def test_pacing_keeps_heterogeneous_work_feasible_for_every_task_order(order: tuple[float, float, float]):
    """Global demand must prevent pacing from making the feasible 1/10/1 workload late."""
    databases = ['a', 'b', 'c']
    durations = {('collector', database): duration for database, duration in zip(databases, order)}
    scheduler = make_scheduler()
    spec = make_spec('collector', 15, dict(zip(databases, order)))

    trace, misses = simulate(scheduler, [spec], databases, durations, until=14)

    assert len(trace) == 3
    assert all(end <= 15 for _, end, _, _ in trace)
    assert any(start > previous_end for (previous_end, (start, *_)) in zip((row[1] for row in trace), trace[1:]))
    assert misses == 0


@pytest.mark.unit
@pytest.mark.parametrize('database_count', [5, 50])
def test_many_databases_are_spread_across_the_window_without_collisions(database_count: int):
    """A low-utilization estate must not collapse back into one packed sweep.

    Runs at the production pacing cap, because a small estate is the case whose per-step wait
    that cap actually clamps.
    """
    databases = [f'db{i:02}' for i in range(database_count)]
    scheduler = make_scheduler(max_wait=MAX_PACING_WAIT_S)
    spec = make_spec('collector', 300)
    durations = {('collector', database): 0.2 for database in databases}

    trace, _ = simulate(scheduler, [spec], databases, durations, until=299)
    starts = [row[0] for row in trace]

    assert len(trace) == database_count
    assert starts[-1] - starts[0] >= 150
    assert all(right - left > 1e-9 for left, right in itertools.pairwise(starts))


@pytest.mark.unit
@pytest.mark.parametrize(('period', 'margin'), [(20.0, 2.0), (100.0, 10.0), (400.0, 30.0)])
@pytest.mark.parametrize('boundary_delta', [0.0, -1e-6])
def test_feasible_boundary_completes_by_the_effective_deadline(period: float, margin: float, boundary_delta: float):
    """Margin arithmetic must not make a workload at the feasible boundary miss."""
    cost = (period - margin + boundary_delta) / 2
    estimates = {'a': cost, 'b': cost}
    scheduler = make_scheduler()
    spec = make_spec('collector', period, estimates)
    durations = {('collector', database): cost for database in estimates}

    trace, misses = simulate(scheduler, [spec], list(estimates), durations, until=period)

    assert len(trace) == 2
    assert trace[-1][1] <= period - margin + 1e-9
    assert misses == 0


@pytest.mark.unit
def test_overload_coalesces_work_and_rotates_coverage():
    """Overload must keep bounded state and rotate service instead of starving the tail."""
    databases = ['a', 'b', 'c', 'd']
    estimates = dict.fromkeys(databases, 5.0)
    scheduler = make_scheduler()
    spec = make_spec('collector', 10, estimates)
    durations = {('collector', database): 5.0 for database in databases}

    trace, misses = simulate(scheduler, [spec], databases, durations, until=100)
    runs_by_window = {}
    for start, _, _, database in trace:
        runs_by_window.setdefault(math.floor(start / 10), []).append(database)

    assert all(len(runs) == len(set(runs)) for runs in runs_by_window.values())
    assert scheduler.pending_count() <= len(databases)
    assert {row[3] for row in trace} == set(databases)
    assert misses > 0


@pytest.mark.unit
def test_runtime_overrun_removes_later_idle_time():
    """An estimate overrun must collapse subsequent gaps instead of spending stale slack."""
    databases = ['a', 'b', 'c']
    estimates = dict.fromkeys(databases, 8.0)
    scheduler = make_scheduler()
    spec = make_spec('collector', 30, estimates)
    durations = {('collector', 'a'): 40.0, ('collector', 'b'): 1.0, ('collector', 'c'): 1.0}

    trace, _ = simulate(scheduler, [spec], databases, durations, until=45)

    assert trace[0][3] == 'a'
    assert trace[1][0] == trace[0][1]
    assert trace[2][0] == trace[1][1]


@pytest.mark.unit
def test_wall_clock_windows_do_not_drift_with_completion_times():
    """Repeated completion must stay epoch-anchored rather than shifting future releases."""
    databases = ['a', 'b', 'c']
    scheduler = make_scheduler()
    spec = make_spec('collector', 10, dict.fromkeys(databases, 1.0))
    durations = {('collector', database): 1.0 for database in databases}

    trace, misses = simulate(scheduler, [spec], databases, durations, until=200)
    runs_by_window = {}
    for start, end, _, database in trace:
        window = math.floor(start / 10)
        assert window * 10 <= start < (window + 1) * 10
        assert end <= (window + 1) * 10
        runs_by_window.setdefault(window, []).append(database)

    assert set(runs_by_window) == set(range(20))
    assert all(sorted(runs) == databases for runs in runs_by_window.values())
    assert misses == 0


@pytest.mark.unit
def test_collectors_keep_independent_periods_and_edf_priority_under_pressure():
    """Heterogeneous intervals must not collapse to one rate or bypass an at-risk EDF head."""
    specs = [make_spec('fast', 60), make_spec('medium', 300), make_spec('slow', 600)]
    durations = {(spec.name, 'db'): 0.1 for spec in specs}
    scheduler = make_scheduler()

    trace, misses = simulate(scheduler, specs, ['db'], durations, until=1_200)
    counts = {spec.name: sum(row[2] == spec.name for row in trace) for spec in specs}

    assert counts == {'fast': 20, 'medium': 4, 'slow': 2}
    assert misses == 0

    overloaded_specs = [
        make_spec('urgent', 10, {'db': 10}),
        make_spec('later', 20, {'db': 10}),
    ]
    pressured = make_scheduler()
    pressured.reconcile(overloaded_specs, ['db'], 0)
    assert pressured.slack(0) <= 0
    assert pressured.decide(0).task.collector == 'urgent'


@pytest.mark.unit
def test_release_during_pacing_wait_is_reselected_before_execution():
    """A newly released short-period task must preempt a stale choice made before the pacing wait."""
    specs = [make_spec('fast', 10, {'db': 1}), make_spec('slow', 100, {'db': 9.5})]
    scheduler = make_scheduler()
    scheduler.reconcile(specs, ['db'], 0)
    fast = scheduler.decide(0, allow_idle=False).task
    assert fast is not None
    assert scheduler.start(fast)
    scheduler.record_completion(fast, 1)
    scheduler.reconcile(specs, ['db'], 1)

    # Just after t=9 the next fast window releases in less than one second. The slow task is still the
    # current choice, but that choice must remain advisory across the wait.
    stale = scheduler.decide(9.1)

    assert stale.task is not None
    assert stale.task.collector == 'slow'
    assert stale.wait == pytest.approx(0.9)
    assert scheduler.pending_count() == 1

    scheduler.reconcile(specs, ['db'], 10)
    replacement = scheduler.decide(10)

    assert replacement.task is not None
    assert replacement.task.collector == 'fast'


@pytest.mark.unit
def test_traces_are_deterministic_and_first_service_rotates():
    """Stable ordering must be reproducible without leaving one database chronically last."""
    databases = ['a', 'b', 'c', 'd']
    spec = make_spec('collector', 10, dict.fromkeys(databases, 1.0))
    durations = {('collector', database): 1.0 for database in databases}

    traces = [simulate(make_scheduler(), [spec], databases, durations, until=40)[0] for _ in range(2)]
    first_by_window = {}
    for row in traces[0]:
        first_by_window.setdefault(math.floor(row[0] / 10), row[3])

    assert traces[0] == traces[1]
    assert set(first_by_window.values()) == set(databases)


@pytest.mark.unit
def test_reconcile_preserves_existing_tasks_when_databases_change():
    """Autodiscovery changes must not rebuild state or make completed tasks run twice."""
    spec = make_spec('collector', 20)
    scheduler = make_scheduler()
    scheduler.reconcile([spec], ['a', 'b'], 0)
    first = scheduler.decide(0, allow_idle=False).task
    assert first is not None
    assert scheduler.start(first)
    scheduler.record_completion(first, 2.0)
    original_tasks = dict(scheduler.groups[0].tasks)

    result = scheduler.reconcile([spec], ['a', 'c'], 3)

    assert result.added == 1
    assert result.removed == 1
    assert scheduler.groups[0].tasks['a'] is original_tasks['a']
    assert scheduler.groups[0].tasks['a'].estimate.observed
    assert scheduler.groups[0].tasks['a'].last_completed_window == 0
    remaining = []
    while scheduler.has_pending():
        task = scheduler.decide(3, allow_idle=False).task
        assert task is not None
        assert scheduler.start(task)
        remaining.append(task.database)
    assert remaining == ['c']


@pytest.mark.unit
def test_cold_start_collects_immediately_and_restart_keeps_epoch_boundaries():
    """Startup must cover the first window without shifting the next wall-clock release."""
    databases = [f'db{i}' for i in range(10)]
    spec = make_spec('collector', 10)
    durations = {('collector', database): 0.1 for database in databases}
    scheduler = make_scheduler()

    trace, _ = simulate(scheduler, [spec], databases, durations, until=20)
    first_window = [row[0] for row in trace if row[0] < 10]
    second_window = [row[0] for row in trace if 10 <= row[0] < 20]
    cold_gaps = [right - left for left, right in itertools.pairwise(first_window)]
    warm_gaps = [right - left for left, right in itertools.pairwise(second_window)]

    assert len(first_window) == len(databases)
    assert min(warm_gaps) > min(cold_gaps)

    restarted = make_scheduler()
    restarted.reconcile([spec], databases, 5)
    assert restarted.groups[0].window_index == 0
    assert restarted.seconds_until_next_release(5) == 5


@pytest.mark.unit
def test_clock_steps_do_not_stall_or_accumulate_occurrences():
    """Window inequality must self-heal after backward and forward wall-clock jumps."""
    spec = make_spec('collector', 10)
    scheduler = make_scheduler()
    scheduler.reconcile([spec], ['db'], 25)
    task = scheduler.decide(25, allow_idle=False).task
    assert task is not None
    assert scheduler.start(task)
    scheduler.record_completion(task, 1)

    scheduler.reconcile([spec], ['db'], 5)
    backward_task = scheduler.decide(5, allow_idle=False).task
    assert backward_task is not None
    assert scheduler.start(backward_task)
    scheduler.record_completion(backward_task, 1)
    forward_result = scheduler.reconcile([spec], ['db'], 35)
    forward_task = scheduler.decide(35, allow_idle=False).task
    assert forward_task is not None
    assert scheduler.start(forward_task)

    assert backward_task.key == task.key == forward_task.key
    assert forward_result.missed == 2
    assert scheduler.pending_count() == 0


@pytest.mark.unit
def test_duration_estimate_rises_immediately_and_decays_after_four_samples():
    """A rolling maximum must protect deadlines without retaining an outlier forever."""
    estimate = DurationEstimate(cap=100)

    assert estimate.value == 1
    estimate.observe(8)
    assert estimate.value == 10
    for _ in range(3):
        estimate.observe(1)
        assert estimate.value == 10
    estimate.observe(1)
    assert estimate.value == 1.25


@pytest.mark.unit
def test_duration_estimate_never_exceeds_its_cap():
    """A command timeout must bound the estimate that every feasibility calculation consumes.

    Without the clamp a single slow observation would inflate pending cost past anything the
    driver can actually allow, suppressing pacing for every task in the group.
    """
    estimate = DurationEstimate(cap=5.0)

    estimate.observe(100.0)

    assert estimate.value == 5.0


@pytest.mark.unit
def test_non_positive_period_uses_safe_default(caplog: pytest.LogCaptureFixture):
    """Invalid user intervals must not cause division-by-zero, stuck scheduling, or log floods."""
    scheduler = make_scheduler()
    spec = make_spec('collector', 0)

    for now in (0, 1, 2):
        scheduler.reconcile([spec], ['db'], now)

    group: CollectorGroup = scheduler.groups[0]
    assert group.period == 300
    # `reconcile` runs after every completed task, so an unlatched warning repeats all day.
    assert caplog.text.count('non-positive collection interval') == 1


@pytest.mark.unit
def test_undiscoverable_database_is_skipped_without_losing_other_work(caplog: pytest.LogCaptureFixture):
    """One database whose collector cannot be built must not cost every other database its metrics.

    An exception escaping `reconcile` reaches the job loop, which stops collection for every
    collector and database, and would do so again on each later pass because the inputs repeat.
    """

    def make_task(database: str, estimate: DurationEstimate) -> TaskState:
        if database == 'broken':
            raise ValueError('cannot resolve database')
        return TaskState('fragile', database, estimate)

    specs = [GroupSpec('fragile', 60, None, make_task), make_spec('healthy', 60)]
    scheduler = make_scheduler()

    result = scheduler.reconcile(specs, ['broken', 'working'], 0)

    assert result.added == 3
    assert sorted(scheduler.groups[0].tasks) == ['working']
    assert [group.name for group in scheduler.groups] == ['fragile', 'healthy']
    assert 'cannot resolve database' in caplog.text

    # The surviving work must stay schedulable, and a later pass must not replay the failure fatally.
    assert scheduler.reconcile(specs, ['broken', 'working'], 1).added == 0
    assert scheduler.pending_count() == 3
