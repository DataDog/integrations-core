# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import pytest

from ddev.ai.config.engine import BrokenEntry, ConfigurationEngine, ValidEntry
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


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)


def test_scans_yaml_phase_and_flow(tmp_path):
    write(
        tmp_path / "f.yaml",
        "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n- type: phase\n  config:\n    name: p\n",
    )
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert "demo" in eng._flows and "p" in eng._phases


def test_scans_agent_md(tmp_path):
    write(tmp_path / "agents" / "a.md", "---\ntype: agent\nmodel: m\n---\nyou are an agent\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng._agents["a"].config.system_prompt == "you are an agent"
    assert isinstance(eng._agents["a"], ValidEntry)


def test_prompt_goal_memory_routing(tmp_path):
    for name, typ in [("intro", "prompt"), ("g", "goal"), ("mem", "memory")]:
        write(tmp_path / "prompts" / f"{name}.md", f"---\ntype: {typ}\n---\nbody-{name}\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng._prompts["intro"].config == "body-intro"
    assert eng._goals["g"].config == "body-g"
    assert eng._memories["mem"].config == "body-mem"


def test_type_folder_mismatch_is_broken(tmp_path):
    write(tmp_path / "agents" / "x.md", "---\ntype: prompt\n---\nbody\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert isinstance(eng._agents["x"], BrokenEntry)


def test_missing_user_dir_raises(tmp_path):
    with pytest.raises(FlowConfigError):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=[str(tmp_path / "nope")], phase_registry=StubReg())


def test_broken_flow_item_lands_in_flows(tmp_path):
    write(tmp_path / "f.yaml", "- type: flow\n  config:\n    name: bad\n    bogus: 1\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert isinstance(eng._flows["bad"], BrokenEntry)
    assert "bad" not in eng._phases


def test_yaml_inside_reserved_folders_is_skipped(tmp_path):
    write(tmp_path / "agents" / "sneaky.yaml", "- type: phase\n  config:\n    name: ghost\n")
    write(
        tmp_path / "prompts" / "sneaky.yml",
        "- type: flow\n  config:\n    name: ghostflow\n    flow:\n      - phase: p\n",
    )
    write(tmp_path / "real.yaml", "- type: phase\n  config:\n    name: ghost\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert "ghostflow" not in eng._flows
    assert eng._phases["ghost"].source_file == tmp_path / "real.yaml"


def test_unparseable_yaml_recorded_as_file_error(tmp_path):
    write(tmp_path / "bad.yaml", "this: : not valid: yaml: [")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert any(p.name == "bad.yaml" for p in eng.file_errors)
    assert "bad" not in eng._phases  # no fabricated phase entry
    assert not eng.has_conflicts


def test_non_list_yaml_recorded_as_file_error(tmp_path):
    write(tmp_path / "scalar.yaml", "just_a_string")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert any(p.name == "scalar.yaml" for p in eng.file_errors)
    assert "scalar" not in eng._phases


def test_broken_file_does_not_conflict_with_real_phase(tmp_path):
    # file stem 'p' would previously collide with a real phase named 'p'
    write(tmp_path / "p.yaml", "not valid: [")
    write(tmp_path / "real.yaml", "- type: phase\n  config:\n    name: p\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert not eng.has_conflicts
    assert isinstance(eng._phases["p"], ValidEntry)


def test_nameless_broken_item_goes_to_file_errors_not_registry(tmp_path):
    write(tmp_path / "f.yaml", "- type: phase\n  bogus: 1\n")  # no config.name
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.file_errors and eng._phases == {}


def test_unknown_type_broken_item_goes_to_file_errors(tmp_path):
    write(tmp_path / "f.yaml", "- type: nonsense\n  config:\n    name: x\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng.file_errors
    assert "x" not in eng._phases and "x" not in eng._flows


def test_named_valid_type_broken_item_still_registered(tmp_path):
    write(tmp_path / "f.yaml", "- type: flow\n  config:\n    name: bad\n    bogus: 1\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert isinstance(eng._flows["bad"], BrokenEntry)  # referenceable by name


def test_same_named_files_with_nameless_broken_items_do_not_conflict(tmp_path):
    write(tmp_path / "a" / "flow.yaml", "- type: phase\n  bogus: 1\n")
    write(tmp_path / "b" / "flow.yaml", "- type: phase\n  bogus: 1\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert not eng.has_conflicts


def test_skipped_item_is_logged(tmp_path, caplog):
    write(tmp_path / "f.yaml", "- type: nonsense\n  config:\n    name: x\n")
    with caplog.at_level("WARNING"):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert any("Skipping unparseable config" in r.getMessage() for r in caplog.records)
