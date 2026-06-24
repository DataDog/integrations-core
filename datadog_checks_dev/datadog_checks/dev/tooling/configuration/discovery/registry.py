# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

REGISTRY: dict[str, Strategy] = {}


@dataclass
class Strategy:
    name: str
    provides: tuple[str, ...]
    valid_fields: frozenset[str]
    context_fields: dict[str, frozenset[str]]
    generate: Callable[[dict[str, Any], int], list[str]]


def strategy(
    *,
    name: str,
    provides: tuple[str, ...] = (),
    valid_fields: frozenset[str] | None = None,
    context_fields: dict[str, frozenset[str]] | None = None,
) -> Callable:
    """Register a codegen strategy."""

    def decorate(func: Callable[[dict[str, Any], int], list[str]]) -> Callable:
        REGISTRY[name] = Strategy(
            name=name,
            provides=provides,
            valid_fields=valid_fields or frozenset(),
            context_fields=context_fields or {},
            generate=func,
        )
        return func

    return decorate
