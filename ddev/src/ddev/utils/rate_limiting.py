# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Generic async rate limiting utilities."""

from __future__ import annotations

import asyncio
import dataclasses
import time
from collections.abc import Callable
from typing import Any

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
        """Return a new snapshot with the non-None fields of *updates* overlaid on this one.

        A response only carries the headers it reported, so a None field in *updates* means
        "not reported this time" and must not clobber a value we already know.
        """
        return BudgetSnapshot(
            limit=self.limit if updates.limit is None else updates.limit,
            remaining=self.remaining if updates.remaining is None else updates.remaining,
            reset_at=self.reset_at if updates.reset_at is None else updates.reset_at,
            retry_after=self.retry_after if updates.retry_after is None else updates.retry_after,
        )


NULL_SNAPSHOT = BudgetSnapshot()
"""Shared all-None snapshot: the governor's initial state and the "no headers" sentinel."""


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
        on_budget_low: Callable[[int, int, float], None] | None = None,
        on_secondary_limit: Callable[[float], None] | None = None,
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
            on_budget_low: Called as ``(remaining, limit, reset_in_seconds)`` whenever an
                observed snapshot lands at or below the reserve threshold. Use it to log or
                emit a metric on the shared budget running low.
            on_secondary_limit: Called with the ``retry_after`` seconds whenever a
                secondary/abuse rate-limit response is observed and a hard pause is armed.
        """
        self.reserve_fraction = reserve_fraction
        self.buffer_seconds = buffer_seconds
        self.max_wait_seconds = max_wait_seconds
        self.now = now
        self.on_budget_low = on_budget_low or (lambda remaining, limit, reset_in_seconds: None)
        self.on_secondary_limit = on_secondary_limit or (lambda retry_after: None)
        self.budget = NULL_SNAPSHOT
        self.pause_until = 0.0
        self.next_slot = 0.0

    def observe(self, snapshot: BudgetSnapshot) -> None:
        """Update governor state from a freshly observed provider rate-limit snapshot."""
        if snapshot.retry_after is not None:
            self.pause_until = self.now() + snapshot.retry_after + self.buffer_seconds
            self.on_secondary_limit(snapshot.retry_after)
        self.budget = self.budget.merged_with(snapshot)
        self.notify_if_budget_low()

    def notify_if_budget_low(self) -> None:
        """Fire the on_budget_low callback when the tracked budget is at or below the reserve."""
        limit, remaining = self.budget.limit, self.budget.remaining
        if limit is not None and remaining is not None and remaining <= self.reserve_fraction * limit:
            now = self.now()
            reset_in_seconds = max(0.0, (self.budget.reset_at or now) - now)
            self.on_budget_low(remaining, limit, reset_in_seconds)

    def reserve(self) -> float:
        """Reserve a pacing slot for the next request and return its absolute epoch target.

        Advances the pacing cursor at most once per call so a single caller reserves exactly
        one slot; the returned target is floored by any active secondary-limit hard pause.
        """
        return max(self.budget_target(), self.pause_until)

    def budget_target(self) -> float:
        """Earliest epoch this request may fire at based on the observed budget, ignoring hard pauses."""
        now = self.now()
        budget = self.budget
        # Handle the case where the remote does not provide:
        # - limit: this means the budget does not govern anything
        # - remaining: this means we have no way of knowing how much budget is left
        # - reset_at: this means the budget does not reset at a known time
        if budget.limit is None or budget.remaining is None or budget.reset_at is None or now >= budget.reset_at:
            return now
        if budget.remaining <= 0:
            return budget.reset_at + self.buffer_seconds
        if budget.remaining <= self.reserve_fraction * budget.limit:
            return self.claim_paced_slot(now, budget.reset_at, budget.remaining)
        return now

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
        deadline = self.reserve()
        for _ in range(MAX_WAIT_ITERATIONS):
            delay = max(deadline, self.pause_until) - self.now()
            if delay <= 0:
                return
            await asyncio.sleep(delay)


class InstrumentedAsyncLimiter:
    """Thin async context manager wrapper around AsyncLimiter.

    Fires an optional callback when a request has to wait for capacity,
    allowing callers to log or emit metrics on throttling events. Optionally layers a
    BudgetGovernor on top, which adds extra backpressure reactive to a remote provider's
    reported rate-limit budget.
    """

    def __init__(
        self,
        limiter: AsyncLimiter,
        on_throttled: Callable[[], None] | None = None,
        on_acquired: Callable[[], None] | None = None,
        budget_governor: BudgetGovernor | None = None,
    ) -> None:
        self._limiter = limiter
        self._on_throttled = on_throttled or (lambda: None)
        self._on_acquired = on_acquired or (lambda: None)
        self.budget_governor = budget_governor

    async def __aenter__(self) -> InstrumentedAsyncLimiter:
        if not self._limiter.has_capacity():
            self._on_throttled()
        await self._limiter.__aenter__()
        if self.budget_governor is not None:
            await self.budget_governor.wait()
        self._on_acquired()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._limiter.__aexit__(exc_type, exc_val, exc_tb)

    def observe(self, snapshot: BudgetSnapshot) -> None:
        """Forward a provider rate-limit snapshot to the budget governor, if any."""
        if self.budget_governor is not None:
            self.budget_governor.observe(snapshot)
