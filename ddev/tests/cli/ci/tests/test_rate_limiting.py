"""Tests for the Dispatcher rate limiter factory."""

from __future__ import annotations

import logging

import pytest

from ddev.cli.ci.tests.rate_limiting import RateLimiterConfig, RateLimiterFactory, RateLimiterFactoryConfig

# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_factory_raises_when_combined_rate_exceeds_total():
    config = RateLimiterFactoryConfig(
        default=RateLimiterConfig(max_rate=800.0),
        slow=RateLimiterConfig(max_rate=800.0),
        total_max_rate=1500.0,
    )
    with pytest.raises(ValueError, match="exceeds total_max_rate"):
        RateLimiterFactory(config)


def test_factory_accepts_combined_rate_at_limit():
    config = RateLimiterFactoryConfig(
        default=RateLimiterConfig(max_rate=750.0),
        slow=RateLimiterConfig(max_rate=750.0),
        total_max_rate=1500.0,
    )
    assert RateLimiterFactory(config) is not None


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
