# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Submission helpers that know which absent-data conventions Catalyst Center uses.

Catalyst Center signals "no data" four different ways -- ``null``, ``-1``, ``{}``, and the empty
string -- and which one appears depends on the field and the device family. Emitting ``0`` for
any of them reads as a healthy zero on a graph.

There are two helpers rather than one so that the ``-1`` rule stays confined to scores. A radio
noise floor is legitimately around -95 dBm, and a blanket sentinel filter would silently drop it.
"""

from __future__ import annotations

from typing import Any


def _numeric(value: Any) -> float | None:
    """Coerce to a number, accepting numeric strings. Returns None if it is not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def emit_gauge(check: Any, name: str, value: Any, tags: list[str]) -> None:
    """Submit a gauge, skipping absent data. Numeric strings are cast."""
    numeric = _numeric(value)
    if numeric is None:
        return
    check.gauge(name, numeric, tags=tags)


def emit_score(check: Any, name: str, value: Any, tags: list[str]) -> None:
    """Submit a 1-10 health score, additionally treating -1 as absent."""
    numeric = _numeric(value)
    if numeric is None or numeric == -1:
        return
    check.gauge(name, numeric, tags=tags)


def emit_watts(check: Any, name: str, value: Any, tags: list[str]) -> None:
    """Submit a PoE power reading given as a unit-suffixed string such as ``"10.5W"``."""
    if not isinstance(value, str):
        emit_gauge(check, name, value, tags)
        return
    emit_gauge(check, name, value.rstrip('Ww').strip(), tags)


def tag(key: str, value: Any) -> str | None:
    """Build a ``key:value`` tag, or None when there is nothing worth tagging.

    Returning None rather than an empty tag lets callers filter in one place; an empty string
    is one of the values Catalyst Center uses for absent data.
    """
    if value is None or value == '':
        return None
    return f'{key}:{value}'


def compact(tags: list[str | None]) -> list[str]:
    """Drop the Nones produced by :func:`tag`."""
    return [item for item in tags if item is not None]
