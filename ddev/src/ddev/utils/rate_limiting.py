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

# Backstop for the pathological no-progress bug (e.g. a clock that never advances), which a
# time-based budget can never detect because a frozen now() never reaches its give-up point. With
# max_wait_seconds absorbing real floods and long windows, this reverts to "unreachable except by
# bug" — which is exactly what its RuntimeError means.
MAX_WAIT_ITERATIONS = 100


@dataclasses.dataclass(frozen=True)
class BudgetSnapshot:
    """Provider-agnostic snapshot of a remote rate-limit budget observed from a response.

    Every field is optional; a field left as None means the response did not report it.

    Attributes:
        limit: Total requests allowed in the current window.
        remaining: Requests still available in the current window.
        reset_at: Wall-clock epoch (seconds) at which the current window resets.
        retry_after: Seconds the provider asked us to wait before retrying, sent on a
            secondary/abuse rate-limit response.
    """

    limit: int | None = None
    remaining: int | None = None
    reset_at: float | None = None
    retry_after: float | None = None

    def merged_with(self, updates: BudgetSnapshot) -> BudgetSnapshot:
        """Return a new snapshot merging the budget fields of *updates* onto this one.

        Merges only limit, remaining, and reset_at; retry_after is not carried over. A None field
        in *updates* keeps the prior value. Within one window (unchanged reset_at) the lower
        remaining is kept; a larger reset_at is a new window and takes the reported remaining; a
        smaller reset_at is a stale response for a previous window and is discarded.
        """
        if self.reset_at is not None and updates.reset_at is not None and updates.reset_at < self.reset_at:
            return self
        reset_at = self.reset_at if updates.reset_at is None else updates.reset_at
        remaining = self.remaining if updates.remaining is None else updates.remaining
        if remaining is not None and self.remaining is not None and reset_at == self.reset_at:
            remaining = min(remaining, self.remaining)
        return BudgetSnapshot(
            limit=self.limit if updates.limit is None else updates.limit,
            remaining=remaining,
            reset_at=reset_at,
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
    ABANDONED = "abandoned"


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


class RateLimitWaitAbandoned(TimeoutError):
    """Raised when a single wait() would exceed the configured max_wait_seconds budget.

    Subclasses the builtin TimeoutError (which asyncio.TimeoutError aliases since 3.11) so generic
    timeout handling catches it, while catching this class enables a rate-limit-specific reaction.
    """

    def __init__(self, waited_seconds: float, remaining_seconds: float) -> None:
        super().__init__(
            f"Abandoned rate-limit wait after {waited_seconds:.1f}s; the target was still {remaining_seconds:.1f}s away"
        )
        self.waited_seconds = waited_seconds
        self.remaining_seconds = remaining_seconds


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
        now: Callable[[], float] = time.time,
        on_event: Callable[[RateLimitEvent], None] | None = None,
        max_wait_seconds: float | None = None,
    ) -> None:
        """
        Args:
            reserve_fraction: Fraction of the total limit at or below which the governor starts
                pacing requests to spread the remaining budget across the time left until reset.
            buffer_seconds: Extra seconds added to hard-pause waits (window reset and
                ``retry_after``) to absorb clock skew between us and the provider.
            now: Wall-clock source returning epoch seconds; defaults to ``time.time``.
            on_event: Called with a RateLimitEvent on every observe and every wait, for logging
                or emitting metrics.
            max_wait_seconds: Total time a single wait() may target before it raises
                RateLimitWaitAbandoned, measured from when the call starts and covering both
                exhausted-window waits and accumulated secondary-limit extensions. None (default)
                disables the killswitch and waits indefinitely for legitimate targets. If set below
                the provider's window length, a fully exhausted window will exceed the budget and
                raise; size this above the ``reset_at - now`` waits you intend to survive.
        """
        self.reserve_fraction = reserve_fraction
        self.buffer_seconds = buffer_seconds
        self.now = now
        self.on_event = on_event or (lambda event: None)
        self.max_wait_seconds = max_wait_seconds
        self.budget = NULL_SNAPSHOT
        self.pause_until = 0.0
        self.next_slot = 0.0

    def observe(self, snapshot: BudgetSnapshot) -> None:
        """Update governor state from a freshly observed provider rate-limit snapshot.

        Updates are commutative so out-of-order concurrent responses converge to the strictest
        constraint seen: the longest secondary-limit pause and the lowest remaining per window.
        """
        if snapshot.retry_after is not None:
            now = self.now()
            self.pause_until = max(self.pause_until, now + snapshot.retry_after + self.buffer_seconds)
            self.on_event(
                SecondaryLimitEvent(retry_after_seconds=snapshot.retry_after, pause_seconds=self.pause_until - now)
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
        # Race-free under asyncio only because there is no await between reading and advancing
        # self.next_slot in claim_paced_slot; inserting one here would let concurrent callers
        # claim the same slot. Enforced by test_pacing_claim_path_is_synchronous and
        # test_reserve_assigns_distinct_slots_under_concurrent_claims.
        target, reason = self.claim_budget_target_with_reason(self.now())
        if self.pause_until > target:
            return self.pause_until, PacingReason.SECONDARY_LIMIT
        return target, reason

    def claim_budget_target_with_reason(self, now: float) -> tuple[float, PacingReason]:
        """Earliest epoch this request may fire at based on the observed budget, with the reason.

        A rationed request never waits past the window reset: once the cursor reaches reset_at the
        window's budget is spent, so any further request waits exactly until reset plus buffer.
        """
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
            # Clamp at the window boundary before claiming: a slot at or past reset_at means this
            # window is spent, so wait until reset without advancing the cursor — later claims in
            # this window must get the same reset target, not ever-later ones.
            if max(self.next_slot, now) >= budget.reset_at:
                return budget.reset_at + self.buffer_seconds, PacingReason.EXHAUSTED
            return self.claim_paced_slot(now, budget.reset_at, budget.remaining), PacingReason.RATIONING
        return now, PacingReason.NONE

    def claim_paced_slot(self, now: float, reset_at: float, remaining: int) -> float:
        """Advance the shared pacing cursor by one interval and return this request's slot."""
        interval = (reset_at - now) / remaining
        slot = max(self.next_slot, now)
        self.next_slot = slot + interval
        return slot

    async def wait(self) -> None:
        """Reserve one slot, then sleep until its target and any hard-pause floor elapse.

        Raises RateLimitWaitAbandoned if the target ever exceeds the configured max_wait_seconds.
        """
        deadline, reason = self.reserve()
        start = self.now()
        wait_seconds = max(0.0, deadline - start)
        if wait_seconds <= 0:
            reason = PacingReason.NONE
        self.on_event(PacingEvent(wait_seconds=wait_seconds, reason=reason))
        give_up_at = None if self.max_wait_seconds is None else start + self.max_wait_seconds
        floor = max(deadline, self.pause_until)
        for _ in range(MAX_WAIT_ITERATIONS):
            current_floor = max(deadline, self.pause_until)
            now = self.now()
            delay = current_floor - now
            if delay <= 0:
                return
            if give_up_at is not None and current_floor > give_up_at:
                # The floor is past the budget: the request is doomed, so fail now rather than
                # sleep into a wait we already know we will abandon.
                self.on_event(PacingEvent(wait_seconds=delay, reason=PacingReason.ABANDONED))
                raise RateLimitWaitAbandoned(waited_seconds=now - start, remaining_seconds=delay)
            if current_floor > floor:
                # The floor only grows when pause_until does, i.e. a secondary-limit observe
                # extended the wait mid-sleep; emit so the extension is observable.
                self.on_event(PacingEvent(wait_seconds=delay, reason=PacingReason.SECONDARY_LIMIT))
                floor = current_floor
            await asyncio.sleep(delay)
        raise RuntimeError(
            f"BudgetGovernor.wait failed to converge after {MAX_WAIT_ITERATIONS} iterations "
            f"(remaining delay: {max(deadline, self.pause_until) - self.now()}s)"
        )


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
        if self.budget_governor is not None:
            await self.budget_governor.wait()
        throttled = not self.limiter.has_capacity()
        await self.limiter.__aenter__()
        self.on_event(BucketEvent(throttled=throttled, name=self.name))
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.limiter.__aexit__(exc_type, exc_val, exc_tb)

    def observe(self, snapshot: BudgetSnapshot) -> None:
        """Forward a provider rate-limit snapshot to the budget governor, if any."""
        if self.budget_governor is not None:
            self.budget_governor.observe(snapshot)
