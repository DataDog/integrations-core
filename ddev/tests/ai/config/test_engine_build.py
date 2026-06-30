# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from ddev.ai.config.engine import ConfigStatus, ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError


class NoopPhase:
    @classmethod
    def validate_config(cls, phase_id, config, agents):
        return None


class StubReg:
    def contains(self, n):
        return True

    def get(self, n):
        return NoopPhase


class StubRegMissing:
    def __init__(self, missing: set[str]) -> None:
        self._missing = missing

    def contains(self, n):
        return n not in self._missing

    def get(self, n):
        return NoopPhase


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_get_flow_resolves_all_refs_and_variables(tmp_path):
    write(tmp_path / "agents" / "ag.md", "---\ntype: agent\n---\nsys\n")
    write(tmp_path / "prompts" / "intro.md", "---\ntype: prompt\n---\nDo the thing {{x}}\n")
    write(tmp_path / "prompts" / "g.md", "---\ntype: goal\n---\ngoal body\n")
    write(tmp_path / "prompts" / "mem.md", "---\ntype: memory\n---\nRemember {{x}}\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: ag\n"
        "    tasks:\n      - name: t\n        prompt_ref: intro\n        goal_ref: g\n"
        "    checkpoint:\n      memory_prompt_ref: mem\n"
        "- type: flow\n  config:\n    name: demo\n    variables:\n      x: hi\n"
        "    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    rf = eng.get_flow("demo")

    task = rf.phases["p"].tasks[0]
    # prompt and goal both inlined on the same task; refs cleared; {{x}} left literal
    assert task.prompt == "Do the thing {{x}}"
    assert task.prompt_ref is None
    assert task.goal == "goal body"
    assert task.goal_ref is None

    checkpoint = rf.phases["p"].checkpoint
    assert checkpoint.memory_prompt == "Remember {{x}}"
    assert checkpoint.memory_prompt_ref is None

    assert rf.variables == {"x": "hi"}

    assert "ag" in rf.agents
    assert rf.agents["ag"].system_prompt == "sys"


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


def real_phase_registry():
    from ddev.ai.constants import CORE_PHASES_DIR, CORE_PHASES_PACKAGE
    from ddev.ai.phases.registry import PhaseRegistry

    registry = PhaseRegistry()
    registry.register_from(CORE_PHASES_DIR, CORE_PHASES_PACKAGE)
    return registry


def test_missing_core_dir_raises(tmp_path):
    with pytest.raises(FlowConfigError, match="Core config directory"):
        ConfigurationEngine(core_dir=tmp_path / "nope", user_dirs=[], phase_registry=StubReg())


def test_phase_class_validate_config_non_flowconfig_error_accumulates(tmp_path):
    class ExplodingReg:
        def contains(self, n):
            return True

        def get(self, n):
            class Boom:
                @classmethod
                def validate_config(cls, phase_id, config, agents):
                    raise ValueError("kaboom")

            return Boom

    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=ExplodingReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("kaboom" in e for e in eng.flows["demo"].errors)


def test_three_conflicting_defaults_report_once(tmp_path):
    write(tmp_path / "agents" / "ag.md", "---\ntype: agent\nvariables:\n  - name: x\n    default: A\n---\nsys\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: ag\n"
        "    variables:\n      - name: x\n        default: B\n"
        "- type: phase\n  config:\n    name: q\n    agent: ag\n"
        "    variables:\n      - name: x\n        default: B\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n"
        "      - phase: p\n      - phase: q\n        dependencies: [p]\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    conflict_errors = [e for e in eng.flows["demo"].errors if "conflicting defaults" in e]
    assert len(conflict_errors) == 1


def test_multiple_errors_accumulate(tmp_path):
    """A flow with several independent problems reports all of them (no raise-on-first)."""
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: a\n    agent: nope\n"
        "    tasks:\n      - name: t\n        prompt_ref: ghost\n"
        "- type: phase\n  config:\n    name: b\n"
        "- type: flow\n  config:\n    name: demo\n"
        "    flow:\n      - phase: a\n      - phase: b\n        dependencies:\n          - missingdep\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    errors = eng.flows["demo"].errors
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("nope" in e for e in errors)
    assert any("ghost" in e for e in errors)
    assert any("missingdep" in e for e in errors)
    assert len(errors) >= 3


def test_broken_phase_referenced(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    bogus: 1\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("broken" in e.lower() for e in eng.flows["demo"].errors)


def test_broken_agent_referenced(tmp_path):
    write(tmp_path / "agents" / "ag.md", "---\ntype: agent\ntools:\n  - nonexistent_tool\n---\nsys\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: ag\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("ag" in e and "broken" in e.lower() for e in eng.flows["demo"].errors)


def test_broken_prompt_ref_referenced(tmp_path):
    write(tmp_path / "prompts" / "x.md", "---\ntype: nonsense\n---\nbody\n")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "    tasks:\n      - name: t\n        prompt_ref: x\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("broken" in e.lower() for e in eng.flows["demo"].errors)


def test_flows_validated_independently(tmp_path):
    """A broken flow doesn't poison a sibling; the overview reports each independently."""
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n"
        "- type: flow\n  config:\n    name: good\n    flow:\n      - phase: p\n"
        "- type: flow\n  config:\n    name: bad\n    flow:\n      - phase: missing\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["good"].status == ConfigStatus.OK
    assert eng.flows["bad"].status == ConfigStatus.BROKEN
    eng.get_flow("good")
    with pytest.raises(FlowConfigError):
        eng.get_flow("bad")


def test_agentic_phase_without_agent_fails_validate_config(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    class: AgenticPhase\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=real_phase_registry())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("agent" in e.lower() for e in eng.flows["demo"].errors)
    with pytest.raises(FlowConfigError):
        eng.get_flow("demo")
