"""Tests for the default GitHub rate-limit protection."""

from __future__ import annotations

import dataclasses
import logging

import pytest

from ddev.utils.github_async.defaults import default_github_rate_limiter, log_rate_limit_events
from ddev.utils.rate_limiting import (
    BudgetSnapshot,
    PacingEvent,
    PacingReason,
    RateLimitEvent,
    SecondaryLimitEvent,
)

LOGGER_NAME = "ddev.utils.github_async.defaults"


async def test_default_github_rate_limiter_wires_callback_into_both_slots() -> None:
    """The factory must wire the callback into both the bucket and the governor slots."""
    seen: list[RateLimitEvent] = []
    limiter = default_github_rate_limiter(on_event=seen.append)

    await limiter.__aenter__()  # bucket acquire -> BucketEvent (limiter slot)
    limiter.observe(BudgetSnapshot(limit=100, remaining=10, reset_at=2000.0))  # observe -> BudgetEvent (governor slot)

    kinds = {type(event).__name__ for event in seen}
    assert "BucketEvent" in kinds  # would be missing if the limiter slot were unwired
    assert "BudgetEvent" in kinds  # would be missing if the governor slot were unwired


@pytest.mark.parametrize(
    ("event", "expected_level"),
    [
        pytest.param(
            SecondaryLimitEvent(retry_after_seconds=5.0, pause_seconds=6.0), logging.WARNING, id="secondary_limit"
        ),
        pytest.param(PacingEvent(wait_seconds=0.0, reason=PacingReason.NONE), logging.DEBUG, id="healthy_pacing"),
        pytest.param(PacingEvent(wait_seconds=3.0, reason=PacingReason.RATIONING), logging.INFO, id="rationing"),
        pytest.param(PacingEvent(wait_seconds=9.0, reason=PacingReason.EXHAUSTED), logging.WARNING, id="exhausted"),
        pytest.param(PacingEvent(wait_seconds=9.0, reason=PacingReason.ABANDONED), logging.ERROR, id="abandoned"),
    ],
)
def test_log_rate_limit_events_level_mapping(
    caplog: pytest.LogCaptureFixture, event: RateLimitEvent, expected_level: int
) -> None:
    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        log_rate_limit_events()(event)

    assert caplog.records
    assert caplog.records[-1].levelno == expected_level


def test_log_rate_limit_events_unknown_event_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    """A future event type must fall through to the DEBUG catch-all, never raise."""

    @dataclasses.dataclass(frozen=True)
    class FutureEvent:
        type: str = "future"

    with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
        log_rate_limit_events()(FutureEvent())  # type: ignore[arg-type]

    assert caplog.records[-1].levelno == logging.DEBUG
