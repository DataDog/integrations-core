# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Callable, Iterator
from functools import wraps
from typing import Any


def discovery_strategy(*, provides: tuple[str, ...] = ()) -> Callable[[Callable], Callable]:
    """Mark a function as a custom (``local:``) discovery strategy.

    ``provides`` declares the context keys each yielded mapping must contain.
    The decorator validates that each yielded context actually contains those
    keys — turning a silent template-render failure into an explicit error at
    the source.
    """

    def decorate(func: Callable[..., Iterator[dict[str, Any]]]) -> Callable[..., Iterator[dict[str, Any]]]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
            for ctx in func(*args, **kwargs):
                missing = [key for key in provides if key not in ctx]
                if missing:
                    raise ValueError(f"discovery strategy {func.__name__!r} did not provide declared keys: {missing}")
                yield ctx

        return wrapper

    return decorate
