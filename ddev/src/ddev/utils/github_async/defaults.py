# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Default rate-limit protection for the async GitHub client.

The rate-limiting mechanism in ``ddev.utils.rate_limiting`` is provider-agnostic; the defaults here
are GitHub-shaped: the bucket is sized to GitHub's primary limit and the log messages are tuned to
GitHub's headers and secondary-limit behavior.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from aiolimiter import AsyncLimiter

from ddev.utils.rate_limiting import (
    RATE_LIMIT_TIME_PERIOD,
    BucketEvent,
    BudgetEvent,
    BudgetGovernor,
    InstrumentedAsyncLimiter,
    PacingEvent,
    PacingReason,
    RateLimitEvent,
    SecondaryLimitEvent,
)

logger = logging.getLogger(__name__)


def log_rate_limit_events(logger: logging.Logger = logger) -> Callable[[RateLimitEvent], None]:
    """Return an on_event callback that logs rate-limit events for operators.

    Stateless: a low budget logs at DEBUG on every observe, so it can be chatty. An edge-detecting
    variant that logs only when is_low flips is a possible follow-up.
    """

    def handle(event: RateLimitEvent) -> None:
        # Lazy %-style args so a disabled level costs nothing.
        match event:
            case SecondaryLimitEvent():
                logger.warning(
                    "GitHub secondary rate limit hit: asked to retry after %.0fs, pausing all requests for %.0fs",
                    event.retry_after_seconds,
                    event.pause_seconds,
                )
            case PacingEvent(reason=PacingReason.ABANDONED):
                logger.error(
                    "rate limit wait abandoned: gave up after the configured budget with %.1fs still to wait",
                    event.wait_seconds,
                )
            case PacingEvent(reason=PacingReason.EXHAUSTED):
                logger.warning("rate limit budget exhausted: waiting %.1fs for the window to reset", event.wait_seconds)
            case PacingEvent(reason=PacingReason.SECONDARY_LIMIT):
                logger.warning("rate limit secondary pause: waiting %.1fs before the next request", event.wait_seconds)
            case PacingEvent(reason=PacingReason.RATIONING):
                logger.info("rate limit budget low: pacing, next request in %.1fs", event.wait_seconds)
            case PacingEvent():
                logger.debug("rate limit healthy: no pacing delay applied")
            case BudgetEvent() if event.is_low:
                logger.debug(
                    "rate limit budget low: %s/%s remaining, resets in %ss",
                    event.remaining,
                    event.limit,
                    event.reset_in_seconds,
                )
            case BudgetEvent():
                pass  # Healthy budget: nothing worth an operator's attention.
            case BucketEvent() if event.throttled:
                logger.debug("%s rate limiter throttling request", event.name)
            case BucketEvent():
                pass  # Bucket had capacity: nothing worth an operator's attention.
            case _:
                # New event types must not break logging.
                logger.debug("unhandled rate limit event: %r", event)

    return handle


def default_github_rate_limiter(
    on_event: Callable[[RateLimitEvent], None] | None = None,
    budget_governor: BudgetGovernor | None = None,
    name: str = "github",
) -> InstrumentedAsyncLimiter:
    """Build the default GitHub rate limiter: a permissive bucket fronting a reactive governor.

    The bucket is deliberately permissive (5000/hour mirrors GitHub's primary limit, so the local
    bucket effectively never throttles); the BudgetGovernor is the real protection, reacting to the
    shared budget and secondary limits reported in response headers. With a healthy budget and no
    secondary limits the governor adds zero wait, so this default is invisible to well-behaved
    callers and engages only once GitHub has already signaled backpressure.
    """
    handler = on_event or log_rate_limit_events()
    governor = budget_governor or BudgetGovernor(on_event=handler)
    # The governor and the InstrumentedAsyncLimiter each carry their own on_event slot; wiring only
    # one silently drops half the events (bucket-throttle vs budget/pacing), so wire both.
    return InstrumentedAsyncLimiter(
        AsyncLimiter(max_rate=5000, time_period=RATE_LIMIT_TIME_PERIOD),
        on_event=handler,
        budget_governor=governor,
        name=name,
    )
