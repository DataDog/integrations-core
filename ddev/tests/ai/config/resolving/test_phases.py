# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

from ddev.ai.config.errors import ErrorKind
from ddev.ai.config.models import CheckpointConfig, ConfigStatus, FlowEntry, TaskConfig
from ddev.ai.config.registry import BrokenEntry, ResourceKind, ResourceRegistry
from ddev.ai.config.resolving.resolver import FlowResolver

from ..utils import StubReg, StubRegMissing
from .helpers import StubRegRaising, agent_entry, flow_entry, phase_entry, prompt_entry


def test_unknown_phase_ref():
    entries = [flow_entry("demo", [FlowEntry(phase="missing")])]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.PHASE and e.subject == "missing" for e in diagnostics.errors)


def test_unknown_implementation_class():
    entries = [
        phase_entry("p"),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubRegMissing({"AgenticPhase"})).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.PHASE and e.subject == "AgenticPhase" for e in diagnostics.errors)


def test_missing_agent():
    entries = [
        phase_entry("p", agent="ghost"),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.AGENT and e.subject == "ghost" for e in diagnostics.errors)


def test_missing_prompt_ref():
    entries = [
        phase_entry("p", tasks=[TaskConfig(name="t1", prompt_ref="nope")]),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.PROMPT and e.subject == "nope" for e in diagnostics.errors)


def test_missing_goal_ref():
    entries = [
        phase_entry("p", tasks=[TaskConfig(name="t1", prompt="hi", goal_ref="nope")]),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.GOAL and e.subject == "nope" for e in diagnostics.errors)


def test_missing_memory_prompt_ref():
    entries = [
        phase_entry("p", checkpoint=CheckpointConfig(memory_prompt_ref="nope")),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    assert any(e.kind == ErrorKind.MEMORY_PROMPT and e.subject == "nope" for e in diagnostics.errors)


def test_broken_phase_entry_referenced():
    broken = BrokenEntry(kind=ResourceKind.PHASE, name="p", source_file=Path("/x/p.yaml"), error="parse failure")
    entries = [broken, flow_entry("demo", [FlowEntry(phase="p")])]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.PHASE)
    assert error.subject == "p"
    assert "parse failure" in error.message
    assert error.sources == [Path("/x/p.yaml")]


def test_broken_agent_entry_referenced():
    broken_agent = BrokenEntry(
        kind=ResourceKind.AGENT, name="writer", source_file=Path("/x/agent.md"), error="bad agent"
    )
    entries = [
        broken_agent,
        phase_entry("p", agent="writer"),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.AGENT)
    assert error.subject == "writer"
    assert "bad agent" in error.message
    assert error.sources == [Path("/x/agent.md")]


def test_phase_class_validate_config_raises_non_flow_config_error():
    entries = [
        phase_entry("p"),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubRegRaising()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.PHASE)
    assert "boom" in error.message


def test_phase_referenced_via_conflict():
    conflict_a = phase_entry("conflict_phase", path="/x/a.yaml")
    conflict_b = phase_entry("conflict_phase", path="/x/b.yaml")
    entries = [conflict_a, conflict_b, flow_entry("demo", [FlowEntry(phase="conflict_phase")])]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.PHASE)
    assert "conflicting definitions" in error.message
    assert set(error.sources) == {Path("/x/a.yaml"), Path("/x/b.yaml")}


def test_conflicting_agent_referenced_reports_conflict():
    entries = [
        agent_entry("writer", path="/x/a.md"),
        agent_entry("writer", path="/x/b.md"),
        phase_entry("p", agent="writer"),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.AGENT and e.subject == "writer")
    assert "conflicting definitions" in error.message
    assert set(error.sources) == {Path("/x/a.md"), Path("/x/b.md")}


def test_conflicting_prompt_ref_reports_conflict():
    entries = [
        prompt_entry("intro", "a", path="/x/a.md"),
        prompt_entry("intro", "b", path="/x/b.md"),
        phase_entry("p", tasks=[TaskConfig(name="t1", prompt_ref="intro")]),
        flow_entry("demo", [FlowEntry(phase="p")]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.PROMPT and e.subject == "intro")
    assert "conflicting definitions" in error.message
    assert set(error.sources) == {Path("/x/a.md"), Path("/x/b.md")}
