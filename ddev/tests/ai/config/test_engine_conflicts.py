# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from ddev.ai.config.engine import ConfigStatus, ConfigurationEngine

from .utils import StubReg, write


def test_core_and_user_same_name_conflict(tmp_path):
    core = tmp_path / "core"
    u = tmp_path / "u"
    write(core / "agents" / "a.md", "---\ntype: agent\n---\ncore body\n")
    write(u / "agents" / "a.md", "---\ntype: agent\n---\nuser body\n")
    eng = ConfigurationEngine(core_dir=core, user_dirs=[str(u)], phase_registry=StubReg())
    assert eng.has_conflicts
    c = [c for c in eng.conflicts if c.name == "a"][0]
    assert c.type == "agent" and len(c.sources) == 2
    assert "a" not in eng._agents  # conflicting resource is dropped, not picked


def test_two_core_flows_conflict(tmp_path):
    core = tmp_path / "core"
    write(
        core / "a.yaml",
        "- type: flow\n  config:\n    name: myflow\n    flow:\n      - phase: p\n",
    )
    write(
        core / "b.yaml",
        "- type: flow\n  config:\n    name: myflow\n    flow:\n      - phase: p\n",
    )
    eng = ConfigurationEngine(core_dir=core, user_dirs=[], phase_registry=StubReg())
    assert eng.has_conflicts
    c = [c for c in eng.conflicts if c.name == "myflow"][0]
    assert c.type == "flow" and len(c.sources) == 2


def test_conflicts_expose_name_type_sources(tmp_path):
    core = tmp_path / "core"
    u1 = tmp_path / "u1"
    u2 = tmp_path / "u2"
    core.mkdir()
    write(u1 / "agents" / "bot.md", "---\ntype: agent\n---\nv1\n")
    write(u2 / "agents" / "bot.md", "---\ntype: agent\n---\nv2\n")
    eng = ConfigurationEngine(core_dir=core, user_dirs=[str(u1), str(u2)], phase_registry=StubReg())
    assert eng.has_conflicts
    conflict = eng.conflicts[0]
    assert conflict.name == "bot"
    assert conflict.type == "agent"
    assert len(conflict.sources) == 2
    source_names = {p.name for p in conflict.sources}
    assert source_names == {"bot.md"}


def test_flow_referencing_conflicted_phase_reports_conflict(tmp_path):
    core = tmp_path / "core"
    write(core / "a.yaml", "- type: phase\n  config:\n    name: p\n")
    write(core / "b.yaml", "- type: phase\n  config:\n    name: p\n")
    write(core / "flow.yaml", "- type: flow\n  config:\n    name: demo\n    flow:\n      - phase: p\n")
    eng = ConfigurationEngine(core_dir=core, user_dirs=[], phase_registry=StubReg())
    diag = eng.flows["demo"]
    assert diag.status == ConfigStatus.BROKEN
    err = next(e for e in diag.errors if e.subject == "p")
    assert "conflict" in err.message.lower() and "not registered" not in err.message
    assert len(err.sources) == 2
