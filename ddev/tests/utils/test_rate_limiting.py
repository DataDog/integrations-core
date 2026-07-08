"""Tests for the generic async rate limiting utilities."""

from __future__ import annotations

import asyncio
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
    SecondaryLimitEvent,
)
from tests.helpers.assertions import assert_blocks


class FakeClock:
    """Injectable, manually-advanceable clock for deterministic governor tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def make_snapshot(*, clock: FakeClock | None = None, reset_in: float | None = None, **fields: Any) -> BudgetSnapshot:
    """Build a BudgetSnapshot; reset_in (seconds from clock.current) sets reset_at."""
    if reset_in is not None:
        fields["reset_at"] = clock.current + reset_in
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
    if advance_seconds:
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


def test_reserve_caps_pacing_interval_at_max_wait_seconds(clock: FakeClock) -> None:
    # remaining=1 with an hour to reset would pace ~3600s apart; the cap bounds it.
    governor = BudgetGovernor(now=clock, max_wait_seconds=30.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=1, reset_in=3600))

    first, _ = governor.reserve()
    second, _ = governor.reserve()

    assert first == pytest.approx(clock.current)
    assert second - first == pytest.approx(30.0)


def test_reserve_does_not_cap_pacing_interval_below_max_wait_seconds(clock: FakeClock) -> None:
    # True interval (100/10 = 10s) is under the cap, so the cap must not shorten it.
    governor = BudgetGovernor(now=clock, max_wait_seconds=30.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))

    first, _ = governor.reserve()
    second, _ = governor.reserve()

    assert second - first == pytest.approx(10.0)


def test_max_wait_seconds_does_not_cap_exhausted_budget_hard_pause(clock: FakeClock) -> None:
    # The cap bounds voluntary pacing only; an exhausted budget still waits the full reset.
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=30.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=3600))

    assert governor.reserve()[0] == pytest.approx(clock.current + 3601.0)


def test_max_wait_seconds_does_not_cap_retry_after_hard_pause(clock: FakeClock) -> None:
    # A retry_after hard pause is honored in full regardless of the pacing cap.
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=30.0)
    governor.observe(BudgetSnapshot(retry_after=600.0))

    assert governor.reserve()[0] == pytest.approx(clock.current + 601.0)


def test_reserve_exhausted_budget_targets_reset_plus_buffer(clock: FakeClock) -> None:
    governor = BudgetGovernor(now=clock, buffer_seconds=2.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=50))

    assert governor.reserve()[0] == pytest.approx(clock.current + 52.0)


def test_observe_with_retry_after_sets_hard_pause_and_fires_event(clock: FakeClock) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, on_event=events.append)

    governor.observe(BudgetSnapshot(retry_after=30.0))

    assert governor.reserve()[0] == pytest.approx(clock.current + 31.0)
    secondary_limit_events = [event for event in events if isinstance(event, SecondaryLimitEvent)]
    assert secondary_limit_events == [SecondaryLimitEvent(retry_after_seconds=30.0, pause_seconds=pytest.approx(31.0))]


def test_observe_keeps_longest_retry_after_pause(clock: FakeClock) -> None:
    """A later, shorter retry_after must not shorten an already-committed secondary-limit pause."""
    governor = BudgetGovernor(now=clock, buffer_seconds=0.0)
    governor.observe(BudgetSnapshot(retry_after=60.0))
    long_pause_target, _ = governor.reserve()

    governor.observe(BudgetSnapshot(retry_after=10.0))

    assert governor.reserve()[0] == long_pause_target


def test_reserve_returns_paced_slot_when_it_exceeds_pause_until(clock: FakeClock, governor: BudgetGovernor) -> None:
    """The floor in reserve() must take the larger of the two targets, not the smaller."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10

    first_slot, _ = governor.reserve()  # claims a slot at now, advances the cursor by one interval
    governor.observe(BudgetSnapshot(retry_after=1.0))  # pause_until = now + 1.0, well below the next paced slot
    second_slot, _ = governor.reserve()

    assert first_slot == pytest.approx(clock.current)
    assert second_slot == pytest.approx(clock.current + interval)
    assert governor.pause_until < second_slot


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

    governor.observe(BudgetSnapshot(limit=100, remaining=10, reset_at=None))

    budget_events = [event for event in events if isinstance(event, BudgetEvent)]
    assert budget_events[-1].reset_in_seconds is None


def test_budget_event_clamps_reset_in_seconds_to_zero_when_reset_at_in_past(clock: FakeClock) -> None:
    events: list[RateLimitEvent] = []
    governor = BudgetGovernor(now=clock, reserve_fraction=0.15, on_event=events.append)

    governor.observe(BudgetSnapshot(limit=100, remaining=10, reset_at=clock.current - 50))

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
        pytest.param(
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0, "retry_after": None},
            {"retry_after": 30.0},
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0, "retry_after": 30.0},
            id="retry_after_overlays_onto_none_base",
        ),
        pytest.param(
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0, "retry_after": 30.0},
            {"retry_after": None},
            {"limit": 5000, "remaining": 4999, "reset_at": 1700000000.0, "retry_after": 30.0},
            id="retry_after_preserved_when_update_is_none",
        ),
    ],
)
def test_merged_with_overlay_rule(
    base_fields: dict[str, Any], update_fields: dict[str, Any], expected_fields: dict[str, Any]
) -> None:
    base = BudgetSnapshot(**base_fields)

    merged = base.merged_with(BudgetSnapshot(**update_fields))

    assert merged == BudgetSnapshot(**expected_fields)


def test_merged_with_keeps_lowest_remaining_within_window() -> None:
    """Within one window (same reset_at) a stale higher remaining must not inflate the value."""
    base = BudgetSnapshot(limit=5000, remaining=4000, reset_at=1700000000.0)

    merged = base.merged_with(BudgetSnapshot(remaining=4999, reset_at=1700000000.0))

    assert merged.remaining == 4000


def test_merged_with_adopts_new_remaining_when_window_advances() -> None:
    """A larger reset_at is a new window, so the reported remaining is adopted as-is."""
    base = BudgetSnapshot(limit=5000, remaining=100, reset_at=1700000000.0)

    merged = base.merged_with(BudgetSnapshot(remaining=4999, reset_at=1700003600.0))

    assert merged.remaining == 4999
    assert merged.reset_at == 1700003600.0


def test_merged_with_discards_stale_window_update() -> None:
    """A smaller reset_at than the known one is a stale, out-of-order response and is discarded."""
    base = BudgetSnapshot(limit=5000, remaining=100, reset_at=1700003600.0)

    merged = base.merged_with(BudgetSnapshot(limit=5000, remaining=4999, reset_at=1700000000.0))

    assert merged == base


def test_merged_with_still_coalesces_retry_after_on_stale_window_update() -> None:
    """A secondary-limit signal is meaningful regardless of window, even on a stale update."""
    base = BudgetSnapshot(limit=5000, remaining=100, reset_at=1700003600.0)

    merged = base.merged_with(BudgetSnapshot(remaining=4999, reset_at=1700000000.0, retry_after=30.0))

    assert merged.remaining == 100
    assert merged.reset_at == 1700003600.0
    assert merged.retry_after == 30.0


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

    governor.observe(BudgetSnapshot(remaining=5))  # same reset_at, same clock, fewer requests left

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


async def test_wait_low_budget_sleeps_exactly_once_and_converges(
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
            governor.observe(BudgetSnapshot(retry_after=50.0))

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
            lambda clock, governor: governor.observe(BudgetSnapshot(retry_after=30.0)),
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


async def test_concurrent_waits_stagger_by_pacing_interval(
    clock: FakeClock, governor: BudgetGovernor, slept: list[float]
) -> None:
    """Concurrent rationed requests must each land on their own slot, one interval apart."""
    # remaining/reset_in are large relative to the number of tasks so that the interval, which
    # is recomputed from time-to-reset on every claim, barely drifts across the four waits.
    governor.observe(make_snapshot(clock=clock, limit=1000, remaining=100, reset_in=10000))
    interval = 10000 / 100
    finish_times: list[float] = []

    async def paced_request() -> None:
        await governor.wait()
        finish_times.append(clock.current)

    await asyncio.gather(*(paced_request() for _ in range(4)))

    assert len(set(finish_times)) == len(finish_times)
    for earlier, later in zip(sorted(finish_times), sorted(finish_times)[1:], strict=False):
        assert later - earlier == pytest.approx(interval, rel=0.05)


# ---------------------------------------------------------------------------
# InstrumentedAsyncLimiter + BudgetGovernor wiring
# ---------------------------------------------------------------------------


async def test_instrumented_limiter_calls_governor_wait_on_enter():
    governor = BudgetGovernor(buffer_seconds=0.0)
    governor.observe(BudgetSnapshot(retry_after=0.05))
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), budget_governor=governor)
    start = asyncio.get_event_loop().time()

    await asyncio.wait_for(limiter.__aenter__(), timeout=1.0)

    assert asyncio.get_event_loop().time() - start >= 0.05


async def test_instrumented_limiter_without_governor_does_not_wait():
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000))
    await asyncio.wait_for(limiter.__aenter__(), timeout=0.05)


async def test_instrumented_limiter_does_not_consume_bucket_token_during_governor_wait() -> None:
    """The bucket token must be acquired only after the governor wait, not before it."""
    governor = BudgetGovernor(buffer_seconds=0.0)
    governor.observe(BudgetSnapshot(retry_after=0.05))
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter, budget_governor=governor)

    task = asyncio.ensure_future(limiter.__aenter__())
    await asyncio.sleep(0)  # let the task start and enter the governor's pause

    assert real_limiter.has_capacity()  # token untouched while paused

    await asyncio.wait_for(task, timeout=1.0)

    assert not real_limiter.has_capacity()  # token acquired only once the wait is over


def test_instrumented_limiter_observe_without_governor_does_not_raise():
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000))
    limiter.observe(BudgetSnapshot(limit=100, remaining=50, reset_at=2000.0))
