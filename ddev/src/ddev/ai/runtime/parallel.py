# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from ddev.ai.errors import RunAbortError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Iterable


async def gather_until_run_abort[T](work: Iterable[Callable[[], Awaitable[T]]]) -> list[T | BaseException]:
    """Collect results in input order, canceling siblings on a run-aborting error."""

    async def run(item: Callable[[], Awaitable[T]]) -> T | BaseException:
        try:
            return await item()
        except RunAbortError:
            raise
        except (Exception, asyncio.CancelledError) as error:
            return error

    tasks = [asyncio.create_task(run(item)) for item in work]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
