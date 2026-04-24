# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Awaitable, Callable, Sequence
from typing import Any


async def dispatch(
    handlers: Sequence[Callable[..., Awaitable[None]]],
    *args: Any,
) -> None:
    """Fire every handler with the same args; swallow Exception individually.

    Handler signatures are enforced one level up by the per-event Protocol
    classes, so this loose type only describes the dispatch contract, not
    the handler contract.
    """
    for handler in handlers:
        try:
            await handler(*args)
        except Exception:
            pass
