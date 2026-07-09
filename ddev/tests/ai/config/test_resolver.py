# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

from ddev.ai.config.errors import ConfigStatus, ErrorKind
from ddev.ai.config.models import (
    AgentConfig,
    CheckpointConfig,
    FlowConfig,
    FlowEntry,
    PhaseConfig,
    TaskConfig,
    VariableDeclaration,
)
from ddev.ai.config.registry import BrokenEntry, ResourceRegistry, ValidEntry
from ddev.ai.config.resolver import FlowResolver

from .utils import StubReg, StubRegMissing


class RaisingPhase:
    @classmethod
    def validate_config(cls, phase_id, config):
        raise ValueError("boom")


class StubRegRaising:
    def contains(self, n):
        return True

    def get(self, n):
        return RaisingPhase

    def format_import_errors(self):
        return ""


def agent_entry(name: str, path: str = "/x/agent.md", **kwargs) -> ValidEntry:
    return ValidEntry(kind="agent", name=name, config=AgentConfig(**kwargs), source_file=Path(path))


def phase_entry(name: str, path: str | None = None, **kwargs) -> ValidEntry:
    source_file = Path(path or f"/x/{name}.yaml")
    return ValidEntry(kind="phase", name=name, config=PhaseConfig(name=name, **kwargs), source_file=source_file)


def flow_entry(name: str, entries: list[FlowEntry], path: str = "/x/flow.yaml", **kwargs) -> ValidEntry:
    config = FlowConfig(name=name, flow=entries, **kwargs)
    return ValidEntry(kind="flow", name=name, config=config, source_file=Path(path))


def prompt_entry(name: str, body: str, path: str | None = None) -> ValidEntry:
    return ValidEntry(kind="prompt", name=name, config=body, source_file=Path(path or f"/x/{name}.md"))


def goal_entry(name: str, body: str, path: str | None = None) -> ValidEntry:
    return ValidEntry(kind="goal", name=name, config=body, source_file=Path(path or f"/x/{name}.md"))


def memory_entry(name: str, body: str, path: str | None = None) -> ValidEntry:
    return ValidEntry(kind="memory_prompt", name=name, config=body, source_file=Path(path or f"/x/{name}.md"))


def test_happy_path_resolves_and_inlines():
    entries = [
        agent_entry("writer", variables=[VariableDeclaration(name="topic", default="cats")]),
        phase_entry(
            "p",
            agent="writer",
            tasks=[TaskConfig(name="t1", prompt_ref="intro", goal_ref="done")],
            checkpoint=CheckpointConfig(memory_prompt_ref="mem"),
        ),
        flow_entry("demo", [FlowEntry(phase="p")]),
        prompt_entry("intro", "intro body"),
        goal_entry("done", "goal body"),
        memory_entry("mem", "mem body"),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.OK
    assert diagnostics.errors == []
    resolved = diagnostics.resolved
    assert resolved is not None
    assert resolved.agents == {"writer": registry.agents["writer"]}
    assert [fe.phase for fe in resolved.flow] == ["p"]
    assert resolved.variables == {"topic": "cats"}

    task = resolved.phases["p"].tasks[0]
    assert task.prompt == "intro body"
    assert task.prompt_ref is None
    assert task.goal == "goal body"
    assert task.goal_ref is None
    assert resolved.phases["p"].checkpoint.memory_prompt == "mem body"
    assert resolved.phases["p"].checkpoint.memory_prompt_ref is None


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
    broken = BrokenEntry(kind="phase", name="p", source_file=Path("/x/p.yaml"), error="parse failure")
    entries = [broken, flow_entry("demo", [FlowEntry(phase="p")])]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.PHASE)
    assert error.subject == "p"
    assert "parse failure" in error.message
    assert error.sources == [Path("/x/p.yaml")]


def test_broken_agent_entry_referenced():
    broken_agent = BrokenEntry(kind="agent", name="writer", source_file=Path("/x/agent.md"), error="bad agent")
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


def test_accumulates_all_errors_in_one_pass():
    entries = [
        phase_entry("p1", agent="ghost", tasks=[TaskConfig(name="t1", prompt_ref="nope")]),
        flow_entry("demo", [FlowEntry(phase="p1", dependencies=["missing_dep"])]),
    ]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    kinds = {e.kind for e in diagnostics.errors}
    assert {ErrorKind.AGENT, ErrorKind.PROMPT, ErrorKind.DEPENDENCY} <= kinds
    assert len(diagnostics.errors) >= 3


def test_phase_referenced_via_conflict():
    conflict_a = phase_entry("conflict_phase", path="/x/a.yaml")
    conflict_b = phase_entry("conflict_phase", path="/x/b.yaml")
    entries = [conflict_a, conflict_b, flow_entry("demo", [FlowEntry(phase="conflict_phase")])]
    registry = ResourceRegistry(entries)
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.PHASE)
    assert "conflict" in error.message.lower()
    assert set(error.sources) == {Path("/x/a.yaml"), Path("/x/b.yaml")}
