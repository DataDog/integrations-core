# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dispatcher-specific rate limiter factory."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from aiolimiter import AsyncLimiter

from ddev.utils.rate_limiting import RATE_LIMIT_TIME_PERIOD, InstrumentedAsyncLimiter


@dataclass(frozen=True)
class RateLimiterConfig:
    """Rate limit configuration for a single limiter tier."""

    max_rate: float
    time_period: float = RATE_LIMIT_TIME_PERIOD


@dataclass
class RateLimiterFactoryConfig:
    """Configuration for the Dispatcher's two-tier rate limiter factory.

    Rates are in requests per hour to match GitHub's documented limits.
    The sum of default.max_rate and slow.max_rate must not exceed total_max_rate.

    Default values:
    - default: 360 req/hr (6 req/min) — typical integrations
    - slow: 120 req/hr (2 req/min) — integrations with long-running tests
    - total_max_rate: 1,500 req/hr — = 15k octo-sts budget / 10 max concurrent runs
    """

    default: RateLimiterConfig = RateLimiterConfig(max_rate=360.0)
    slow: RateLimiterConfig = RateLimiterConfig(max_rate=120.0)
    total_max_rate: float = 1500.0
    slow_integrations: frozenset[str] = field(default_factory=frozenset)


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
        combined = cfg.default.max_rate + cfg.slow.max_rate
        if combined > cfg.total_max_rate:
            raise ValueError(
                f"default ({cfg.default.max_rate} req/hr) + slow ({cfg.slow.max_rate} req/hr) = "
                f"{combined} exceeds total_max_rate ({cfg.total_max_rate} req/hr)"
            )
        self._slow_integrations = cfg.slow_integrations
        self._default = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.default.max_rate, cfg.default.time_period),
            on_throttled=lambda: logger.debug("Default rate limiter throttling request") if logger else None,
        )
        self._slow = InstrumentedAsyncLimiter(
            AsyncLimiter(cfg.slow.max_rate, cfg.slow.time_period),
            on_throttled=lambda: logger.debug("Slow rate limiter throttling request") if logger else None,
        )

    def get_limiter(self, integrations: frozenset[str]) -> InstrumentedAsyncLimiter:
        """Return the appropriate rate limiter for the given set of integrations.

        Returns the slow limiter if any integration appears in the slow list,
        otherwise returns the default limiter.
        """
        return self._slow if integrations & self._slow_integrations else self._default
