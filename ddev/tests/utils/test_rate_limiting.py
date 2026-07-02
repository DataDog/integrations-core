"""Tests for the generic async rate limiting utilities."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from aiolimiter import AsyncLimiter

from ddev.utils.rate_limiting import InstrumentedAsyncLimiter


async def _assert_blocks(coro, timeout: float = 0.05) -> None:
    """Assert that a coroutine blocks without completing within the timeout."""
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(coro, timeout=timeout)


async def test_instrumented_limiter_calls_on_throttled_when_no_capacity():
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    on_throttled = MagicMock()
    limiter = InstrumentedAsyncLimiter(real_limiter, on_throttled=on_throttled)

    async with limiter:
        pass  # consumes the single token; has_capacity was True, so on_throttled not called

    # on_throttled fires before the coroutine suspends, even though the acquire never completes
    await _assert_blocks(limiter.__aenter__())

    on_throttled.assert_called_once()


async def test_instrumented_limiter_does_not_call_on_throttled_when_capacity_available():
    on_throttled = MagicMock()
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=2, time_period=1000), on_throttled=on_throttled)

    async with limiter:
        pass

    on_throttled.assert_not_called()


async def test_instrumented_limiter_none_callback_does_not_raise():
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter, on_throttled=None)

    async with limiter:
        pass  # drain

    # Entering with an exhausted bucket and on_throttled=None must not raise any exception
    await _assert_blocks(limiter.__aenter__())


async def test_instrumented_limiter_drains_real_bucket():
    """Acquiring through InstrumentedAsyncLimiter must consume a token from the real bucket."""
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter)

    assert real_limiter.has_capacity()
    async with limiter:
        pass
    assert not real_limiter.has_capacity()


async def test_instrumented_limiter_blocks_on_exhausted_bucket():
    """A second acquire on an empty bucket must block, not pass through."""
    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    limiter = InstrumentedAsyncLimiter(real_limiter)

    async with limiter:
        pass  # drain the single token

    await _assert_blocks(limiter.__aenter__())


async def test_instrumented_limiter_calls_on_acquired_after_token_granted():
    on_acquired = MagicMock()
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), on_acquired=on_acquired)

    async with limiter:
        pass

    on_acquired.assert_called_once()


async def test_instrumented_limiter_on_acquired_fires_after_wait():
    on_throttled = MagicMock()
    on_acquired = MagicMock()
    real_limiter = AsyncLimiter(max_rate=1, time_period=0.1)
    limiter = InstrumentedAsyncLimiter(real_limiter, on_throttled=on_throttled, on_acquired=on_acquired)

    async with limiter:
        pass  # drain; on_acquired fires once here

    # Bucket is empty — next acquire blocks until the 0.1s period refills it
    async with limiter:
        pass  # on_throttled fires on entry, on_acquired fires once the wait is over

    on_throttled.assert_called_once()
    assert on_acquired.call_count == 2


async def test_instrumented_limiter_none_on_acquired_does_not_raise():
    limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), on_acquired=None)

    async with limiter:
        pass
