# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Generic async rate limiting utilities."""

from __future__ import annotations

import asyncio
import dataclasses
import time
from collections.abc import Callable
from enum import StrEnum
from typing import Any, Literal

from aiolimiter import AsyncLimiter

RATE_LIMIT_TIME_PERIOD = 3600.0  # 1 hour — matches GitHub's rate limit window

MAX_WAIT_ITERATIONS = 1000  # safety cap; the pacing math converges well before this


@dataclasses.dataclass(frozen=True)
class BudgetSnapshot:
    """Provider-agnostic snapshot of a remote rate-limit budget observed from a response.

    Every field is optional so a snapshot can carry only what a given response exposed;
    a field left as None means the response did not report it and the governor keeps its
    previous value for that field.

    Attributes:
        limit: Total requests allowed in the current window, as reported by the provider.
        remaining: Requests still available in the current window.
        reset_at: Wall-clock epoch (seconds) at which the current window resets and the
            budget refills.
        retry_after: Seconds the provider asked us to wait before retrying, sent on a
            secondary/abuse rate-limit response. Triggers a hard pause when present.
    """

    limit: int | None = None
    remaining: int | None = None
    reset_at: float | None = None
    retry_after: float | None = None

    def merged_with(self, updates: BudgetSnapshot) -> BudgetSnapshot:
        """Return a new snapshot combining this observation with a newer one (*updates*).

        A None field in *updates* means "not reported this time" and keeps the prior value.
        Within one window (unchanged reset_at) remaining is monotonically non-increasing, so a
        higher remaining from a stale, out-of-order response is discarded in favour of the lower
        one; a larger reset_at is a new window and adopts the reported remaining as-is.
        """
        reset_at = self.reset_at if updates.reset_at is None else updates.reset_at
        remaining = self.remaining if updates.remaining is None else updates.remaining
        if remaining is not None and self.remaining is not None and reset_at == self.reset_at:
            remaining = min(remaining, self.remaining)
        return BudgetSnapshot(
            limit=self.limit if updates.limit is None else updates.limit,
            remaining=remaining,
            reset_at=reset_at,
            retry_after=self.retry_after if updates.retry_after is None else updates.retry_after,
        )


NULL_SNAPSHOT = BudgetSnapshot()
"""Shared all-None snapshot: the governor's initial state and the "no headers" sentinel."""


class RateLimitEventType(StrEnum):
    """Discriminator for the RateLimitEvent union."""

    BUCKET = "bucket"
    BUDGET = "budget"
    SECONDARY_LIMIT = "secondary_limit"
    PACING = "pacing"


class PacingReason(StrEnum):
    """Why a PacingEvent's wait_seconds is what it is."""

    NONE = "none"
    RATIONING = "rationing"
    EXHAUSTED = "exhausted"
    SECONDARY_LIMIT = "secondary_limit"


@dataclasses.dataclass(frozen=True)
class BucketEvent:
    """Fired once per InstrumentedAsyncLimiter acquire, carrying whether it had to throttle."""

    throttled: bool
    name: str = ""
    type: Literal[RateLimitEventType.BUCKET] = RateLimitEventType.BUCKET


@dataclasses.dataclass(frozen=True)
class BudgetEvent:
    """Fired on every BudgetGovernor.observe with the current budget and pause state."""

    is_low: bool
    is_paused: bool
    limit: int | None = None
    remaining: int | None = None
    reset_in_seconds: float | None = None
    pause_remaining_seconds: float = 0.0
    type: Literal[RateLimitEventType.BUDGET] = RateLimitEventType.BUDGET


@dataclasses.dataclass(frozen=True)
class SecondaryLimitEvent:
    """Fired when a secondary/abuse rate-limit response arms a hard pause."""

    retry_after_seconds: float
    pause_seconds: float
    type: Literal[RateLimitEventType.SECONDARY_LIMIT] = RateLimitEventType.SECONDARY_LIMIT


@dataclasses.dataclass(frozen=True)
class PacingEvent:
    """Fired once per BudgetGovernor.wait with the delay applied and why."""

    wait_seconds: float
    reason: PacingReason
    type: Literal[RateLimitEventType.PACING] = RateLimitEventType.PACING


RateLimitEvent = BucketEvent | BudgetEvent | SecondaryLimitEvent | PacingEvent


class BudgetGovernor:
    """Reactive backpressure control loop driven by a remote provider's rate-limit information.

    Layered on top of a local token bucket: the bucket enforces our own request rate, while
    the governor reacts to the remote server's reported remaining budget (which is shared
    across the whole organization and invisible to the local bucket) and adds extra delay
    once that budget runs low.
    """

    def __init__(
        self,
        reserve_fraction: float = 0.15,
        buffer_seconds: float = 1.0,
        max_wait_seconds: float | None = None,
        now: Callable[[], float] = time.time,
        on_event: Callable[[RateLimitEvent], None] | None = None,
    ) -> None:
        """
        Args:
            reserve_fraction: Fraction of the total limit at or below which the governor
                starts rationing. While ``remaining > reserve_fraction * limit`` the local
                bucket alone governs; once at or below it, requests are paced to spread the
                remaining budget across the time left until reset.
            buffer_seconds: Extra seconds added to hard-pause waits (window reset and
                ``retry_after``) to absorb clock skew between us and the provider.
            max_wait_seconds: Upper bound on a single rationing interval. As remaining nears
                empty the unbounded interval (time_to_reset / remaining) can approach the whole
                window; this caps it so a request never paces itself out by more than this many
                seconds. None means uncapped. Only bounds voluntary pacing: the hard pauses for
                an exhausted budget or a ``retry_after`` are always honored in full.
            now: Wall-clock source returning epoch seconds. Injectable so tests can drive
                time deterministically; defaults to ``time.time``.
            on_event: Called with a RateLimitEvent on every observe and every wait, so callers
                can log or emit continuous metrics from a single handler.
        """
        self.reserve_fraction = reserve_fraction
        self.buffer_seconds = buffer_seconds
        self.max_wait_seconds = max_wait_seconds
        self.now = now
        self.on_event = on_event or (lambda event: None)
        self.budget = NULL_SNAPSHOT
        self.pause_until = 0.0
        self.next_slot = 0.0

    def observe(self, snapshot: BudgetSnapshot) -> None:
        """Update governor state from a freshly observed provider rate-limit snapshot.

        Updates are commutative so out-of-order concurrent responses converge to the strictest
        constraint seen: the longest secondary-limit pause and the lowest remaining per window.
        """
        if snapshot.retry_after is not None:
            self.pause_until = max(self.pause_until, self.now() + snapshot.retry_after + self.buffer_seconds)
            self.on_event(
                SecondaryLimitEvent(
                    retry_after_seconds=snapshot.retry_after, pause_seconds=self.pause_until - self.now()
                )
            )
        self.budget = self.budget.merged_with(snapshot)
        self.emit_budget_event()

    def emit_budget_event(self) -> None:
        """Build and emit a BudgetEvent reflecting the current budget and pause state."""
        limit, remaining = self.budget.limit, self.budget.remaining
        is_low = limit is not None and remaining is not None and remaining <= self.reserve_fraction * limit
        now = self.now()
        reset_in_seconds = None if self.budget.reset_at is None else max(0.0, self.budget.reset_at - now)
        self.on_event(
            BudgetEvent(
                is_low=is_low,
                is_paused=now < self.pause_until,
                limit=limit,
                remaining=remaining,
                reset_in_seconds=reset_in_seconds,
                pause_remaining_seconds=max(0.0, self.pause_until - now),
            )
        )

    def reserve(self) -> tuple[float, PacingReason]:
        """Reserve a pacing slot for the next request; return its epoch target and the reason.

        Advances the pacing cursor at most once per call so a single caller reserves exactly one
        slot. The target is floored by any active secondary-limit hard pause, which then dominates
        the reason.
        """
        target, reason = self.budget_target_with_reason(self.now())
        if self.pause_until > target:
            return self.pause_until, PacingReason.SECONDARY_LIMIT
        return target, reason

    def budget_target_with_reason(self, now: float) -> tuple[float, PacingReason]:
        """Earliest epoch this request may fire at based on the observed budget, with the reason."""
        budget = self.budget
        # Handle the case where the remote does not provide:
        # - limit: this means the budget does not govern anything
        # - remaining: this means we have no way of knowing how much budget is left
        # - reset_at: this means the budget does not reset at a known time
        if budget.limit is None or budget.remaining is None or budget.reset_at is None or now >= budget.reset_at:
            return now, PacingReason.NONE
        if budget.remaining <= 0:
            return budget.reset_at + self.buffer_seconds, PacingReason.EXHAUSTED
        if budget.remaining <= self.reserve_fraction * budget.limit:
            return self.claim_paced_slot(now, budget.reset_at, budget.remaining), PacingReason.RATIONING
        return now, PacingReason.NONE

    def claim_paced_slot(self, now: float, reset_at: float, remaining: int) -> float:
        """Advance the shared pacing cursor by one interval and return this request's slot."""
        interval = (reset_at - now) / remaining
        if self.max_wait_seconds is not None:
            interval = min(interval, self.max_wait_seconds)
        slot = max(self.next_slot, now)
        self.next_slot = slot + interval
        return slot

    async def wait(self) -> None:
        """Reserve one slot, then sleep until its target and any hard-pause floor elapse."""
        deadline, reason = self.reserve()
        now = self.now()
        wait_seconds = max(0.0, deadline - now)
        if wait_seconds <= 0:
            reason = PacingReason.NONE
        self.on_event(PacingEvent(wait_seconds=wait_seconds, reason=reason))
        for _ in range(MAX_WAIT_ITERATIONS):
            delay = max(deadline, self.pause_until) - self.now()
            if delay <= 0:
                return
            await asyncio.sleep(delay)


class InstrumentedAsyncLimiter:
    """Thin async context manager wrapper around AsyncLimiter.

    Fires an optional callback on every acquire, allowing callers to log or emit metrics on
    throttling. Optionally layers a BudgetGovernor on top, which adds extra backpressure
    reactive to a remote provider's reported rate-limit budget.
    """

    def __init__(
        self,
        limiter: AsyncLimiter,
        on_event: Callable[[RateLimitEvent], None] | None = None,
        budget_governor: BudgetGovernor | None = None,
        name: str = "",
    ) -> None:
        self.limiter = limiter
        self.on_event = on_event or (lambda event: None)
        self.budget_governor = budget_governor
        self.name = name

    async def __aenter__(self) -> InstrumentedAsyncLimiter:
        throttled = not self.limiter.has_capacity()
        await self.limiter.__aenter__()
        if self.budget_governor is not None:
            await self.budget_governor.wait()
        self.on_event(BucketEvent(throttled=throttled, name=self.name))
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.limiter.__aexit__(exc_type, exc_val, exc_tb)

    def observe(self, snapshot: BudgetSnapshot) -> None:
        """Forward a provider rate-limit snapshot to the budget governor, if any."""
        if self.budget_governor is not None:
            self.budget_governor.observe(snapshot)
