# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Generic async rate limiting utilities."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from aiolimiter import AsyncLimiter

RATE_LIMIT_TIME_PERIOD = 3600.0  # 1 hour — matches GitHub's rate limit window


class InstrumentedAsyncLimiter:
    """Thin async context manager wrapper around AsyncLimiter.

    Fires an optional callback when a request has to wait for capacity,
    allowing callers to log or emit metrics on throttling events.
    """

    def __init__(
        self,
        limiter: AsyncLimiter,
        on_throttled: Callable[[], None] | None = None,
        on_acquired: Callable[[], None] | None = None,
    ) -> None:
        self._limiter = limiter
        self._on_throttled = on_throttled or (lambda: None)
        self._on_acquired = on_acquired or (lambda: None)

    async def __aenter__(self) -> InstrumentedAsyncLimiter:
        if not self._limiter.has_capacity():
            self._on_throttled()
        await self._limiter.__aenter__()
        self._on_acquired()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._limiter.__aexit__(exc_type, exc_val, exc_tb)
