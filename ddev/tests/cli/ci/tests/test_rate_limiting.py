"""Tests for the Dispatcher rate limiter factory."""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from ddev.cli.ci.tests.rate_limiting import RateLimiterConfig, RateLimiterFactory, RateLimiterFactoryConfig

# ---------------------------------------------------------------------------
# RateLimiterConfig field validation
# ---------------------------------------------------------------------------


def test_rate_limiter_config_rejects_zero_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(max_rate=0)


def test_rate_limiter_config_rejects_negative_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(max_rate=-1.0)


def test_rate_limiter_config_rejects_zero_time_period():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(max_rate=10.0, time_period=0)


def test_rate_limiter_config_rejects_negative_time_period():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(max_rate=10.0, time_period=-1.0)


def test_rate_limiter_config_hourly_rate_with_default_period():
    # 360 tokens per 3600s = 360 req/hr
    assert RateLimiterConfig(max_rate=360.0).hourly_rate == pytest.approx(360.0)


def test_rate_limiter_config_hourly_rate_with_custom_period():
    # 6 tokens per 60s = 360 req/hr
    assert RateLimiterConfig(max_rate=6.0, time_period=60.0).hourly_rate == pytest.approx(360.0)


# ---------------------------------------------------------------------------
# RateLimiterFactoryConfig construction validation
# ---------------------------------------------------------------------------


def test_factory_config_raises_when_combined_rate_exceeds_total():
    with pytest.raises(ValidationError, match="exceeds total_hourly_max_rate"):
        RateLimiterFactoryConfig(
            default=RateLimiterConfig(max_rate=800.0),
            slow=RateLimiterConfig(max_rate=800.0),
            total_hourly_max_rate=1500.0,
        )


def test_factory_config_raises_when_combined_rate_exceeds_total_mixed_periods():
    # default: 6 req/min = 360 req/hr, slow: 6 req/min = 360 req/hr, combined = 720 > 500
    with pytest.raises(ValidationError, match="exceeds total_hourly_max_rate"):
        RateLimiterFactoryConfig(
            default=RateLimiterConfig(max_rate=6.0, time_period=60.0),
            slow=RateLimiterConfig(max_rate=6.0, time_period=60.0),
            total_hourly_max_rate=500.0,
        )


def test_factory_config_accepts_combined_rate_at_limit():
    assert RateLimiterFactoryConfig(
        default=RateLimiterConfig(max_rate=750.0),
        slow=RateLimiterConfig(max_rate=750.0),
        total_hourly_max_rate=1500.0,
    )


def test_factory_config_default_is_within_bounds():
    assert RateLimiterFactoryConfig()


def test_factory_config_rejects_negative_total_hourly_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterFactoryConfig(total_hourly_max_rate=-1.0)


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
    assert factory.get_limiter(frozenset({"redis", "postgres_lite"})) is factory.default


def test_get_limiter_returns_slow_for_slow_integration():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo", "mysql"})))
    assert factory.get_limiter(frozenset({"mongo"})) is factory.slow


def test_get_limiter_returns_slow_when_any_integration_is_slow():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo", "mysql"})))
    assert factory.get_limiter(frozenset({"redis", "mysql", "postgres_lite"})) is factory.slow


def test_get_limiter_returns_default_for_empty_integrations():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(slow_integrations=frozenset({"mongo"})))
    assert factory.get_limiter(frozenset()) is factory.default


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


# ---------------------------------------------------------------------------
# shared governor + on_event wiring
# ---------------------------------------------------------------------------


def test_factory_shares_budget_governor_across_both_tiers():
    factory = RateLimiterFactory()

    assert factory.default.budget_governor is factory.slow.budget_governor


def test_factory_shares_on_event_across_governor_and_both_limiters():
    factory = RateLimiterFactory(logger=logging.getLogger("test"))

    assert factory.default.on_event is factory.slow.on_event
    assert factory.default.on_event is factory.default.budget_governor.on_event


def test_factory_uses_distinct_names_for_default_and_slow_limiters():
    factory = RateLimiterFactory()

    assert factory.default.name == "default"
    assert factory.slow.name == "slow"
