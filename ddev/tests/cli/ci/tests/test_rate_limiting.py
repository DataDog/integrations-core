"""Tests for the Dispatcher rate limiter factory."""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from ddev.cli.ci.tests.rate_limiting import RateLimiterConfig, RateLimiterFactory, RateLimiterFactoryConfig

# ---------------------------------------------------------------------------
# RateLimiterConfig field validation
# ---------------------------------------------------------------------------


def test_rate_limiter_config_rejects_zero_hourly_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(hourly_max_rate=0)


def test_rate_limiter_config_rejects_negative_hourly_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(hourly_max_rate=-1.0)


def test_rate_limiter_config_rejects_zero_time_period():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(hourly_max_rate=10.0, time_period=0)


def test_rate_limiter_config_rejects_negative_time_period():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(hourly_max_rate=10.0, time_period=-1.0)


def test_rate_limiter_config_limiter_max_rate_scales_with_time_period():
    # 360 req/hr over a 60s window = 6 tokens per window
    cfg = RateLimiterConfig(hourly_max_rate=360.0, time_period=60.0)
    assert cfg.limiter_max_rate == pytest.approx(6.0)


def test_rate_limiter_config_limiter_max_rate_default_time_period():
    # 360 req/hr over a 3600s window = 360 tokens per window
    cfg = RateLimiterConfig(hourly_max_rate=360.0)
    assert cfg.limiter_max_rate == pytest.approx(360.0)


# ---------------------------------------------------------------------------
# RateLimiterFactoryConfig construction validation
# ---------------------------------------------------------------------------


def test_factory_config_raises_when_combined_rate_exceeds_total():
    with pytest.raises(ValidationError, match="exceeds total_max_rate"):
        RateLimiterFactoryConfig(
            default=RateLimiterConfig(hourly_max_rate=800.0),
            slow=RateLimiterConfig(hourly_max_rate=800.0),
            total_hourly_max_rate=1500.0,
        )


def test_factory_config_accepts_combined_rate_at_limit():
    assert RateLimiterFactoryConfig(
        default=RateLimiterConfig(hourly_max_rate=750.0),
        slow=RateLimiterConfig(hourly_max_rate=750.0),
        total_hourly_max_rate=1500.0,
    )


def test_factory_config_default_is_within_bounds():
    assert RateLimiterFactoryConfig()


def test_factory_config_rejects_negative_total_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterFactoryConfig(total_max_rate=-1.0)


# ---------------------------------------------------------------------------
# RateLimiterFactory construction
# ---------------------------------------------------------------------------


def test_factory_default_config_is_within_bounds():
    assert RateLimiterFactory() is not None


def test_factory_with_logger_does_not_raise():
    assert RateLimiterFactory(logger=logging.getLogger("test")) is not None


# ---------------------------------------------------------------------------
# get_limiter — tier selection
# ---------------------------------------------------------------------------


def test_get_limiter_returns_default_for_non_slow_integrations():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo", "mysql"})))
    assert factory.get_limiter(frozenset({"redis", "postgres_lite"})) is factory._default


def test_get_limiter_returns_slow_for_slow_integration():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo", "mysql"})))
    assert factory.get_limiter(frozenset({"mongo"})) is factory._slow


def test_get_limiter_returns_slow_when_any_integration_is_slow():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo", "mysql"})))
    assert factory.get_limiter(frozenset({"redis", "mysql", "postgres_lite"})) is factory._slow


def test_get_limiter_returns_default_for_empty_integrations():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo"})))
    assert factory.get_limiter(frozenset()) is factory._default


# ---------------------------------------------------------------------------
# get_limiter — shared instances (the global-cap invariant)
# ---------------------------------------------------------------------------


def test_get_limiter_same_tier_returns_same_object():
    """All default-tier batches must share the same limiter to enforce a global cap."""
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo"})))
    assert factory.get_limiter(frozenset({"redis"})) is factory.get_limiter(frozenset({"postgres"}))


def test_get_limiter_slow_tier_returns_same_object():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo", "mysql"})))
    assert factory.get_limiter(frozenset({"mongo"})) is factory.get_limiter(frozenset({"mysql"}))
