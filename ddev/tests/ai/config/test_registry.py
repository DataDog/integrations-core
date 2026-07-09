# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

from ddev.ai.config.models import AgentConfig, FlowConfig, FlowEntry, PhaseConfig
from ddev.ai.config.registry import BrokenEntry, ResourceRegistry, ValidEntry


def test_single_entries_land_in_entry_and_ok_view():
    agent = ValidEntry(kind="agent", name="a", config=AgentConfig(), source_file=Path("/x/a.md"))
    phase = ValidEntry(kind="phase", name="p", config=PhaseConfig(name="p"), source_file=Path("/x/p.yaml"))
    flow = ValidEntry(
        kind="flow",
        name="demo",
        config=FlowConfig(name="demo", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/f.yaml"),
    )
    prompt = ValidEntry(kind="prompt", name="intro", config="body", source_file=Path("/x/intro.md"))
    goal = ValidEntry(kind="goal", name="done", config="goal body", source_file=Path("/x/done.md"))
    memory = ValidEntry(kind="memory_prompt", name="mem", config="mem body", source_file=Path("/x/mem.md"))

    reg = ResourceRegistry([agent, phase, flow, prompt, goal, memory])

    assert reg.entry("agent", "a") is agent
    assert reg.entry("phase", "p") is phase
    assert reg.entry("flow", "demo") is flow
    assert reg.entry("prompt", "intro") is prompt
    assert reg.entry("goal", "done") is goal
    assert reg.entry("memory_prompt", "mem") is memory

    assert reg.agents == {"a": agent.config}
    assert reg.phases == {"p": phase.config}
    assert reg.flows == {"demo": flow.config}
    assert reg.prompts == {"intro": "body"}
    assert reg.goals == {"done": "goal body"}
    assert reg.memories == {"mem": "mem body"}


def test_entry_absent_returns_none():
    reg = ResourceRegistry([])
    assert reg.entry("agent", "missing") is None


def test_broken_entry_excluded_from_ok_view_but_reachable_via_entry():
    broken = BrokenEntry(kind="agent", name="bad", source_file=Path("/x/bad.md"), error="boom")
    reg = ResourceRegistry([broken])

    assert reg.entry("agent", "bad") is broken
    assert reg.agents == {}


def test_conflicting_same_kind_and_name_disabled_everywhere():
    e1 = ValidEntry(kind="agent", name="dup", config=AgentConfig(), source_file=Path("/x/one.md"))
    e2 = ValidEntry(kind="agent", name="dup", config=AgentConfig(), source_file=Path("/x/two.md"))
    reg = ResourceRegistry([e1, e2])

    assert reg.has_conflicts
    assert len(reg.conflicts) == 1
    conflict = reg.conflicts[0]
    assert conflict.kind == "agent"
    assert conflict.name == "dup"
    assert conflict.sources == [Path("/x/one.md"), Path("/x/two.md")]

    assert reg.entry("agent", "dup") is None
    assert reg.agents == {}


def test_cross_type_same_name_coexists_without_conflict():
    agent = ValidEntry(kind="agent", name="x", config=AgentConfig(), source_file=Path("/x/agent.md"))
    flow = ValidEntry(
        kind="flow",
        name="x",
        config=FlowConfig(name="x", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/flow.yaml"),
    )
    reg = ResourceRegistry([agent, flow])

    assert not reg.has_conflicts
    assert reg.entry("agent", "x") is agent
    assert reg.entry("flow", "x") is flow
    assert reg.agents == {"x": agent.config}
    assert reg.flows == {"x": flow.config}


def test_flow_names_includes_valid_and_broken_but_not_conflicting():
    valid_flow = ValidEntry(
        kind="flow",
        name="good",
        config=FlowConfig(name="good", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/good.yaml"),
    )
    broken_flow = BrokenEntry(kind="flow", name="broken", source_file=Path("/x/broken.yaml"), error="oops")
    conflict_a = ValidEntry(
        kind="flow",
        name="dup",
        config=FlowConfig(name="dup", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/dup1.yaml"),
    )
    conflict_b = ValidEntry(
        kind="flow",
        name="dup",
        config=FlowConfig(name="dup", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/dup2.yaml"),
    )

    reg = ResourceRegistry([valid_flow, broken_flow, conflict_a, conflict_b])

    assert set(reg.flow_names) == {"good", "broken"}
    assert "dup" not in reg.flow_names
    assert any(c.kind == "flow" and c.name == "dup" for c in reg.conflicts)


def test_conflict_among_str_body_kinds():
    p1 = ValidEntry(kind="prompt", name="intro", config="v1", source_file=Path("/x/intro1.md"))
    p2 = ValidEntry(kind="prompt", name="intro", config="v2", source_file=Path("/x/intro2.md"))
    reg = ResourceRegistry([p1, p2])

    assert reg.has_conflicts
    assert reg.prompts == {}
    assert reg.entry("prompt", "intro") is None
    conflict = next(c for c in reg.conflicts if c.name == "intro")
    assert conflict.kind == "prompt"
    assert conflict.sources == [Path("/x/intro1.md"), Path("/x/intro2.md")]


def test_conflicts_record_kind_name_and_all_sources():
    e1 = ValidEntry(kind="phase", name="p", config=PhaseConfig(name="p"), source_file=Path("/x/a.yaml"))
    e2 = ValidEntry(kind="phase", name="p", config=PhaseConfig(name="p"), source_file=Path("/x/b.yaml"))
    e3 = ValidEntry(kind="phase", name="p", config=PhaseConfig(name="p"), source_file=Path("/x/c.yaml"))
    reg = ResourceRegistry([e1, e2, e3])

    conflict = reg.conflicts[0]
    assert conflict.kind == "phase"
    assert conflict.name == "p"
    assert conflict.sources == [Path("/x/a.yaml"), Path("/x/b.yaml"), Path("/x/c.yaml")]
