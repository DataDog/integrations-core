# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

from ddev.ai.config.errors import ConfigStatus, ErrorKind
from ddev.ai.config.models import CheckpointConfig, FlowEntry, TaskConfig, VariableDeclaration
from ddev.ai.config.registry import BrokenEntry, ResourceKind, ResourceRegistry
from ddev.ai.config.resolving.resolver import FlowResolver

from ..utils import StubReg
from .helpers import agent_entry, flow_entry, goal_entry, memory_entry, phase_entry, prompt_entry


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


def test_flow_not_found_is_broken():
    registry = ResourceRegistry([])
    diagnostics = FlowResolver(registry, StubReg()).resolve("nope")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.FLOW)
    assert error.subject == "nope"
    assert "not found" in error.message.lower()


def test_broken_flow_entry_is_broken():
    broken = BrokenEntry(kind=ResourceKind.FLOW, name="demo", source_file=Path("/x/f.yaml"), error="bad flow")
    registry = ResourceRegistry([broken])
    diagnostics = FlowResolver(registry, StubReg()).resolve("demo")

    assert diagnostics.status == ConfigStatus.BROKEN
    error = next(e for e in diagnostics.errors if e.kind == ErrorKind.FLOW)
    assert "bad flow" in error.message
    assert error.sources == [Path("/x/f.yaml")]
