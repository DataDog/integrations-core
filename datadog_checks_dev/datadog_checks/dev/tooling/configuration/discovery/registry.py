# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Field names of the runtime datadog_checks.base.utils.discovery.Service and Port
# pydantic models. datadog_checks_dev never imports datadog_checks_base, so these
# are the single source of truth on the dev side and are guarded by a base unit
# test (datadog_checks_base/tests/base/utils/discovery/test_discovery.py) that
# asserts they match the actual models, so they cannot silently drift.
SERVICE_FIELDS = frozenset({'id', 'host', 'ports'})
PORT_FIELDS = frozenset({'number', 'name'})


@dataclass(frozen=True)
class Input:
    """A declared strategy input, validated against the spec stanza."""

    type: str  # "array[int]" | "string" | "integer" | "boolean"
    required: bool = True


@dataclass(frozen=True)
class Strategy:
    name: str
    provides: tuple[str, ...]  # context keys injected into templates, e.g. ("port",)
    inputs: dict[str, Input] = field(default_factory=dict)  # accepted stanza keys (besides `candidates`)
    runtime_imports: tuple[str, ...] = ()  # import lines added to the generated discovery.py
    # stanza -> code lines that open the per-candidate loop and bind a `ctx` dict
    emit_context: Callable[[dict[str, Any]], list[str]] = lambda stanza: []


REGISTRY: dict[str, Strategy] = {}


def strategy(
    name: str,
    *,
    provides: tuple[str, ...] = (),
    inputs: dict[str, Input] | None = None,
    runtime_imports: tuple[str, ...] = (),
) -> Callable[[Callable[[dict[str, Any]], list[str]]], Callable[[dict[str, Any]], list[str]]]:
    """Register a core discovery strategy.

    The decorated function is the codegen: it receives the resolved strategy
    stanza and returns the Python lines that open the per-candidate loop and bind
    a `ctx` dict exposing the declared `provides`.
    """

    def decorate(emit_context: Callable[[dict[str, Any]], list[str]]) -> Callable[[dict[str, Any]], list[str]]:
        REGISTRY[name] = Strategy(name, tuple(provides), inputs or {}, tuple(runtime_imports), emit_context)
        return emit_context

    return decorate
