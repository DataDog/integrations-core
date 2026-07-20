# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest

from ddev.ai.config.engine import ConfigurationEngine as BaseConfigurationEngine
from ddev.ai.config.errors import ConfigError, ErrorKind
from ddev.ai.config.models import ConfigStatus
from ddev.ai.config.registry import ResourceKind

from .utils import StubReg, make_provider_registry, write


class ConfigurationEngine(BaseConfigurationEngine):
    def __init__(self, *args, provider_registry=None, **kwargs):
        super().__init__(
            *args,
            provider_registry=provider_registry or make_provider_registry("anthropic"),
            **kwargs,
        )


def real_phase_registry():
    from ddev.ai.constants import CORE_PHASES_DIR, CORE_PHASES_PACKAGE
    from ddev.ai.phases.registry import PhaseRegistry

    registry = PhaseRegistry()
    registry.register_from(CORE_PHASES_DIR, CORE_PHASES_PACKAGE)
    return registry


PHASE_AND_FLOW = (
    "- type: phase\n  config:\n    name: p\n    agent: ag\n"
    "    tasks:\n      - name: t\n        prompt_ref: intro\n        goal_ref: g\n"
    "    checkpoint:\n      memory_prompt_ref: mem\n"
    "- type: flow\n  config:\n    name: demo\n    description: Generate an integration\n"
    "    inputs:\n      - name: topic\n        label: Topic\n        type: string\n        default: metrics\n"
    "    variables:\n      x: hi\n"
    "    flow:\n      - phase: p\n"
)


def write_full_flow(root):
    write(root / "ag.md", "---\ntype: agent\nname: ag\nmodel: sonnet\n---\nsys")
    write(root / "intro.md", "---\ntype: prompt\nname: intro\n---\nDo the thing ${x}")
    write(root / "g.md", "---\ntype: goal\nname: g\n---\ngoal body")
    write(root / "mem.md", "---\ntype: memory_prompt\nname: mem\n---\nRemember ${x}")
    write(root / "f.yaml", PHASE_AND_FLOW)


def test_unavailable_agent_provider_breaks_dependent_flow(tmp_path):
    write_full_flow(tmp_path)
    write(tmp_path / "ag.md", "---\ntype: agent\nname: ag\nprovider: unavailable\n---\nsys")

    eng = ConfigurationEngine(
        core_dir=tmp_path,
        user_dirs=[],
        phase_registry=StubReg(),
        provider_registry=make_provider_registry("anthropic"),
    )

    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any("unavailable" in error.message for error in eng.flows["demo"].errors)


# ---------------------------------------------------------------------------
# End-to-end wiring: discover -> classify -> registry -> resolve
# ---------------------------------------------------------------------------


def test_get_flow_resolves_all_refs_and_variables(tmp_path):
    write_full_flow(tmp_path)
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    rf = eng.get_flow("demo")

    task = rf.phases["p"].tasks[0]
    assert task.prompt == "Do the thing ${x}"
    assert task.prompt_ref is None
    assert task.goal == "goal body"
    assert task.goal_ref is None
    assert rf.phases["p"].checkpoint.memory_prompt == "Remember ${x}"
    assert rf.phases["p"].checkpoint.memory_prompt_ref is None
    assert rf.variables == {"x": "hi"}
    assert rf.agents["ag"].system_prompt == "sys"
    assert rf.description == "Generate an integration"
    assert [flow_input.name for flow_input in rf.inputs] == ["topic", "prd", "max_timeout"]


def test_runtime_input_satisfies_eager_variable_resolution(tmp_path):
    write(
        tmp_path / "flow.yaml",
        "- type: phase\n"
        "  config:\n"
        "    name: p\n"
        "    variables:\n"
        "      - name: topic\n"
        "- type: flow\n"
        "  config:\n"
        "    name: demo\n"
        "    inputs:\n"
        "      - name: topic\n"
        "        label: Topic\n"
        "        type: string\n"
        "    flow:\n"
        "      - phase: p\n",
    )

    resolved = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg()).get_flow("demo")

    assert [flow_input.name for flow_input in resolved.inputs] == ["topic", "prd", "max_timeout"]
    assert resolved.variables == {}


def test_directory_layout_is_irrelevant(tmp_path):
    """Classification is by type tag, not directory; nesting/naming don't matter."""
    write(tmp_path / "deeply" / "nested" / "anything.md", "---\ntype: agent\nname: ag\nmodel: sonnet\n---\nsys")
    write(tmp_path / "intro.md", "---\ntype: prompt\nname: intro\n---\np")
    write(tmp_path / "g.md", "---\ntype: goal\nname: g\n---\ng")
    write(tmp_path / "sub" / "mem.md", "---\ntype: memory_prompt\nname: mem\n---\nm")
    write(tmp_path / "config" / "flow.yaml", PHASE_AND_FLOW)

    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.OK
    assert eng.get_flow("demo").agents["ag"].system_prompt == "sys"


def test_markdown_keyed_by_front_matter_name_not_stem(tmp_path):
    """Identity is the front-matter name; the filename stem is organizational only."""
    write(tmp_path / "unrelated-filename.md", "---\ntype: agent\nname: ag\nmodel: sonnet\n---\nsys")
    write(tmp_path / "intro.md", "---\ntype: prompt\nname: intro\n---\np")
    write(tmp_path / "g.md", "---\ntype: goal\nname: g\n---\ng")
    write(tmp_path / "mem.md", "---\ntype: memory_prompt\nname: mem\n---\nm")
    write(tmp_path / "f.yaml", PHASE_AND_FLOW)

    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert "ag" in eng.get_flow("demo").agents


def test_single_mapping_yaml_resource_resolves(tmp_path):
    """A YAML file may hold one resource as a bare mapping, with no list wrapper."""
    write(tmp_path / "ag.md", "---\ntype: agent\nname: ag\nmodel: sonnet\n---\nsys")
    write(tmp_path / "phase.yaml", "type: phase\nconfig:\n  name: p\n  agent: ag\n")
    write(tmp_path / "flow.yaml", "type: flow\nconfig:\n  name: demo\n  flow:\n    - phase: p\n")

    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.flows["demo"].status == ConfigStatus.OK
    assert "p" in eng.get_flow("demo").phases


# ---------------------------------------------------------------------------
# File errors vs skip-silently (behavior changes)
# ---------------------------------------------------------------------------


def test_markdown_missing_name_is_file_error(tmp_path):
    write(tmp_path / "ag.md", "---\ntype: agent\n---\nsys")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert any(p.name == "ag.md" for p in eng.file_errors)


def test_scalar_yaml_skipped_silently(tmp_path):
    write(tmp_path / "scalar.yaml", "just_a_string")
    write(tmp_path / "mapping.yaml", "a: 1\nb: 2\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.file_errors == {}
    assert not eng.has_conflicts


def test_frontmatterless_markdown_skipped_silently(tmp_path):
    write(tmp_path / "notes.md", "Just some prose with no front matter.")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.file_errors == {}


def test_type_in_wrong_format_is_file_error(tmp_path):
    write(tmp_path / "phase_in_md.md", "---\ntype: phase\nname: p\n---\nbody")
    write(tmp_path / "agent_in_yaml.yaml", "- type: agent\n  config:\n    name: ag\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    error_names = {p.name for p in eng.file_errors}
    assert error_names == {"phase_in_md.md", "agent_in_yaml.yaml"}


def test_unparseable_yaml_recorded_as_file_error(tmp_path):
    write(tmp_path / "bad.yaml", "not valid: [")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert any(p.name == "bad.yaml" for p in eng.file_errors)


def test_non_utf8_file_recorded_as_file_error(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_bytes(b"\xff")

    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())

    assert "not valid UTF-8" in eng.file_errors[path]


def test_skipped_file_error_is_logged(tmp_path, caplog):
    write(tmp_path / "bad.yaml", "not valid: [")
    with caplog.at_level("WARNING"):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert any("Skipping unparseable config" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# Eager diagnostics
# ---------------------------------------------------------------------------


def test_flows_overview_populated_without_get_flow(tmp_path):
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
    with pytest.raises(ConfigError):
        eng.get_flow("bad")


def test_get_flow_unknown_name_raises(tmp_path):
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    with pytest.raises(ConfigError):
        eng.get_flow("nope")


def test_get_flow_missing_surfaces_file_error_note(tmp_path):
    write(tmp_path / "bad.yaml", "not valid: [")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    with pytest.raises(ConfigError, match="failed to parse"):
        eng.get_flow("anything")


# ---------------------------------------------------------------------------
# Conflicts (identity is (type, name), global)
# ---------------------------------------------------------------------------


def test_core_and_user_same_identity_conflict(tmp_path):
    core = tmp_path / "core"
    user = tmp_path / "user"
    write(core / "a.md", "---\ntype: agent\nname: ag\n---\ncore body")
    write(user / "b.md", "---\ntype: agent\nname: ag\n---\nuser body")
    eng = ConfigurationEngine(core_dir=core, user_dirs=[str(user)], phase_registry=StubReg())
    assert eng.has_conflicts
    conflict = next(c for c in eng.conflicts if c.name == "ag")
    assert conflict.kind == ResourceKind.AGENT
    assert len(conflict.sources) == 2


def test_cross_type_same_name_coexists(tmp_path):
    """agent:x and flow:x are different identities and both remain usable."""
    write(tmp_path / "x_agent.md", "---\ntype: agent\nname: x\nmodel: sonnet\n---\nsys")
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    agent: x\n"
        "- type: flow\n  config:\n    name: x\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert not eng.has_conflicts
    assert eng.flows["x"].status == ConfigStatus.OK
    assert "x" in eng.get_flow("x").agents


def test_flow_conflict_surfaces_as_broken(tmp_path):
    core = tmp_path / "core"
    user = tmp_path / "user"
    write(core / "one.yaml", "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n")
    write(user / "two.yaml", "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n")
    eng = ConfigurationEngine(core_dir=core, user_dirs=[str(user)], phase_registry=StubReg())
    diag = eng.flows["demo"]
    assert diag.status == ConfigStatus.BROKEN
    err = next(e for e in diag.errors if e.kind is ErrorKind.FLOW)
    assert {p.name for p in err.sources} == {"one.yaml", "two.yaml"}
    with pytest.raises(ConfigError):
        eng.get_flow("demo")


def test_overlapping_core_and_user_dir_is_not_a_false_conflict(tmp_path):
    """A file reachable from both core and an overlapping user dir is read once, not conflicting."""
    write_full_flow(tmp_path)
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[str(tmp_path)], phase_registry=StubReg())
    assert not eng.has_conflicts
    assert eng.flows["demo"].status == ConfigStatus.OK
    assert eng.get_flow("demo").variables == {"x": "hi"}


# ---------------------------------------------------------------------------
# Directory validation & real phase registry
# ---------------------------------------------------------------------------


def test_missing_core_dir_raises(tmp_path):
    with pytest.raises(ConfigError, match="Core config directory"):
        ConfigurationEngine(core_dir=tmp_path / "nope", user_dirs=[], phase_registry=StubReg())


def test_missing_user_dir_raises(tmp_path):
    with pytest.raises(ConfigError, match="User config directory"):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=[str(tmp_path / "nope")], phase_registry=StubReg())


def test_agentic_phase_without_agent_fails_with_real_registry(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: phase\n  config:\n    name: p\n    class: AgenticPhase\n"
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=real_phase_registry())
    assert eng.flows["demo"].status == ConfigStatus.BROKEN
    assert any(e.kind is ErrorKind.PHASE and "requires 'agent'" in e.message for e in eng.flows["demo"].errors)


def test_flows_returns_a_copy(tmp_path):
    """Mutating the mapping returned by ``flows`` must not corrupt the engine's cache."""
    write_full_flow(tmp_path)
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())

    eng.flows.clear()

    assert "demo" in eng.flows
