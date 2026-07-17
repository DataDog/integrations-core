# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from ddev.ai.config.errors import ErrorKind
from ddev.ai.config.models import ConfigStatus, FlowEntry, FlowInput, VariableDeclaration
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


def test_explicit_flow_value_resolves_conflicting_defaults():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="model", default="agent-default")]),
        phase_entry("p", agent="writer", variables=[VariableDeclaration(name="model", default="phase-default")]),
        flow_entry("demo", [FlowEntry(phase="p")], variables={"model": "flow-value"}),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert not [e for e in diagnostics.errors if e.kind == ErrorKind.VARIABLE]
    assert diagnostics.resolved.variables == {"model": "flow-value"}


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


def test_required_runtime_input_satisfies_required_variable_without_static_value():
    entries = [
        phase_entry("p", variables=[VariableDeclaration(name="topic")]),
        flow_entry(
            "demo",
            [FlowEntry(phase="p")],
            inputs=[FlowInput(name="topic", label="Topic", input_type="string", required=True)],
        ),
    ]
    diagnostics = FlowResolver(ResourceRegistry(entries), StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.resolved.variables == {}


def test_built_in_prd_input_satisfies_required_variable():
    entries = [
        phase_entry("p", variables=[VariableDeclaration(name="prd")]),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    diagnostics = FlowResolver(ResourceRegistry(entries), StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.resolved.variables == {}


def test_required_runtime_input_resolves_default_conflict_without_static_value():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="topic", default="agent")]),
        phase_entry("p", agent="writer", variables=[VariableDeclaration(name="topic", default="phase")]),
        flow_entry(
            "demo",
            [FlowEntry(phase="p")],
            inputs=[FlowInput(name="topic", label="Topic", input_type="string", required=True)],
        ),
    ]
    diagnostics = FlowResolver(ResourceRegistry(entries), StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.resolved.variables == {}


def test_optional_runtime_input_without_default_does_not_satisfy_required_variable():
    entries = [
        phase_entry("p", variables=[VariableDeclaration(name="topic")]),
        flow_entry(
            "demo",
            [FlowEntry(phase="p")],
            inputs=[FlowInput(name="topic", label="Topic", input_type="string", required=False)],
        ),
    ]
    diagnostics = FlowResolver(ResourceRegistry(entries), StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(error.subject == "topic" and "Required variable" in error.message for error in diagnostics.errors)


def test_optional_runtime_input_without_default_does_not_resolve_default_conflict():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="topic", default="agent")]),
        phase_entry("p", agent="writer", variables=[VariableDeclaration(name="topic", default="phase")]),
        flow_entry(
            "demo",
            [FlowEntry(phase="p")],
            inputs=[FlowInput(name="topic", label="Topic", input_type="string", required=False)],
        ),
    ]
    diagnostics = FlowResolver(ResourceRegistry(entries), StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(error.subject == "topic" and "conflicting defaults" in error.message for error in diagnostics.errors)


def test_defaulted_optional_runtime_input_resolves_variable_without_static_value():
    entries = [
        phase_entry("p", variables=[VariableDeclaration(name="topic")]),
        flow_entry(
            "demo",
            [FlowEntry(phase="p")],
            inputs=[FlowInput(name="topic", label="Topic", input_type="string", required=False, default="metrics")],
        ),
    ]
    diagnostics = FlowResolver(ResourceRegistry(entries), StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.resolved.variables == {}
