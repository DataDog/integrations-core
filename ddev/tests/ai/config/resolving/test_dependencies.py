# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from ddev.ai.config.errors import ErrorKind
from ddev.ai.config.models import ConfigStatus, FlowEntry
from ddev.ai.config.registry import ResourceRegistry
from ddev.ai.config.resolving.resolver import FlowResolver

from ..utils import StubReg
from .helpers import flow_entry, phase_entry


def test_dependency_not_scheduled():
    entries = [
        phase_entry("p"),
        flow_entry("demo", [FlowEntry(phase="p", dependencies=["missing_dep"])]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.DEPENDENCY and e.subject == "missing_dep" for e in diagnostics.errors)


def test_duplicate_phase_in_flow():
    entries = [
        phase_entry("p"),
        flow_entry("demo", [FlowEntry(phase="p"), FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.DEPENDENCY and e.subject == "p" for e in diagnostics.errors)


def test_dependency_cycle_detected():
    entries = [
        phase_entry("a"),
        phase_entry("b"),
        flow_entry(
            "demo",
            [FlowEntry(phase="a", dependencies=["b"]), FlowEntry(phase="b", dependencies=["a"])],
        ),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.DEPENDENCY)
    assert "cycle" in error.message.lower()
