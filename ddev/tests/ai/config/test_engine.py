# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import textwrap
from pathlib import Path

import pytest

from ddev.ai.config.engine import ConfigurationEngine


def write_yaml(directory: Path, filename: str, content: str) -> Path:
    path = directory / filename
    path.write_text(textwrap.dedent(content))
    return path


def test_empty_directory_builds_empty_registries(tmp_path):
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert engine._agents == {}
    assert engine._phases == {}
    assert engine._flows == {}


def test_scans_yaml_and_yml_extensions(tmp_path):
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: agent
          config:
            name: agent_a
    """,
    )
    write_yaml(
        tmp_path,
        "b.yml",
        """\
        - type: agent
          config:
            name: agent_b
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert "agent_a" in engine._agents
    assert "agent_b" in engine._agents


def test_scans_recursively(tmp_path):
    sub = tmp_path / "subdir"
    sub.mkdir()
    write_yaml(
        sub,
        "agents.yaml",
        """\
        - type: agent
          config:
            name: nested_agent
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert "nested_agent" in engine._agents


def test_non_yaml_files_are_ignored(tmp_path):
    (tmp_path / "readme.txt").write_text("hello")
    (tmp_path / "config.json").write_text("{}")
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert engine._agents == {}


def test_mixed_types_in_single_file(tmp_path):
    write_yaml(
        tmp_path,
        "mixed.yaml",
        """\
        - type: agent
          config:
            name: my_agent
        - type: phase
          config:
            name: my_phase
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert "my_agent" in engine._agents
    assert "my_phase" in engine._phases
    assert "my_flow" in engine._flows


def test_no_conflicts_when_names_are_unique(tmp_path):
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: agent
          config:
            name: agent_a
    """,
    )
    write_yaml(
        tmp_path,
        "b.yaml",
        """\
        - type: agent
          config:
            name: agent_b
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert not engine.has_conflicts
    assert engine.conflicts == []


def test_conflict_detected_same_name_same_type(tmp_path):
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: agent
          config:
            name: shared_agent
    """,
    )
    write_yaml(
        tmp_path,
        "b.yaml",
        """\
        - type: agent
          config:
            name: shared_agent
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert engine.has_conflicts
    assert len(engine.conflicts) == 1
    c = engine.conflicts[0]
    assert c.name == "shared_agent"
    assert c.type == "agent"
    assert len(c.sources) == 2


def test_same_name_different_types_no_conflict(tmp_path):
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: agent
          config:
            name: shared_name
        - type: phase
          config:
            name: shared_name
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert not engine.has_conflicts


def test_user_dir_expands_tilde(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    user_dir = tmp_path / "myflows"
    user_dir.mkdir()
    ConfigurationEngine(core_dir=tmp_path, user_dirs=["~/myflows"])
    # No error means tilde was expanded and dir found


def test_user_dir_nonexistent_raises(tmp_path):
    with pytest.raises(Exception, match="/nonexistent"):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=["/nonexistent/path"])


def test_scanning_succeeds_even_with_conflicts(tmp_path):
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    write_yaml(
        tmp_path,
        "b.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    # Should not raise — validation is deferred to build_flow
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert engine.has_conflicts


def test_build_flow_raises_on_conflicts(tmp_path):
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    write_yaml(
        tmp_path,
        "b.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="conflicts"):
        engine.build_flow("my_flow")


def test_build_flow_raises_on_unknown_flow(tmp_path):
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="not found"):
        engine.build_flow("nonexistent")


def test_build_flow_raises_on_missing_phase(tmp_path):
    write_yaml(
        tmp_path,
        "flows.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: ghost_phase
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="ghost_phase"):
        engine.build_flow("my_flow")


def test_build_flow_raises_on_missing_agent(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: phase
          config:
            name: my_phase
            agent: ghost_agent
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: my_phase
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="ghost_agent"):
        engine.build_flow("my_flow")


def test_build_flow_raises_on_cycle(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: phase
          config:
            name: phase_a
        - type: phase
          config:
            name: phase_b
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
                dependencies: [phase_b]
              - phase: phase_b
                dependencies: [phase_a]
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="[Cc]ycle"):
        engine.build_flow("my_flow")


def test_build_flow_variable_default_conflict(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            variables:
              - name: endpoint
                default: http://localhost:9090
        - type: phase
          config:
            name: phase_a
            agent: agent_a
            variables:
              - name: endpoint
                default: http://localhost:8080
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="conflicting default"):
        engine.build_flow("my_flow")


def test_build_flow_missing_required_variable(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            variables:
              - name: integration_name
        - type: phase
          config:
            name: phase_a
            agent: agent_a
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(Exception, match="integration_name"):
        engine.build_flow("my_flow")


def test_build_flow_variable_resolved_from_flow(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            variables:
              - name: integration_name
        - type: phase
          config:
            name: phase_a
            agent: agent_a
        - type: flow
          config:
            name: my_flow
            variables:
              integration_name: my_integration
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.variables["integration_name"] == "my_integration"


def test_build_flow_same_default_no_conflict(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            variables:
              - name: endpoint
                default: http://localhost:9090
        - type: phase
          config:
            name: phase_a
            agent: agent_a
            variables:
              - name: endpoint
                default: http://localhost:9090
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")  # Must not raise
    assert resolved.variables["endpoint"] == "http://localhost:9090"


def test_build_flow_relative_paths_resolved(tmp_path):
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_a.md").write_text("system prompt")
    (tmp_path / "task.md").write_text("do the thing")

    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
        - type: phase
          config:
            name: phase_a
            agent: agent_a
            tasks:
              - name: task1
                prompt_path: task.md
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.agents["agent_a"].system_prompt_path == tmp_path / "prompts" / "agent_a.md"
    assert resolved.phases["phase_a"].tasks[0].prompt_path == tmp_path / "task.md"
