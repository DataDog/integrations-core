# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Submission and field-interpretation helpers for Catalyst Center's absent-data conventions.

Catalyst Center signals "no data" four different ways -- `null`, `-1`, `{}`, and the empty
string -- and which one appears depends on the field and the device family. Emitting `0` for
any of them reads as a healthy zero on a graph.

There are two helpers rather than one so that the `-1` rule stays confined to scores. A radio
noise floor is legitimately around -95 dBm, and a blanket sentinel filter would silently drop it.
"""

from __future__ import annotations

from typing import Any

from datadog_checks.base import AgentCheck


def to_number(value: Any) -> float | None:
    """Coerce to a number, accepting numeric strings. Returns None if it is not numeric.

    Public because a caller that has to scale a value needs the number before it can submit it,
    and must not reimplement which shapes count as absent.
    """
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


def emit_gauge(check: AgentCheck, name: str, value: Any, tags: list[str]) -> None:
    """Submit a gauge, skipping absent data. Numeric strings are cast."""
    numeric = to_number(value)
    if numeric is None:
        return
    check.gauge(name, numeric, tags=tags)


def emit_score(check: AgentCheck, name: str, value: Any, tags: list[str]) -> None:
    """Submit a 1-10 health score, additionally treating -1 as absent."""
    numeric = to_number(value)
    if numeric is None or numeric == -1:
        return
    check.gauge(name, numeric, tags=tags)


def emit_watts(check: AgentCheck, name: str, value: Any, tags: list[str]) -> None:
    """Submit a PoE power reading given as a unit-suffixed string such as `"10.5W"`."""
    if not isinstance(value, str):
        emit_gauge(check, name, value, tags)
        return
    emit_gauge(check, name, value.rstrip('Ww').strip(), tags)


def tag(key: str, value: Any) -> str | None:
    """Build a `key:value` tag, or None when there is nothing worth tagging.

    Returning None rather than an empty tag lets callers filter in one place; an empty string
    is one of the values Catalyst Center uses for absent data.
    """
    if value is None or value == '':
        return None
    return f'{key}:{value}'


def compact(tags: list[str | None]) -> list[str]:
    """Drop the Nones produced by `tag()`."""
    return [item for item in tags if item is not None]


def is_uplink(record: dict[str, Any]) -> bool:
    """Whether one merged interface record describes an uplink.

    `isWan` is the appliance's own judgement about which link leaves the site, so it stays
    primary: where it is set, its value decides and the description is never consulted. Much
    hardware leaves it null, and the port description is the fallback for that case.

    The match is deliberately narrow: the substring `uplink`, case-insensitively, and nothing
    else. Treating `core`, `dist`, `trunk` or `portMode` as markers would relabel ordinary trunk
    ports on an access switch and silently inflate the uplink throughput aggregate.

    One rule with three callers -- the `uplink` tag, the device rollup and the NDM port role --
    so they cannot drift apart.
    """
    is_wan = record.get('isWan')
    if is_wan is not None:
        return bool(is_wan)
    return 'uplink' in (record.get('description') or '').lower()
