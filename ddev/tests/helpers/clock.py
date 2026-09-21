import asyncio

import pytest


class FakeClock:
    """Injectable, manually-advanceable clock for deterministic time in async tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def advance_clock_on_sleep(clock: FakeClock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make asyncio.sleep advance the fake clock instead of blocking, so timed waits are instant."""

    async def fake_sleep(delay: float) -> None:
        clock.advance(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
