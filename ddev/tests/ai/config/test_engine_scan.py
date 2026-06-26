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
    assert eng._agents["a"].status == ConfigStatus.OK


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
    assert eng._agents["x"].status == ConfigStatus.BROKEN


def test_missing_user_dir_raises(tmp_path):
    with pytest.raises(FlowConfigError):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=[str(tmp_path / "nope")], phase_registry=StubReg())


def test_broken_flow_item_lands_in_flows(tmp_path):
    write(tmp_path / "f.yaml", "- type: flow\n  config:\n    name: bad\n    bogus: 1\n")
    eng = ConfigurationEngine(core_dir=tmp_path, user_dirs=[], phase_registry=StubReg())
    assert eng._flows["bad"].status == ConfigStatus.BROKEN
    assert "bad" not in eng._phases
