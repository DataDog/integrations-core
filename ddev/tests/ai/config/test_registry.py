# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

from ddev.ai.config.models import AgentConfig, FlowConfig, FlowEntry, PhaseConfig
from ddev.ai.config.registry import BrokenEntry, ResourceKind, ResourceRegistry, ValidEntry


def test_single_entries_land_in_entry_and_ok_view():
    agent = ValidEntry(kind=ResourceKind.AGENT, name="a", config=AgentConfig(), source_file=Path("/x/a.md"))
    phase = ValidEntry(kind=ResourceKind.PHASE, name="p", config=PhaseConfig(name="p"), source_file=Path("/x/p.yaml"))
    flow = ValidEntry(
        kind=ResourceKind.FLOW,
        name="demo",
        config=FlowConfig(name="demo", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/f.yaml"),
    )
    prompt = ValidEntry(kind=ResourceKind.PROMPT, name="intro", config="body", source_file=Path("/x/intro.md"))
    goal = ValidEntry(kind=ResourceKind.GOAL, name="done", config="goal body", source_file=Path("/x/done.md"))
    memory = ValidEntry(kind=ResourceKind.MEMORY_PROMPT, name="mem", config="mem body", source_file=Path("/x/mem.md"))

    reg = ResourceRegistry([agent, phase, flow, prompt, goal, memory])

    assert reg.entry(ResourceKind.AGENT, "a") is agent
    assert reg.entry(ResourceKind.PHASE, "p") is phase
    assert reg.entry(ResourceKind.FLOW, "demo") is flow
    assert reg.entry(ResourceKind.PROMPT, "intro") is prompt
    assert reg.entry(ResourceKind.GOAL, "done") is goal
    assert reg.entry(ResourceKind.MEMORY_PROMPT, "mem") is memory

    assert reg.agents == {"a": agent.config}
    assert reg.phases == {"p": phase.config}
    assert reg.flows == {"demo": flow.config}
    assert reg.prompts == {"intro": "body"}
    assert reg.goals == {"done": "goal body"}
    assert reg.memories == {"mem": "mem body"}


def test_entry_absent_returns_none():
    reg = ResourceRegistry([])
    assert reg.entry(ResourceKind.AGENT, "missing") is None


def test_broken_entry_excluded_from_ok_view_but_reachable_via_entry():
    broken = BrokenEntry(kind=ResourceKind.AGENT, name="bad", source_file=Path("/x/bad.md"), error="boom")
    reg = ResourceRegistry([broken])

    assert reg.entry(ResourceKind.AGENT, "bad") is broken
    assert reg.agents == {}


def test_conflicting_same_kind_and_name_disabled_everywhere():
    e1 = ValidEntry(kind=ResourceKind.AGENT, name="dup", config=AgentConfig(), source_file=Path("/x/one.md"))
    e2 = ValidEntry(kind=ResourceKind.AGENT, name="dup", config=AgentConfig(), source_file=Path("/x/two.md"))
    reg = ResourceRegistry([e1, e2])

    assert reg.has_conflicts
    assert len(reg.conflicts) == 1
    conflict = reg.conflicts[0]
    assert conflict.kind == ResourceKind.AGENT
    assert conflict.name == "dup"
    assert conflict.sources == [Path("/x/one.md"), Path("/x/two.md")]

    assert reg.entry(ResourceKind.AGENT, "dup") is None
    assert reg.agents == {}


def test_cross_type_same_name_coexists_without_conflict():
    agent = ValidEntry(kind=ResourceKind.AGENT, name="x", config=AgentConfig(), source_file=Path("/x/agent.md"))
    flow = ValidEntry(
        kind=ResourceKind.FLOW,
        name="x",
        config=FlowConfig(name="x", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/flow.yaml"),
    )
    reg = ResourceRegistry([agent, flow])

    assert not reg.has_conflicts
    assert reg.entry(ResourceKind.AGENT, "x") is agent
    assert reg.entry(ResourceKind.FLOW, "x") is flow
    assert reg.agents == {"x": agent.config}
    assert reg.flows == {"x": flow.config}


def test_flow_names_includes_valid_and_broken_but_not_conflicting():
    valid_flow = ValidEntry(
        kind=ResourceKind.FLOW,
        name="good",
        config=FlowConfig(name="good", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/good.yaml"),
    )
    broken_flow = BrokenEntry(kind=ResourceKind.FLOW, name="broken", source_file=Path("/x/broken.yaml"), error="oops")
    conflict_a = ValidEntry(
        kind=ResourceKind.FLOW,
        name="dup",
        config=FlowConfig(name="dup", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/dup1.yaml"),
    )
    conflict_b = ValidEntry(
        kind=ResourceKind.FLOW,
        name="dup",
        config=FlowConfig(name="dup", flow=[FlowEntry(phase="p")]),
        source_file=Path("/x/dup2.yaml"),
    )

    reg = ResourceRegistry([valid_flow, broken_flow, conflict_a, conflict_b])

    assert set(reg.flow_names) == {"good", "broken"}
    assert "dup" not in reg.flow_names
    assert any(c.kind == ResourceKind.FLOW and c.name == "dup" for c in reg.conflicts)


def test_conflict_among_str_body_kinds():
    p1 = ValidEntry(kind=ResourceKind.PROMPT, name="intro", config="v1", source_file=Path("/x/intro1.md"))
    p2 = ValidEntry(kind=ResourceKind.PROMPT, name="intro", config="v2", source_file=Path("/x/intro2.md"))
    reg = ResourceRegistry([p1, p2])

    assert reg.has_conflicts
    assert reg.prompts == {}
    assert reg.entry(ResourceKind.PROMPT, "intro") is None
    conflict = next(c for c in reg.conflicts if c.name == "intro")
    assert conflict.kind == ResourceKind.PROMPT
    assert conflict.sources == [Path("/x/intro1.md"), Path("/x/intro2.md")]


def test_conflicts_record_kind_name_and_all_sources():
    e1 = ValidEntry(kind=ResourceKind.PHASE, name="p", config=PhaseConfig(name="p"), source_file=Path("/x/a.yaml"))
    e2 = ValidEntry(kind=ResourceKind.PHASE, name="p", config=PhaseConfig(name="p"), source_file=Path("/x/b.yaml"))
    e3 = ValidEntry(kind=ResourceKind.PHASE, name="p", config=PhaseConfig(name="p"), source_file=Path("/x/c.yaml"))
    reg = ResourceRegistry([e1, e2, e3])

    conflict = reg.conflicts[0]
    assert conflict.kind == ResourceKind.PHASE
    assert conflict.name == "p"
    assert conflict.sources == [Path("/x/a.yaml"), Path("/x/b.yaml"), Path("/x/c.yaml")]
