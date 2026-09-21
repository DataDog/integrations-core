# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dispatcher-specific rate limiter factory."""

from __future__ import annotations

import logging
from collections.abc import Callable

from aiolimiter import AsyncLimiter
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ddev.utils.rate_limiting import (
    RATE_LIMIT_TIME_PERIOD,
    BudgetGovernor,
    InstrumentedAsyncLimiter,
    RateLimitEvent,
    RateLimitEventType,
)

SECONDS_PER_HOUR = 3600.0


def event_logger(logger: logging.Logger) -> Callable[[RateLimitEvent], None]:
    """Build an on_event handler that logs the informative rate-limit events at debug level."""

    def handle(event: RateLimitEvent) -> None:
        if event.type is RateLimitEventType.BUDGET and event.is_low:
            logger.debug(
                "GitHub rate-limit budget low: %s/%s remaining, resets in %.1fs",
                event.remaining,
                event.limit,
                event.reset_in_seconds,
            )
        elif event.type is RateLimitEventType.SECONDARY_LIMIT:
            logger.debug("GitHub secondary rate limit hit, retry after %.1fs", event.retry_after_seconds)
        elif event.type is RateLimitEventType.BUCKET and event.throttled:
            logger.debug("%s rate limiter throttling request", event.name)

    return handle


class RateLimiterConfig(BaseModel):
    """A local bucket with an initial ``max_rate`` burst, refilled over ``time_period``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_rate: float = Field(gt=0)
    time_period: float = Field(default=RATE_LIMIT_TIME_PERIOD, gt=0)

    @property
    def hourly_rate(self) -> float:
        """Sustained refill rate expressed in requests per hour, excluding the initial burst."""
        return self.max_rate / self.time_period * SECONDS_PER_HOUR


class RateLimiterFactoryConfig(BaseModel):
    """Configuration for the Dispatcher's shared rate limiter tiers.

    The sum of sustained refill rates must not exceed ``total_hourly_max_rate``.
    Initially full buckets allow additional bursts, so this is not a hard request
    count in a rolling hour. The shared governor honors GitHub's actual budget and pauses.

    Default refill rates are 360/hour for polling, 120/hour for slow integrations,
    and 1,000/hour for artifacts. The 1,500/hour ceiling is a per-run sharing guideline
    based on a 15,000/hour installation budget and ten concurrent runs.
    """

    model_config = ConfigDict(extra="forbid")

    default: RateLimiterConfig = RateLimiterConfig(max_rate=360.0)
    slow: RateLimiterConfig = RateLimiterConfig(max_rate=120.0)
    artifacts: RateLimiterConfig = RateLimiterConfig(max_rate=1000.0)
    total_hourly_max_rate: float = Field(default=1500.0, gt=0)
    slow_integrations: frozenset[str] = frozenset()
    reserve_fraction: float = Field(default=0.15, gt=0, le=1)
    budget_buffer_seconds: float = Field(default=1.0, ge=0)

    @model_validator(mode="after")
    def validate_combined_rate(self) -> RateLimiterFactoryConfig:
        combined = self.default.hourly_rate + self.slow.hourly_rate + self.artifacts.hourly_rate
        if combined > self.total_hourly_max_rate:
            raise ValueError(
                f"default ({self.default.hourly_rate} req/hr) + slow ({self.slow.hourly_rate} req/hr) + "
                f"artifacts ({self.artifacts.hourly_rate} req/hr) = "
                f"{combined} exceeds total_hourly_max_rate ({self.total_hourly_max_rate} req/hr)"
            )
        return self


class RateLimiterFactory:
    """Creates and vends rate limiters for the Dispatcher.

    One bucket per tier, shared across the run. All tiers share the same governor
    so a provider pause or exhausted budget constrains every kind of request.
    """

    def __init__(
        self,
        config: RateLimiterFactoryConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        cfg = config or RateLimiterFactoryConfig()
        self.slow_integrations = cfg.slow_integrations
        on_event = event_logger(logger) if logger else None
        budget_governor = BudgetGovernor(
            reserve_fraction=cfg.reserve_fraction,
            buffer_seconds=cfg.budget_buffer_seconds,
            on_event=on_event,
        )
        self.default = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.default.max_rate, cfg.default.time_period),
            on_event=on_event,
            budget_governor=budget_governor,
            name="default",
        )
        self.slow = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.slow.max_rate, cfg.slow.time_period),
            on_event=on_event,
            budget_governor=budget_governor,
            name="slow",
        )
        self.artifacts = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.artifacts.max_rate, cfg.artifacts.time_period),
            on_event=on_event,
            budget_governor=budget_governor,
            name="artifacts",
        )

    def get_limiter(self, integrations: frozenset[str]) -> InstrumentedAsyncLimiter:
        """Return the appropriate rate limiter for the given set of integrations.

        Returns the slow limiter if any integration appears in the slow list,
        otherwise returns the default limiter.
        """
        return self.slow if integrations & self.slow_integrations else self.default
