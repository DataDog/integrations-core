# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dispatcher-specific rate limiter factory."""

from __future__ import annotations

import logging

from aiolimiter import AsyncLimiter
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ddev.utils.rate_limiting import RATE_LIMIT_TIME_PERIOD, InstrumentedAsyncLimiter

SECONDS_PER_HOUR = 3600.0


class RateLimiterConfig(BaseModel):
    """Rate limit configuration for a single limiter tier."""

    model_config = ConfigDict(frozen=True)

    hourly_max_rate: float = Field(gt=0)
    time_period: float = Field(default=RATE_LIMIT_TIME_PERIOD, gt=0)

    @property
    def limiter_max_rate(self) -> float:
        """Bucket size to pass to AsyncLimiter for the configured time_period."""
        return self.hourly_max_rate * self.time_period / SECONDS_PER_HOUR


class RateLimiterFactoryConfig(BaseModel):
    """Configuration for the Dispatcher's two-tier rate limiter factory.

    All rates are in requests per hour to match GitHub's documented limits.
    The sum of default.hourly_max_rate and slow.hourly_max_rate must not exceed total_max_rate.

    Default values:
    - default: 360 req/hr (6 req/min) — typical integrations
    - slow: 120 req/hr (2 req/min) — integrations with long-running tests
    - total_max_rate: 1,500 req/hr — = 15k octo-sts budget / 10 max concurrent runs
    """

    default: RateLimiterConfig = RateLimiterConfig(hourly_max_rate=360.0)
    slow: RateLimiterConfig = RateLimiterConfig(hourly_max_rate=120.0)
    total_max_rate: float = Field(default=1500.0, gt=0)
    slow_integrations: frozenset[str] = frozenset()

    @model_validator(mode="after")
    def validate_combined_rate(self) -> RateLimiterFactoryConfig:
        combined = self.default.hourly_max_rate + self.slow.hourly_max_rate
        if combined > self.total_max_rate:
            raise ValueError(
                f"default ({self.default.hourly_max_rate} req/hr) + slow ({self.slow.hourly_max_rate} req/hr) = "
                f"{combined} exceeds total_max_rate ({self.total_max_rate} req/hr)"
            )
        return self


class RateLimiterFactory:
    """Creates and vends rate limiters for the Dispatcher.

    Holds exactly two shared InstrumentedAsyncLimiter instances — one for
    the default tier and one for the slow tier. All processors in a dispatcher
    run share the same factory, so they compete for the same token buckets and
    the per-run combined rate stays bounded.
    """

    def __init__(
        self,
        config: RateLimiterFactoryConfig | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        cfg = config or RateLimiterFactoryConfig()
        self._slow_integrations = cfg.slow_integrations
        self._default = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.default.limiter_max_rate, cfg.default.time_period),
            on_throttled=lambda: logger.debug("Default rate limiter throttling request") if logger else None,
        )
        self._slow = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.slow.limiter_max_rate, cfg.slow.time_period),
            on_throttled=lambda: logger.debug("Slow rate limiter throttling request") if logger else None,
        )

    def get_limiter(self, integrations: frozenset[str]) -> InstrumentedAsyncLimiter:
        """Return the appropriate rate limiter for the given set of integrations.

        Returns the slow limiter if any integration appears in the slow list,
        otherwise returns the default limiter.
        """
        return self._slow if integrations & self._slow_integrations else self._default
