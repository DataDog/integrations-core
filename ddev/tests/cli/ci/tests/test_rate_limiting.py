"""Tests for the Dispatcher rate limiter factory."""

from __future__ import annotations

import asyncio
import logging
from functools import partial

import pytest
from pydantic import ValidationError

from ddev.cli.ci.tests import rate_limiting
from ddev.cli.ci.tests.rate_limiting import RateLimiterConfig, RateLimiterFactory, RateLimiterFactoryConfig
from ddev.utils.rate_limiting import BudgetGovernor, BudgetSnapshot
from tests.helpers.clock import FakeClock, advance_clock_on_sleep

# ---------------------------------------------------------------------------
# RateLimiterConfig field validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        pytest.param({"max_rate": 0}, id="zero-max-rate"),
        pytest.param({"max_rate": -1.0}, id="negative-max-rate"),
        pytest.param({"max_rate": 10.0, "time_period": 0}, id="zero-time-period"),
        pytest.param({"max_rate": 10.0, "time_period": -1.0}, id="negative-time-period"),
    ],
)
def test_rate_limiter_config_rejects_a_non_positive_rate(kwargs: dict):
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        # 360 tokens per 3600s and 6 per 60s are the same hourly budget, which is the unit the
        # combined-rate check compares against.
        pytest.param({"max_rate": 360.0}, id="default-period"),
        pytest.param({"max_rate": 6.0, "time_period": 60.0}, id="custom-period"),
    ],
)
def test_rate_limiter_config_normalizes_its_rate_to_an_hourly_one(kwargs: dict):
    assert RateLimiterConfig(**kwargs).hourly_rate == pytest.approx(360.0)


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
    # 360 + 360 + 600 = 1320 requests/hour, above the shared budget.
    with pytest.raises(ValidationError, match="exceeds total_hourly_max_rate"):
        RateLimiterFactoryConfig(
            default=RateLimiterConfig(max_rate=6.0, time_period=60.0),
            slow=RateLimiterConfig(max_rate=6.0, time_period=60.0),
            artifacts=RateLimiterConfig(max_rate=10.0, time_period=60.0),
            total_hourly_max_rate=1300.0,
        )


def test_factory_config_accepts_combined_rate_at_limit():
    """The boundary is inclusive, so a config that exactly spends the budget is legal."""
    assert RateLimiterFactoryConfig(
        default=RateLimiterConfig(max_rate=360.0),
        slow=RateLimiterConfig(max_rate=120.0),
        artifacts=RateLimiterConfig(max_rate=17.0, time_period=60.0),
        total_hourly_max_rate=1500.0,
    )


def test_factory_config_rejects_an_artifact_tier_that_overspends_the_budget():
    with pytest.raises(ValidationError, match="exceeds total_hourly_max_rate"):
        RateLimiterFactoryConfig(artifacts=RateLimiterConfig(max_rate=18.0, time_period=60.0))


def test_factory_config_defaults_satisfy_their_own_combined_rate_check():
    """The shipped defaults must not be a config the validator would reject."""
    assert RateLimiterFactoryConfig()


def test_factory_config_rejects_negative_total_hourly_max_rate():
    with pytest.raises(ValidationError, match="greater than 0"):
        RateLimiterFactoryConfig(total_hourly_max_rate=-1.0)


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


@pytest.mark.parametrize(
    "sender, receiver", [("artifacts", "default"), ("default", "artifacts"), ("artifacts", "slow")]
)
async def test_a_provider_pause_applies_across_tiers(
    sender: str, receiver: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    monkeypatch.setattr(rate_limiting, "BudgetGovernor", partial(BudgetGovernor, now=clock))
    factory = RateLimiterFactory(logger=logging.getLogger("test-factory"))
    started = clock.current

    with caplog.at_level(logging.DEBUG, logger="test-factory"):
        getattr(factory, sender).observe(BudgetSnapshot(retry_after=5))
        async with getattr(factory, receiver):
            admitted = clock.current

    assert admitted >= started + 5
    assert "secondary rate limit" in caplog.text


async def test_artifacts_can_proceed_when_the_polling_allowance_is_spent():
    factory = RateLimiterFactory(RateLimiterFactoryConfig(default=RateLimiterConfig(max_rate=1)))
    async with factory.default:
        pass

    async with asyncio.timeout(5), factory.artifacts:
        pass
