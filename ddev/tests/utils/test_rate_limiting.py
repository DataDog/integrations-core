"""Tests for the generic async rate limiting utilities."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from aiolimiter import AsyncLimiter

from ddev.utils.rate_limiting import MAX_WAIT_ITERATIONS, BudgetGovernor, BudgetSnapshot, InstrumentedAsyncLimiter
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


@pytest.mark.parametrize(
    "none_callback",
    ["on_throttled", "on_acquired"],
    ids=["none_on_throttled", "none_on_acquired"],
)
async def test_instrumented_limiter_none_callback_does_not_raise(none_callback: str) -> None:
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter, **{none_callback: None})

    async with limiter:
        pass  # drain

    # Entering with an exhausted bucket and the callback set to None must not raise.
    await assert_blocks(limiter.__aenter__())


async def test_instrumented_limiter_calls_on_throttled_when_no_capacity():
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    on_throttled = MagicMock()
    limiter = InstrumentedAsyncLimiter(real_limiter, on_throttled=on_throttled)

    async with limiter:
        pass  # consumes the single token; has_capacity was True, so on_throttled not called

    # on_throttled fires before the coroutine suspends, even though the acquire never completes
    await assert_blocks(limiter.__aenter__())

    on_throttled.assert_called_once()


async def test_instrumented_limiter_does_not_call_on_throttled_when_capacity_available():
    on_throttled = MagicMock()
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=2, time_period=1000), on_throttled=on_throttled)

    async with limiter:
        pass

    on_throttled.assert_not_called()


async def test_instrumented_limiter_drains_real_bucket():
    """Acquiring through InstrumentedAsyncLimiter must consume a token from the real bucket."""
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter)

    assert real_limiter.has_capacity()
    async with limiter:
        pass
    assert not real_limiter.has_capacity()


async def test_instrumented_limiter_blocks_on_exhausted_bucket():
    """A second acquire on an empty bucket must block, not pass through."""
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter)

    async with limiter:
        pass  # drain the single token

    await assert_blocks(limiter.__aenter__())


async def test_instrumented_limiter_calls_on_acquired_after_token_granted():
    on_acquired = MagicMock()
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), on_acquired=on_acquired)

    async with limiter:
        pass

    on_acquired.assert_called_once()


async def test_instrumented_limiter_on_acquired_fires_after_wait():
    on_throttled = MagicMock()
    on_acquired = MagicMock()
    real_limiter = AsyncLimiter(max_rate=1, time_period=0.1)
    limiter = InstrumentedAsyncLimiter(real_limiter, on_throttled=on_throttled, on_acquired=on_acquired)

    async with limiter:
        pass  # drain; on_acquired fires once here

    # Bucket is empty — next acquire blocks until the 0.1s period refills it
    async with limiter:
        pass  # on_throttled fires on entry, on_acquired fires once the wait is over

    on_throttled.assert_called_once()
    assert on_acquired.call_count == 2


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

    assert governor.reserve() == pytest.approx(clock.current)


def test_reserve_paces_requests_when_remaining_at_or_below_reserve(clock: FakeClock, governor: BudgetGovernor) -> None:
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10  # (reset_at - now) / remaining

    # Without advancing the clock, successive reservations return targets that increase by
    # exactly one interval each — the pacing cursor advances exactly once per reserve() call.
    first = governor.reserve()
    second = governor.reserve()
    third = governor.reserve()

    assert first == pytest.approx(clock.current)
    assert second - first == pytest.approx(interval)
    assert third - second == pytest.approx(interval)


def test_reserve_caps_pacing_interval_at_max_wait_seconds(clock: FakeClock) -> None:
    # remaining=1 with an hour to reset would pace ~3600s apart; the cap bounds it.
    governor = BudgetGovernor(now=clock, max_wait_seconds=30.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=1, reset_in=3600))

    first = governor.reserve()
    second = governor.reserve()

    assert first == pytest.approx(clock.current)
    assert second - first == pytest.approx(30.0)


def test_reserve_does_not_cap_pacing_interval_below_max_wait_seconds(clock: FakeClock) -> None:
    # True interval (100/10 = 10s) is under the cap, so the cap must not shorten it.
    governor = BudgetGovernor(now=clock, max_wait_seconds=30.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))

    first = governor.reserve()
    second = governor.reserve()

    assert second - first == pytest.approx(10.0)


def test_max_wait_seconds_does_not_cap_exhausted_budget_hard_pause(clock: FakeClock) -> None:
    # The cap bounds voluntary pacing only; an exhausted budget still waits the full reset.
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=30.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=3600))

    assert governor.reserve() == pytest.approx(clock.current + 3601.0)


def test_max_wait_seconds_does_not_cap_retry_after_hard_pause(clock: FakeClock) -> None:
    # A retry_after hard pause is honored in full regardless of the pacing cap.
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, max_wait_seconds=30.0)
    governor.observe(BudgetSnapshot(retry_after=600.0))

    assert governor.reserve() == pytest.approx(clock.current + 601.0)


def test_reserve_exhausted_budget_targets_reset_plus_buffer(clock: FakeClock) -> None:
    governor = BudgetGovernor(now=clock, buffer_seconds=2.0)
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=50))

    assert governor.reserve() == pytest.approx(clock.current + 52.0)


def test_observe_with_retry_after_sets_hard_pause_and_fires_callback(clock: FakeClock) -> None:
    on_secondary_limit = MagicMock()
    governor = BudgetGovernor(now=clock, buffer_seconds=1.0, on_secondary_limit=on_secondary_limit)

    governor.observe(BudgetSnapshot(retry_after=30.0))

    assert governor.reserve() == pytest.approx(clock.current + 31.0)
    on_secondary_limit.assert_called_once_with(30.0)


def test_observe_keeps_longest_retry_after_pause(clock: FakeClock) -> None:
    """A later, shorter retry_after must not shorten an already-committed secondary-limit pause."""
    governor = BudgetGovernor(now=clock, buffer_seconds=0.0)
    governor.observe(BudgetSnapshot(retry_after=60.0))
    long_pause = governor.pause_until

    governor.observe(BudgetSnapshot(retry_after=10.0))

    assert governor.pause_until == long_pause


def test_reserve_returns_paced_slot_when_it_exceeds_pause_until(clock: FakeClock, governor: BudgetGovernor) -> None:
    """The floor in reserve() must take the larger of the two targets, not the smaller."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10

    first_slot = governor.reserve()  # claims a slot at now, advances the cursor by one interval
    governor.observe(BudgetSnapshot(retry_after=1.0))  # pause_until = now + 1.0, well below the next paced slot
    second_slot = governor.reserve()

    assert first_slot == pytest.approx(clock.current)
    assert second_slot == pytest.approx(clock.current + interval)
    assert governor.pause_until < second_slot


@pytest.mark.parametrize(
    ("remaining", "expected_fires"),
    [
        pytest.param(10, True, id="below_threshold"),
        pytest.param(15, True, id="at_threshold_boundary"),
        pytest.param(50, False, id="above_threshold"),
    ],
)
def test_observe_fires_on_budget_low(clock: FakeClock, remaining: int, expected_fires: bool) -> None:
    on_budget_low = MagicMock()
    governor = BudgetGovernor(now=clock, reserve_fraction=0.15, on_budget_low=on_budget_low)

    governor.observe(make_snapshot(clock=clock, limit=100, remaining=remaining, reset_in=40))

    if expected_fires:
        on_budget_low.assert_called_once_with(remaining, 100, pytest.approx(40.0))
    else:
        on_budget_low.assert_not_called()


@pytest.mark.parametrize(
    "reset_at_offset",
    [None, -50],
    ids=["reset_at_none", "reset_at_in_past"],
)
def test_notify_if_budget_low_clamps_reset_in_seconds_to_zero(clock: FakeClock, reset_at_offset: int | None) -> None:
    on_budget_low = MagicMock()
    governor = BudgetGovernor(now=clock, reserve_fraction=0.15, on_budget_low=on_budget_low)
    reset_at = None if reset_at_offset is None else clock.current + reset_at_offset

    governor.observe(BudgetSnapshot(limit=100, remaining=10, reset_at=reset_at))

    on_budget_low.assert_called_once_with(10, 100, pytest.approx(0.0))


def test_merged_with_overlays_non_none_fields():
    base = BudgetSnapshot(limit=5000, remaining=4999, reset_at=1700000000.0)

    merged = base.merged_with(BudgetSnapshot(remaining=4998))

    assert merged == BudgetSnapshot(limit=5000, remaining=4998, reset_at=1700000000.0)


def test_merged_with_keeps_known_values_when_update_field_is_none():
    base = BudgetSnapshot(limit=5000, remaining=4999, reset_at=1700000000.0)

    merged = base.merged_with(BudgetSnapshot())

    assert merged == base


@pytest.mark.parametrize(
    ("base_retry_after", "update_retry_after", "expected"),
    [
        pytest.param(None, 30.0, 30.0, id="overlays_onto_none_base"),
        pytest.param(30.0, None, 30.0, id="preserves_base_when_update_is_none"),
    ],
)
def test_merged_with_coalesces_retry_after(
    base_retry_after: float | None, update_retry_after: float | None, expected: float
) -> None:
    base = BudgetSnapshot(limit=5000, remaining=4999, reset_at=1700000000.0, retry_after=base_retry_after)

    merged = base.merged_with(BudgetSnapshot(retry_after=update_retry_after))

    assert merged.retry_after == expected


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


def test_observe_partial_snapshot_does_not_clobber_known_budget(clock: FakeClock, governor: BudgetGovernor) -> None:
    governor.observe(make_snapshot(clock=clock, limit=5000, remaining=4999, reset_in=60))

    governor.observe(BudgetSnapshot(remaining=4998))

    assert governor.budget.limit == 5000
    assert governor.budget.remaining == 4998
    assert governor.budget.reset_at == clock.current + 60


def test_none_callbacks_do_not_raise(clock: FakeClock) -> None:
    governor = BudgetGovernor(now=clock, on_budget_low=None, on_secondary_limit=None)

    governor.observe(make_snapshot(clock=clock, limit=100, remaining=1, reset_in=10, retry_after=5.0))

    assert governor.pause_until == pytest.approx(clock.current + 5.0 + governor.buffer_seconds)
    assert governor.budget.limit == 100
    assert governor.budget.remaining == 1
    assert governor.budget.reset_at == pytest.approx(clock.current + 10)


def test_claim_paced_slot_interval_widens_after_lower_remaining_observed(
    clock: FakeClock, governor: BudgetGovernor
) -> None:
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))

    first = governor.reserve()
    second = governor.reserve()
    interval_before = second - first

    governor.observe(BudgetSnapshot(remaining=5))  # same reset_at, same clock, fewer requests left

    third = governor.reserve()
    fourth = governor.reserve()
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
    """Regression: a single low-budget wait() must sleep once (~one interval), never diverge."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=10, reset_in=100))
    interval = 100 / 10
    # Pretend a prior request already reserved the first slot, so this one must actually wait.
    governor.reserve()

    await governor.wait()

    assert len(slept) == 1
    assert slept[0] == pytest.approx(interval)


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
    assert slept == pytest.approx([interval])


async def test_wait_extends_when_retry_after_observed_mid_wait(
    clock: FakeClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A retry_after pause raised while a request is mid-wait must extend the wait (pause_until floor)."""
    governor = BudgetGovernor(now=clock, buffer_seconds=0.0, reserve_fraction=0.15)
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


async def test_wait_caps_at_max_iterations_without_hanging(
    clock: FakeClock, governor: BudgetGovernor, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A permanently exhausted budget with a sleep that never advances the clock must not hang."""
    governor.observe(make_snapshot(clock=clock, limit=100, remaining=0, reset_in=100))

    sleep_count = 0

    async def fake_sleep(delay: float) -> None:
        nonlocal sleep_count
        sleep_count += 1

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    await asyncio.wait_for(governor.wait(), timeout=1.0)

    assert sleep_count == MAX_WAIT_ITERATIONS


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


def test_instrumented_limiter_observe_delegates_to_governor():
    governor = MagicMock(spec=BudgetGovernor)
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), budget_governor=governor)
    snapshot = BudgetSnapshot(limit=100, remaining=50, reset_at=2000.0)

    limiter.observe(snapshot)

    governor.observe.assert_called_once_with(snapshot)


def test_instrumented_limiter_observe_without_governor_does_not_raise():
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000))
    limiter.observe(BudgetSnapshot(limit=100, remaining=50, reset_at=2000.0))
