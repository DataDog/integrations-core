# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from ddev.ai.config.engine import ConfigStatus, ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError


class StubReg:
    def contains(self, n):
        return True


class StubRegMissing:
    def __init__(self, missing: set[str]) -> None:
        self._missing = missing

    def contains(self, n):
        return n not in self._missing


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_get_flow_inlines_refs(tmp_path):
    write(tmp_path / "prompts" / "intro.md", "---\ntype: prompt\n---\nDo the thing {{x}}\n")
    write(tmp_path / "prompts" / "mem.md", "---\ntype: memory\n---\nRemember {{x}}\n")
    write(tmp_path / "agents" / "ag.md", "---\ntype: agent\n---\nsys\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: ag\n"
        "    tasks:\n      - name: t\n        prompt_ref: intro\n"
        "    checkpoint:\n      memory_prompt_ref: mem\n"
        "- type: flow\n  config:\n    name: demo\n    variables:\n      x: hi\n"
        "    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    rf = eng.get_flow("demo")
    t = rf.phases["p"].tasks[0]
    assert t.prompt == "Do the thing {{x}}" and t.prompt_ref is None
    assert rf.phases["p"].checkpoint.memory_prompt == "Remember {{x}}"
    assert rf.variables == {"x": "hi"}


def test_inlines_both_prompt_and_goal_refs(tmp_path):
    write(tmp_path / "prompts" / "intro.md", "---\ntype: prompt\n---\nprompt body\n")
    write(tmp_path / "prompts" / "g.md", "---\ntype: goal\n---\ngoal body\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    tasks:\n      - name: t\n        prompt_ref: intro\n        goal_ref: g\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    rf = eng.get_flow("demo")
    t = rf.phases["p"].tasks[0]
    assert t.prompt == "prompt body" and t.prompt_ref is None
    assert t.goal == "goal body" and t.goal_ref is None


def test_unknown_phase_ref_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: missing\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status.value == "broken"
    assert any("missing" in e for e in eng.flows["demo"].errors)
    with pytest.raises(FlowConfigError):
        eng.get_flow("demo")


def test_unknown_class_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    class: Bogus\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubRegMissing({"Bogus"}))
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("Bogus" in e for e in eng.flows["demo"].errors)


def test_missing_agent_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: nope\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("nope" in e for e in eng.flows["demo"].errors)


def test_missing_prompt_ref_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    tasks:\n      - name: t\n        prompt_ref: nope\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("nope" in e for e in eng.flows["demo"].errors)


def test_missing_goal_ref_accumulates(tmp_path):
    write(tmp_path / "prompts" / "intro.md", "---\ntype: prompt\n---\nbody\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    tasks:\n      - name: t\n        prompt_ref: intro\n        goal_ref: nope\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("nope" in e for e in eng.flows["demo"].errors)


def test_missing_memory_prompt_ref_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    checkpoint:\n      memory_prompt_ref: nope\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("nope" in e for e in eng.flows["demo"].errors)


def test_dependency_not_scheduled_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: p\n        dependencies:\n          - ghost\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("ghost" in e for e in eng.flows["demo"].errors)


def test_duplicate_phase_in_flow_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: p\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("p" in e for e in eng.flows["demo"].errors)


def test_cycle_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: a\n"
        "- type: phase\n  config:\n    name: b\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: a\n        dependencies:\n          - b\n"
        "      - phase: b\n        dependencies:\n          - a\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("cycle" in e.lower() for e in eng.flows["demo"].errors)


def test_conflict_touching_flow_surfaces(tmp_path):
    user_dir = tmp_path / "user"
    write(
        tmp_path / "core" / "f1.yaml",
        "- type: phase\n  config:\n    name: p\n- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    write(
        user_dir / "a.yaml",
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    write(
        user_dir / "b.yaml",
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path / "core", user_dirs=[str(user_dir)], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    with pytest.raises(FlowConfigError):
        eng.get_flow("demo")


def test_missing_required_variable_accumulates(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    variables:\n      - name: x\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("x" in e for e in eng.flows["demo"].errors)


def test_conflicting_default_accumulates(tmp_path):
    write(tmp_path / "agents" / "ag.md", "---\ntype: agent\nvariables:\n  - name: x\n    default: A\n---\nsys\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: ag\n"
        "    variables:\n      - name: x\n        default: B\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("x" in e for e in eng.flows["demo"].errors)


def test_flow_value_overrides_default(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    variables:\n      - name: x\n        default: A\n"
        "- type: flow\n  config:\n    name: demo\n    variables:\n      x: override\n"
        "    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    rf = eng.get_flow("demo")
    assert rf.variables == {"x": "override"}


def test_identical_defaults_coalesce(tmp_path):
    write(tmp_path / "agents" / "ag.md", "---\ntype: agent\nvariables:\n  - name: x\n    default: same\n---\nsys\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: ag\n"
        "    variables:\n      - name: x\n        default: same\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    rf = eng.get_flow("demo")
    assert rf.variables == {"x": "same"}


def test_flows_overview_populated_without_get_flow(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert "demo" in eng.flows
    assert eng.flows["demo"].status == ConfigStatus.OK


def test_get_flow_unknown_name_raises(tmp_path):
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    with pytest.raises(FlowConfigError):
        eng.get_flow("nope")
