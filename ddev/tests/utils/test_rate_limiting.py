"""Tests for the generic async rate limiting utilities."""

from __future__ import annotations

import asyncio
import inspect
import itertools
from collections.abc import Callable
from typing import Any
from unittest.mock import MagicMock

import pytest
from aiolimiter import AsyncLimiter

from ddev.utils.rate_limiting import (
    MAX_WAIT_ITERATIONS,
    BucketEvent,
    BudgetEvent,
    BudgetGovernor,
    BudgetSnapshot,
    InstrumentedAsyncLimiter,
    PacingEvent,
    PacingReason,
    RateLimitEvent,
    RateLimitWaitAbandoned,
    SecondaryLimitEvent,
)
from tests.helpers.assertions import assert_blocks
from tests.helpers.clock import FakeClock


def make_snapshot(
    *,
    clock: FakeClock | None = None,
    reset_in: float | None = None,
    limit: int | None = None,
    remaining: int | None = None,
    reset_at: float | None = None,
    retry_after: float | None = None,
) -> BudgetSnapshot:
    """Build a BudgetSnapshot from the given fields; reset_in sets reset_at to clock.current + reset_in."""
    fields: dict[str, Any] = {}
    if limit is not None:
        fields["limit"] = limit
    if remaining is not None:
        fields["remaining"] = remaining
    if reset_at is not None:
        fields["reset_at"] = reset_at
    if reset_in is not None:
        assert clock is not None, "clock is required when reset_in is provided"
        fields["reset_at"] = clock.current + reset_in
    if retry_after is not None:
        fields["retry_after"] = retry_after
    return BudgetSnapshot(**fields)


def sleep_advancing(clock: FakeClock) -> tuple[MagicMock, list[float]]:
    """Return a fake asyncio.sleep that advances the fake clock and records each slept amount."""
    slept: list[float] = []

    async def fake_sleep(delay: float) -> None:
        slept.append(delay)
        clock.advance(delay)

    return MagicMock(side_effect=fake_sleep), slept


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def governor(clock: FakeClock) -> BudgetGovernor:
    return BudgetGovernor(now=clock, reserve_fraction=0.15)


@pytest.fixture
def slept(clock: FakeClock, monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Monkeypatch asyncio.sleep to advance the fake clock and return the recorded sleep durations."""
    fake_sleep, slept_durations = sleep_advancing(clock)
    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return slept_durations


async def test_instrumented_limiter_none_callback_does_not_raise() -> None:
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter, on_event=None)

    async with limiter:
        pass  # drain

    # Entering with an exhausted bucket and the callback set to None must not raise.
    await assert_blocks(limiter.__aenter__())


async def test_instrumented_limiter_blocks_on_exhausted_bucket():
    """A second acquire on an empty bucket must block, not pass through."""
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter)

    async with limiter:
        pass  # drain the single token

    await assert_blocks(limiter.__aenter__())


async def test_instrumented_limiter_bucket_event_fires_once_per_acquire() -> None:
    events: list[RateLimitEvent] = []
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), on_event=events.append)

    async with limiter:
        pass

    assert events == [BucketEvent(throttled=False, name="")]


async def test_instrumented_limiter_bucket_event_throttled_after_wait_for_capacity() -> None:
    events: list[RateLimitEvent] = []
    real_limiter = AsyncLimiter(max_rate=1, time_period=0.1)
    limiter = InstrumentedAsyncLimiter(real_limiter, on_event=events.append)

    async with limiter:
        pass  # drain; throttled=False fires once here

    # Bucket is empty — next acquire blocks until the 0.1s period refills it
    async with limiter:
        pass  # throttled=True fires once the wait is over

    bucket_events = [event for event in events if isinstance(event, BucketEvent)]
    assert [event.throttled for event in bucket_events] == [False, True]


# ---------------------------------------------------------------------------
# BudgetGovernor.reserve — pure computation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("snapshot_fields", "advance_seconds"),
    [
        pytest.param(None, 0, id="no_snapshot_observed"),
        pytest.param({"limit": 100, "remaining": 90, "reset_in": 3600}, 0, id="remaining_is_healthy"),
        pytest.param({"limit": 100, "remaining": 0, "reset_in": 10}, 11, id="reset_time_has_passed"),
        pytest.param({"remaining": 10, "reset_in": 50}, 0, id="limit_unknown"),
        pytest.param({"limit": 100, "reset_in": 50}, 0, id="remaining_unknown"),
        pytest.param({"limit": 100, "remaining": 10}, 0, id="reset_at_unknown"),
    ],
)
def test_reserve_returns_now(
    clock: FakeClock, governor: BudgetGovernor, snapshot_fields: dict[str, Any] | None, advance_seconds: int
) -> None:
    if snapshot_fields is not None:
        governor.observe(make_snapshot(clock=clock, **snapshot_fields))
    clock.advance(advance_seconds)

    assert governor.reserve()[0] == pytest.approx(clock.current)


def test_reserve_paces_requests_when_remaining_at_or_below_reserve(clock: FakeClock, governor: BudgetGovernor) -> None:
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10  # (reset_at - now) / remaining

    # Without advancing the clock, successive reservations return targets that increase by
    # exactly one interval each — the pacing cursor advances exactly once per reserve() call.
    first, _ = governor.reserve()
    second, _ = governor.reserve()
    third, _ = governor.reserve()

    assert first == pytest.approx(clock.current)
    assert second - first == pytest.approx(interval)
    assert third - second == pytest.approx(interval)


def test_reserve_clamps_paced_slots_at_window_reset(clock: FakeClock, governor: BudgetGovernor) -> None:
    # Only 2 requests fit in the window; the 3rd and 4th overflow and wait until reset, not beyond.
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=2, reset_in=100))
    interval = 100 / 2
    reset_target = clock.current + 100 + governor.buffer_seconds

    first, first_reason = governor.reserve()
    second, second_reason = governor.reserve()
    third, third_reason = governor.reserve()
    fourth, fourth_reason = governor.reserve()

    assert (first_reason, second_reason) == (PacingReason.RATIONING, PacingReason.RATIONING)
    assert second - first == pytest.approx(interval)
    assert (third_reason, fourth_reason) == (PacingReason.EXHAUSTED, PacingReason.EXHAUSTED)
    # Both overflow requests get the SAME reset target — the cursor must not advance past the clamp.
    assert third == pytest.approx(reset_target)
    assert fourth == pytest.approx(reset_target)


def test_reserve_returns_now_in_new_window_after_clamp(clock: FakeClock, governor: BudgetGovernor) -> None:
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=2, reset_in=100))
    for _ in range(3):
        governor.reserve()  # fill the window and engage the clamp

    clock.advance(101)  # past reset_at: the window has rolled over
    target, reason = governor.reserve()

    assert reason is PacingReason.NONE
    assert target == pytest.approx(clock.current)


def test_reserve_exhausted_budget_targets_reset_plus_buffer(clock: FakeClock) -> None:
    governor = BudgetGovernor(now=clock, buffer_seconds=2.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=50))

    assert governor.reserve()[0] == pytest.approx(clock.current + 52.0)


def test_observe_with_retry_after_sets_hard_pause_and_fires_event(clock: FakeClock) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, on_event=events.append)

    governor.observe(make_snapshot(retry_after=30.0))

    assert governor.reserve()[0] == pytest.approx(clock.current + 31.0)
    secondary_limit_events = [event for event in events if isinstance(event, SecondaryLimitEvent)]
    assert secondary_limit_events == [SecondaryLimitEvent(retry_after_seconds=30.0, pause_seconds=pytest.approx(31.0))]


def test_observe_keeps_longest_retry_after_pause(clock: FakeClock) -> None:
    """A later, shorter retry_after must not shorten an already-committed secondary-limit pause."""
    governor = BudgetGovernor(now=clock, buffer_seconds=0.0)
    governor.observe(make_snapshot(retry_after=60.0))
    long_pause_target, _ = governor.reserve()

    governor.observe(make_snapshot(retry_after=10.0))

    assert governor.reserve()[0] == long_pause_target


def test_reserve_returns_paced_slot_when_it_exceeds_pause_until(clock: FakeClock, governor: BudgetGovernor) -> None:
    """The floor in reserve() must take the larger of the two targets, not the smaller."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10

    first_slot, _ = governor.reserve()  # claims a slot at now, advances the cursor by one interval
    governor.observe(make_snapshot(retry_after=1.0))  # pause_until = now + 1.0, well below the next paced slot
    second_slot, _ = governor.reserve()

    assert first_slot == pytest.approx(clock.current)
    assert second_slot == pytest.approx(clock.current + interval)
    assert governor.pause_until < second_slot


async def test_reserve_assigns_distinct_slots_under_concurrent_claims(
    clock: FakeClock, governor: BudgetGovernor
) -> None:
    """Concurrently reserved slots must be distinct and one interval apart.

    Runs on the real event loop with asyncio.sleep left intact. reserve() must claim its slot
    without yielding. If the claim path is ever made async, this test fails immediately because
    reserve() returns a coroutine and reserve()[0] raises TypeError; once someone updates the test
    to await reserve(), an await between reading and advancing next_slot makes the gathered claims
    interleave, all read the same cursor, and the slot assertion below fails.
    """
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10

    async def claim() -> float:
        return governor.reserve()[0]

    slots = await asyncio.gather(*(claim() for _ in range(4)))

    assert sorted(slots) == [pytest.approx(clock.current + step * interval) for step in range(4)]


def test_pacing_claim_path_is_synchronous() -> None:
    """The pacing read-modify-write of next_slot is race-free under asyncio only because no
    function in the claim path is a coroutine: a plain def cannot contain an await, so a task
    entering reserve() cannot be suspended before it finishes advancing the cursor.

    If this fails, you are converting the claim path to async. That is not forbidden, but it
    removes the structural guarantee: you must then make the read-modify-write in
    claim_paced_slot atomic by other means (e.g. an asyncio.Lock) and update
    test_reserve_assigns_distinct_slots_under_concurrent_claims to await reserve() —
    that test's slot-collision assertion will then verify your replacement mechanism.
    """
    claim_path = (
        BudgetGovernor.reserve,
        BudgetGovernor.claim_budget_target_with_reason,
        BudgetGovernor.claim_paced_slot,
    )
    for fn in claim_path:
        assert not inspect.iscoroutinefunction(fn), f"{fn.__qualname__} must remain synchronous"


@pytest.mark.parametrize(
    ("remaining", "expected_is_low"),
    [
        pytest.param(10, True, id="below_threshold"),
        pytest.param(15, True, id="at_threshold_boundary"),
        pytest.param(50, False, id="above_threshold"),
    ],
)
def test_observe_fires_budget_event_with_is_low(clock: FakeClock, remaining: int, expected_is_low: bool) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, reserve_fraction=0.15, on_event=events.append)

    governor.observe(make_snapshot(clock=clock, limit=100, remaining=remaining, reset_in=40))

    budget_events = [event for event in events if isinstance(event, BudgetEvent)]
    assert len(budget_events) == 1
    last = budget_events[-1]
    assert last.is_low is expected_is_low
    assert last.limit == 100
    assert last.remaining == remaining
    assert last.reset_in_seconds == pytest.approx(40.0)


def test_budget_event_reset_in_seconds_is_none_when_reset_at_unknown(clock: FakeClock) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, reserve_fraction=0.15, on_event=events.append)

    governor.observe(make_snapshot(limit=100, remaining=10))

    budget_events = [event for event in events if isinstance(event, BudgetEvent)]
    assert budget_events[-1].reset_in_seconds is None


def test_budget_event_clamps_reset_in_seconds_to_zero_when_reset_at_in_past(clock: FakeClock) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, reserve_fraction=0.15, on_event=events.append)

    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=-50))

    budget_events = [event for event in events if isinstance(event, BudgetEvent)]
    assert budget_events[-1].reset_in_seconds == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("base_fields", "update_fields", "expected_fields"),
    [
        pytest.param(
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0},
            {"remaining": 4998},
            {"limit": 5000, "remaining": 4998, "reset_at": 1700000000.0},
            id="non_none_update_overwrites",
        ),
        pytest.param(
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0},
            {},
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0},
            id="none_update_keeps_prior",
        ),
    ],
)
def test_merged_with_overlay_rule(
    base_fields: dict[str, Any], update_fields: dict[str, Any], expected_fields: dict[str, Any]
) -> None:
    base = make_snapshot(**base_fields)

    merged = base.merged_with(make_snapshot(**update_fields))

    assert merged == make_snapshot(**expected_fields)


def test_merged_with_keeps_lowest_remaining_within_window() -> None:
    """Within one window (same reset_at) a stale higher remaining must not inflate the value."""
    base = make_snapshot(limit=5000, remaining=4000, reset_at=1700000000.0)

    merged = base.merged_with(make_snapshot(remaining=4999, reset_at=1700000000.0))

    assert merged.remaining == 4000


def test_merged_with_adopts_new_remaining_when_window_advances() -> None:
    """A larger reset_at is a new window, so the reported remaining is adopted as-is."""
    base = make_snapshot(limit=5000, remaining=100, reset_at=1700000000.0)

    merged = base.merged_with(make_snapshot(remaining=4999, reset_at=1700003600.0))

    assert merged.remaining == 4999
    assert merged.reset_at == 1700003600.0


def test_merged_with_discards_stale_window_update() -> None:
    """A smaller reset_at than the known one is a stale, out-of-order response and is discarded."""
    base = make_snapshot(limit=5000, remaining=100, reset_at=1700003600.0)

    merged = base.merged_with(make_snapshot(limit=5000, remaining=4999, reset_at=1700000000.0))

    assert merged == base


def test_observe_honors_retry_after_on_stale_window_snapshot(clock: FakeClock) -> None:
    """retry_after is consumed in observe regardless of the budget merge, even for a stale window."""
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0)
    governor.observe(make_snapshot(clock=clock, limit=5000, remaining=100, reset_in=3600))

    # A stale, out-of-order response for an earlier window: its budget is discarded, but the
    # secondary-limit signal it carries must still arm the pause.
    governor.observe(make_snapshot(clock=clock, remaining=4999, reset_in=0, retry_after=30.0))

    assert governor.budget.remaining == 100
    assert governor.budget.reset_at == clock.current + 3600
    assert governor.pause_until == pytest.approx(clock.current + 30.0 + 1.0)


def test_observe_converges_regardless_of_order(clock: FakeClock) -> None:
    """Observing the same responses in any order yields the same budget and pause (commutative)."""
    snapshots = {
        "window_a": make_snapshot(clock=clock, limit=100, remaining=50, reset_in=100),
        "window_a_lower_remaining": make_snapshot(clock=clock, remaining=10, reset_in=100),
        "window_b": make_snapshot(clock=clock, limit=100, remaining=90, reset_in=200),
        "secondary_limit": make_snapshot(retry_after=30.0),
    }
    # The latest window (b) wins the budget; retry_after is not persisted but arms pause_until.
    expected_budget = make_snapshot(clock=clock, limit=100, remaining=90, reset_in=200)

    for order in itertools.permutations(snapshots.items()):
        governor = BudgetGovernor(now=clock)
        for _, snapshot in order:
            governor.observe(snapshot)
        applied = " -> ".join(name for name, _ in order)
        expected_pause_until = clock.current + 30.0 + governor.buffer_seconds
        assert governor.budget == expected_budget, f"budget diverged for order: {applied}"
        assert governor.pause_until == pytest.approx(expected_pause_until), f"pause diverged for order: {applied}"


def test_none_callback_does_not_raise(clock: FakeClock) -> None:
    governor = BudgetGovernor(now=clock, on_event=None)

    governor.observe(make_snapshot(clock=clock, limit=100, remaining=1, reset_in=10, retry_after=5.0))

    assert governor.reserve()[0] == pytest.approx(clock.current + 5.0 + governor.buffer_seconds)


def test_claim_paced_slot_interval_widens_after_lower_remaining_observed(
    clock: FakeClock, governor: BudgetGovernor
) -> None:
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))

    first, _ = governor.reserve()
    second, _ = governor.reserve()
    interval_before = second - first

    governor.observe(make_snapshot(remaining=5))  # same reset_at, same clock, fewer requests left

    third, _ = governor.reserve()
    fourth, _ = governor.reserve()
    interval_after = fourth - third

    assert interval_after > interval_before


# ---------------------------------------------------------------------------
# BudgetGovernor.wait — async loop
# ---------------------------------------------------------------------------


async def test_wait_returns_immediately_when_no_delay():
    governor = BudgetGovernor(now=FakeClock())
    await asyncio.wait_for(governor.wait(), timeout=0.05)


async def test_wait_low_budget_advances_by_one_interval(
    clock: FakeClock, governor: BudgetGovernor, slept: list[float]
) -> None:
    """Regression: a single low-budget wait() must advance by ~one interval, never diverge."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10
    # Pretend a prior request already reserved the first slot, so this one must actually wait.
    governor.reserve()
    start = clock.current

    await governor.wait()

    assert clock.current - start == pytest.approx(interval)


async def test_two_sequential_paced_waits_are_spaced_by_one_interval(
    clock: FakeClock, governor: BudgetGovernor, slept: list[float]
) -> None:
    """Two sequential paced wait() calls must be ~interval apart, not MAX_WAIT_ITERATIONS*interval."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10

    await governor.wait()  # first request: reserves slot at now, no sleep
    first_finished_at = clock.current
    await governor.wait()  # second request: reserves slot one interval later

    assert clock.current - first_finished_at == pytest.approx(interval)


async def test_wait_extends_when_retry_after_observed_mid_wait(
    clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retry_after pause raised while a request is mid-wait must extend the wait (pause_until floor)."""
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, buffer_seconds=0.0, reserve_fraction=0.15, on_event=events.append)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10
    governor.reserve()  # first request reserved; this wait() must pace by one interval

    injected = False

    async def fake_sleep(delay: float) -> None:
        nonlocal injected
        clock.advance(delay)
        if not injected:
            injected = True
            # A concurrent observe() lands a secondary-limit pause well beyond the paced slot.
            governor.observe(make_snapshot(retry_after=50.0))

    monkeypatch.setattr(asyncio, "sleep", MagicMock(side_effect=fake_sleep))

    start = clock.current
    await governor.wait()

    # Without the floor re-check the wait would end after ~interval; the injected pause pushes it out.
    assert clock.current - start == pytest.approx(interval + 50.0)
    pacing_events = [event for event in events if isinstance(event, PacingEvent)]
    assert pacing_events[-1] == PacingEvent(wait_seconds=pytest.approx(50.0), reason=PacingReason.SECONDARY_LIMIT)


async def test_wait_raises_when_max_iterations_exceeded_without_hanging(
    clock: FakeClock, governor: BudgetGovernor, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A permanently exhausted budget with a sleep that never advances the clock must not hang."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=100))

    async def fake_sleep(delay: float) -> None:
        pass

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    with pytest.raises(RuntimeError, match=str(MAX_WAIT_ITERATIONS)):
        await asyncio.wait_for(governor.wait(), timeout=1.0)


async def test_wait_abandons_immediately_when_exhausted_window_exceeds_budget(
    clock: FakeClock, slept: list[float]
) -> None:
    """A window that resets past the budget must raise before sleeping at all."""
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=300)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=3600))

    with pytest.raises(RateLimitWaitAbandoned) as exc_info:
        await governor.wait()

    assert slept == []
    assert exc_info.value.waited_seconds == pytest.approx(0.0)
    assert exc_info.value.remaining_seconds == pytest.approx(3601.0)


async def test_wait_abandons_when_flood_pushes_floor_past_budget(
    clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A secondary-limit extension that crosses the budget mid-wait must raise, not be slept out."""
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(
        now=clock, buffer_seconds=0.0, reserve_fraction=0.15, max_wait_seconds=60, on_event=events.append
    )
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10
    governor.reserve()  # first request reserved; this wait() paces by one interval

    async def fake_sleep(delay: float) -> None:
        clock.advance(delay)
        # Each sleep lands a fresh secondary-limit pause far beyond the budget.
        governor.observe(make_snapshot(retry_after=100.0))

    monkeypatch.setattr(asyncio, "sleep", MagicMock(side_effect=fake_sleep))

    start = clock.current
    with pytest.raises(RateLimitWaitAbandoned) as exc_info:
        await governor.wait()

    # Only the initial paced interval was slept; the 100s flood extension was never slept out.
    assert clock.current - start == pytest.approx(interval)
    assert exc_info.value.waited_seconds == pytest.approx(interval)
    assert exc_info.value.remaining_seconds == pytest.approx(100.0)
    abandoned = [e for e in events if isinstance(e, PacingEvent) and e.reason is PacingReason.ABANDONED]
    assert abandoned == [PacingEvent(wait_seconds=pytest.approx(100.0), reason=PacingReason.ABANDONED)]


async def test_wait_with_ample_budget_sleeps_identically_to_no_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """A budget larger than the whole wait must not change any sleep versus a disabled budget."""

    def armed_governor(max_wait_seconds: float | None) -> tuple[BudgetGovernor, list[float]]:
        clock = FakeClock()
        governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=max_wait_seconds)
        governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=100))
        fake_sleep, slept = sleep_advancing(clock)
        monkeypatch.setattr(asyncio, "sleep", fake_sleep)
        return governor, slept

    governor_none, slept_none = armed_governor(None)
    await governor_none.wait()

    governor_budget, slept_budget = armed_governor(100_000)
    await governor_budget.wait()

    assert slept_budget == slept_none


async def test_wait_without_budget_does_not_abandon_long_exhausted_wait(clock: FakeClock, slept: list[float]) -> None:
    """With max_wait_seconds=None the governor waits out an entire window without raising."""
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=None)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=3600))
    start = clock.current

    await governor.wait()

    assert clock.current - start == pytest.approx(3601.0)


async def test_wait_abandoned_is_caught_as_timeout_error(clock: FakeClock, slept: list[float]) -> None:
    """RateLimitWaitAbandoned subclasses TimeoutError so generic timeout handling catches it."""
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=1.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=3600))

    with pytest.raises(TimeoutError):
        await governor.wait()


def arm_rationing(clock: FakeClock, governor: BudgetGovernor) -> None:
    """Observe a low budget and consume the first slot so the next wait() must actually pace."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    governor.reserve()


@pytest.mark.parametrize(
    ("arm", "expected_wait_seconds", "expected_reason"),
    [
        pytest.param(None, 0.0, PacingReason.NONE, id="healthy"),
        pytest.param(arm_rationing, 100 / 10, PacingReason.RATIONING, id="rationing"),
        pytest.param(
            lambda clock, governor: governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=50)),
            51.0,
            PacingReason.EXHAUSTED,
            id="exhausted",
        ),
        pytest.param(
            lambda clock, governor: governor.observe(make_snapshot(retry_after=30.0)),
            31.0,
            PacingReason.SECONDARY_LIMIT,
            id="secondary_limit",
        ),
    ],
)
async def test_wait_fires_pacing_event_with_reason(
    clock: FakeClock,
    slept: list[float],
    arm: Callable[[FakeClock, BudgetGovernor], None] | None,
    expected_wait_seconds: float,
    expected_reason: PacingReason,
) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, on_event=events.append)
    if arm is not None:
        arm(clock, governor)

    await governor.wait()

    pacing_events = [event for event in events if isinstance(event, PacingEvent)]
    assert pacing_events == [PacingEvent(wait_seconds=pytest.approx(expected_wait_seconds), reason=expected_reason)]


# ---------------------------------------------------------------------------
# InstrumentedAsyncLimiter + BudgetGovernor wiring
# ---------------------------------------------------------------------------


async def test_instrumented_limiter_calls_governor_wait_on_enter():
    governor = BudgetGovernor(buffer_seconds=0.0)
    governor.observe(make_snapshot(retry_after=0.05))
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), budget_governor=governor)
    start = asyncio.get_running_loop().time()

    await asyncio.wait_for(limiter.__aenter__(), timeout=1.0)

    assert asyncio.get_running_loop().time() - start >= 0.05


async def test_instrumented_limiter_without_governor_does_not_wait():
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000))
    await asyncio.wait_for(limiter.__aenter__(), timeout=0.05)


async def test_instrumented_limiter_does_not_consume_bucket_token_during_governor_wait() -> None:
    """The bucket token must be acquired only after the governor wait, not before it."""
    governor = BudgetGovernor(buffer_seconds=0.0)
    governor.observe(make_snapshot(retry_after=0.05))
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter, budget_governor=governor)

    task = asyncio.create_task(limiter.__aenter__())
    try:
        await asyncio.sleep(0)  # let the task start and enter the governor's pause

        assert real_limiter.has_capacity()  # token untouched while paused

        await asyncio.wait_for(task, timeout=1.0)

        assert not real_limiter.has_capacity()  # token acquired only once the wait is over
    finally:
        task.cancel()


def test_instrumented_limiter_observe_without_governor_does_not_raise():
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000))
    limiter.observe(make_snapshot(limit=100, remaining=50, reset_at=2000.0))
