# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from ddev.ai.config.errors import ConfigStatus, ErrorKind
from ddev.ai.config.models import FlowEntry, VariableDeclaration
from ddev.ai.config.registry import ResourceRegistry
from ddev.ai.config.resolving.resolver import FlowResolver

from ..utils import StubReg
from .helpers import agent_entry, flow_entry, phase_entry


def test_required_variable_missing():
    entries = [
        phase_entry("p", variables=[VariableDeclaration(name="var1")]),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.VARIABLE)
    assert error.subject == "var1"
    assert "Required variable" in error.message
    assert "phase 'p'" in error.message


def test_conflicting_defaults_reported_once_with_multiple_sources():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="x", default="A")]),
        phase_entry("p1", agent="writer", variables=[VariableDeclaration(name="x", default="B")]),
        phase_entry("p2", agent="writer", variables=[VariableDeclaration(name="x", default="C")]),
        flow_entry("demo", [FlowEntry(phase="p1"), FlowEntry(phase="p2")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    variable_errors = [e for e in diagnostics.errors if e.kind == ErrorKind.VARIABLE and e.subject == "x"]
    assert len(variable_errors) == 1
    error = variable_errors[0]
    assert "conflicting defaults" in error.message
    assert "agent 'writer'" in error.message
    assert "phase 'p1'" in error.message
    assert len(error.sources) == 3


def test_identical_defaults_coalesce():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="x", default="A")]),
        phase_entry("p1", agent="writer", variables=[VariableDeclaration(name="x", default="A")]),
        flow_entry("demo", [FlowEntry(phase="p1")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.resolved.variables == {"x": "A"}


def test_flow_variable_overrides_default():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="topic", default="cats")]),
        phase_entry("p", agent="writer"),
        flow_entry("demo", [FlowEntry(phase="p")], variables={"topic": "dogs"}),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.resolved.variables == {"topic": "dogs"}
