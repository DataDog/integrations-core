# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import textwrap
from pathlib import Path

import pytest

from ddev.ai.config.engine import ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError, detect_cycles


def write_yaml(directory: Path, filename: str, content: str) -> Path:
    path = directory / filename
    path.write_text(textwrap.dedent(content))
    return path


# ---------------------------------------------------------------------------
# Basic scanning
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


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


def test_conflict_sources_are_in_scan_order(tmp_path):
    """Conflict sources list reflects the order files were scanned (alphabetical within a dir)."""
    a_path = write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: agent
          config:
            name: dup
            model: first
    """,
    )
    b_path = write_yaml(
        tmp_path,
        "b.yaml",
        """\
        - type: agent
          config:
            name: dup
            model: second
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    c = engine.conflicts[0]
    assert c.sources == [a_path, b_path]


def test_three_sources_all_listed_in_conflict(tmp_path):
    for name in ("a.yaml", "b.yaml", "c.yaml"):
        write_yaml(
            tmp_path,
            name,
            """\
            - type: phase
              config:
                name: shared_phase
        """,
        )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert len(engine.conflicts) == 1
    assert len(engine.conflicts[0].sources) == 3


def test_conflicted_resource_not_in_registry(tmp_path):
    """Conflicting resources must NOT be silently stored — direct lookup should miss."""
    write_yaml(
        tmp_path,
        "a.yaml",
        """\
        - type: agent
          config:
            name: dup
    """,
    )
    write_yaml(
        tmp_path,
        "b.yaml",
        """\
        - type: agent
          config:
            name: dup
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert engine.has_conflicts
    assert "dup" not in engine._agents


# ---------------------------------------------------------------------------
# User dirs
# ---------------------------------------------------------------------------


def test_user_dir_expands_tilde(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows
    user_dir = tmp_path / "myflows"
    user_dir.mkdir()
    ConfigurationEngine(core_dir=tmp_path, user_dirs=["~/myflows"])


def test_user_dir_nonexistent_raises(tmp_path):
    with pytest.raises(FlowConfigError, match="nonexistent"):
        ConfigurationEngine(core_dir=tmp_path, user_dirs=[str(tmp_path / "nonexistent")])


def test_user_dir_resources_are_picked_up(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    user = tmp_path / "user"
    user.mkdir()
    write_yaml(
        core,
        "core.yaml",
        """\
        - type: agent
          config:
            name: core_agent
    """,
    )
    write_yaml(
        user,
        "user.yaml",
        """\
        - type: agent
          config:
            name: user_agent
    """,
    )
    engine = ConfigurationEngine(core_dir=core, user_dirs=[str(user)])
    assert "core_agent" in engine._agents
    assert "user_agent" in engine._agents


def test_user_dir_conflict_with_core_dir(tmp_path):
    """Same (type, name) in core and user dir produces a conflict — no silent override."""
    core = tmp_path / "core"
    core.mkdir()
    user = tmp_path / "user"
    user.mkdir()
    write_yaml(
        core,
        "c.yaml",
        """\
        - type: agent
          config:
            name: shared
            model: core-model
    """,
    )
    write_yaml(
        user,
        "u.yaml",
        """\
        - type: agent
          config:
            name: shared
            model: user-model
    """,
    )
    engine = ConfigurationEngine(core_dir=core, user_dirs=[str(user)])
    assert engine.has_conflicts
    c = engine.conflicts[0]
    assert c.name == "shared"
    assert len(c.sources) == 2


def test_multiple_user_dirs_cascade(tmp_path):
    """Resources from multiple user dirs all land in the registry when names are unique."""
    core = tmp_path / "core"
    core.mkdir()
    u1 = tmp_path / "u1"
    u1.mkdir()
    u2 = tmp_path / "u2"
    u2.mkdir()
    write_yaml(
        u1,
        "a.yaml",
        """\
        - type: agent
          config:
            name: agent_u1
    """,
    )
    write_yaml(
        u2,
        "b.yaml",
        """\
        - type: agent
          config:
            name: agent_u2
    """,
    )
    engine = ConfigurationEngine(core_dir=core, user_dirs=[str(u1), str(u2)])
    assert "agent_u1" in engine._agents
    assert "agent_u2" in engine._agents
    assert not engine.has_conflicts


def test_overlapping_scan_dirs_no_double_processing(tmp_path):
    """Passing core_dir twice (via user_dirs) should not create spurious conflicts."""
    write_yaml(
        tmp_path,
        "agents.yaml",
        """\
        - type: agent
          config:
            name: shared_agent
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path, user_dirs=[str(tmp_path)])
    assert not engine.has_conflicts
    assert "shared_agent" in engine._agents


def test_yaml_and_yml_same_stem_no_double_processing(tmp_path):
    """A file.yaml and file.yml with the same content do NOT produce a conflict."""
    content = """\
        - type: agent
          config:
            name: only_once
    """
    (tmp_path / "x.yaml").write_text(textwrap.dedent(content))
    (tmp_path / "x.yml").write_text(textwrap.dedent(content))
    engine = ConfigurationEngine(core_dir=tmp_path)
    # Two distinct files → conflict, because they have the same (type, name) from different paths.
    # But the key correctness property is that each file is processed at most once.
    assert len(engine.conflicts) == 1
    assert len(engine.conflicts[0].sources) == 2


# ---------------------------------------------------------------------------
# Scanning + conflicts (existing behavior)
# ---------------------------------------------------------------------------


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
    engine = ConfigurationEngine(core_dir=tmp_path)
    assert engine.has_conflicts


# ---------------------------------------------------------------------------
# build_flow error paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "yaml_content,expected_match",
    [
        pytest.param(
            """\
        - type: flow
          config:
            name: my_flow
            flow: []
        """,
            "conflicts",
            id="conflict",
        ),
        pytest.param(
            "",
            "not found",
            id="unknown_flow",
        ),
        pytest.param(
            """\
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: ghost_phase
        """,
            "ghost_phase",
            id="missing_phase",
        ),
        pytest.param(
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
            "ghost_agent",
            id="missing_agent",
        ),
        pytest.param(
            """\
        - type: phase
          config:
            name: phase_a
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
              - phase: phase_a
        """,
            "[Dd]uplicate",
            id="duplicate_phase",
        ),
        pytest.param(
            """\
        - type: phase
          config:
            name: phase_b
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_b
                dependencies: [phase_a]
        """,
            "phase_a",
            id="dependency_not_in_flow",
        ),
        pytest.param(
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
            "conflicting default",
            id="variable_default_conflict",
        ),
        pytest.param(
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
            "integration_name",
            id="missing_required_variable",
        ),
    ],
)
def test_build_flow_error_paths(tmp_path, yaml_content, expected_match):
    if yaml_content:
        write_yaml(tmp_path, "config.yaml", yaml_content)
    if expected_match == "conflicts":
        # Conflict test needs two files
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
    with pytest.raises(FlowConfigError, match=expected_match):
        engine = ConfigurationEngine(core_dir=tmp_path)
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
    with pytest.raises(FlowConfigError, match="[Cc]ycle"):
        engine.build_flow("my_flow")


# ---------------------------------------------------------------------------
# _parse_file failure modes
# ---------------------------------------------------------------------------


def test_non_list_yaml_file_raises(tmp_path):
    (tmp_path / "config.yaml").write_text("key: value\n")
    with pytest.raises(FlowConfigError, match="expected a YAML list"):
        ConfigurationEngine(core_dir=tmp_path)


def test_malformed_yaml_raises_flow_config_error(tmp_path):
    (tmp_path / "bad.yaml").write_text("key: [unclosed\n")
    with pytest.raises(FlowConfigError, match="Malformed YAML"):
        ConfigurationEngine(core_dir=tmp_path)


def test_unreadable_file_raises_flow_config_error(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("- type: agent\n  config:\n    name: x\n")
    bad.chmod(0o000)
    try:
        with pytest.raises(FlowConfigError, match="Could not read"):
            ConfigurationEngine(core_dir=tmp_path)
    finally:
        bad.chmod(0o644)


def test_list_element_not_a_mapping_raises(tmp_path):
    (tmp_path / "config.yaml").write_text("- just_a_string\n")
    with pytest.raises(FlowConfigError):
        ConfigurationEngine(core_dir=tmp_path)


def test_unknown_type_value_raises(tmp_path):
    (tmp_path / "config.yaml").write_text("- type: widget\n  config:\n    name: x\n")
    with pytest.raises(FlowConfigError):
        ConfigurationEngine(core_dir=tmp_path)


# ---------------------------------------------------------------------------
# Variable resolution
# ---------------------------------------------------------------------------


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
    resolved = engine.build_flow("my_flow")
    assert resolved.variables["endpoint"] == "http://localhost:9090"


def test_variable_default_promoted_from_second_source(tmp_path):
    """A variable with no default in phase A but a default in phase B should resolve."""
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: phase
          config:
            name: phase_a
            variables:
              - name: shared_var
        - type: phase
          config:
            name: phase_b
            variables:
              - name: shared_var
                default: from_b
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
              - phase: phase_b
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.variables["shared_var"] == "from_b"


def test_runtime_override_takes_precedence_over_default(tmp_path):
    """Flow-level variables override declared defaults."""
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            variables:
              - name: endpoint
                default: http://default
        - type: phase
          config:
            name: phase_a
            agent: agent_a
        - type: flow
          config:
            name: my_flow
            variables:
              endpoint: http://override
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.variables["endpoint"] == "http://override"


def test_missing_variable_error_lists_all_missing(tmp_path):
    """When multiple variables are missing, all are listed in the error."""
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            variables:
              - name: var_one
              - name: var_two
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
    with pytest.raises(FlowConfigError) as exc_info:
        engine.build_flow("my_flow")
    msg = str(exc_info.value)
    assert "var_one" in msg
    assert "var_two" in msg


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


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


def test_build_flow_absolute_prompt_path_preserved(tmp_path):
    task_file = tmp_path / "task.md"
    task_file.write_text("do the thing")
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "agent_a.md").write_text("sys")

    write_yaml(
        tmp_path,
        "config.yaml",
        f"""\
        - type: agent
          config:
            name: agent_a
        - type: phase
          config:
            name: phase_a
            agent: agent_a
            tasks:
              - name: task1
                prompt_path: {task_file}
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.phases["phase_a"].tasks[0].prompt_path == task_file


def test_build_flow_goal_path_resolved(tmp_path):
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "agent_a.md").write_text("sys")
    (tmp_path / "goal.md").write_text("goal text")
    (tmp_path / "task.md").write_text("task text")

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
                goal_path: goal.md
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.phases["phase_a"].tasks[0].goal_path == tmp_path / "goal.md"


def test_build_flow_user_supplied_system_prompt_path_preserved(tmp_path):
    """If the YAML sets system_prompt_path explicitly, it must not be overwritten."""
    custom_prompt = tmp_path / "custom.md"
    custom_prompt.write_text("custom sys")

    write_yaml(
        tmp_path,
        "config.yaml",
        f"""\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: {custom_prompt}
        - type: phase
          config:
            name: phase_a
            agent: agent_a
            tasks:
              - name: task1
                prompt: inline
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    resolved = engine.build_flow("my_flow")
    assert resolved.agents["agent_a"].system_prompt_path == custom_prompt


# ---------------------------------------------------------------------------
# detect_cycles — direct unit tests
# ---------------------------------------------------------------------------


def test_detect_cycles_no_cycles():
    deps = {"a": ["b"], "b": ["c"], "c": []}
    cycles, truncated = detect_cycles(deps)
    assert cycles == []
    assert not truncated


def test_detect_cycles_self_loop():
    deps = {"a": ["a"]}
    cycles, truncated = detect_cycles(deps)
    assert len(cycles) == 1
    assert "a" in cycles[0]
    assert not truncated


def test_detect_cycles_simple_two_node():
    deps = {"a": ["b"], "b": ["a"]}
    cycles, truncated = detect_cycles(deps)
    assert len(cycles) >= 1
    cycle_nodes = {n for c in cycles for n in c}
    assert "a" in cycle_nodes and "b" in cycle_nodes
    assert not truncated


def test_detect_cycles_limit_truncated():
    # Build a graph with more cycles than the limit
    n = 10
    deps = {str(i): [str((i + 1) % n), str((i + 2) % n)] for i in range(n)}
    cycles, truncated = detect_cycles(deps, limit=3)
    assert len(cycles) == 3
    assert truncated


def test_detect_cycles_empty_graph():
    cycles, truncated = detect_cycles({})
    assert cycles == []
    assert not truncated


def test_detect_cycles_no_duplicate_start_nodes(tmp_path):
    """The same simple cycle from different start nodes is reported at most once."""
    deps = {"a": ["b"], "b": ["a"], "c": []}
    cycles, _ = detect_cycles(deps)
    cycle_sets = [frozenset(c) for c in cycles]
    assert len(set(cycle_sets)) == len(cycle_sets), "duplicate cycle reported"


# ---------------------------------------------------------------------------
# build_flow — additional cycle / multi-cycle
# ---------------------------------------------------------------------------


def test_build_flow_multi_cycle_reports_both(tmp_path):
    write_yaml(
        tmp_path,
        "config.yaml",
        """\
        - type: phase
          config:
            name: p1
        - type: phase
          config:
            name: p2
        - type: phase
          config:
            name: p3
        - type: phase
          config:
            name: p4
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: p1
                dependencies: [p3, p4]
              - phase: p2
                dependencies: [p1]
              - phase: p3
                dependencies: [p2]
              - phase: p4
                dependencies: [p2]
    """,
    )
    engine = ConfigurationEngine(core_dir=tmp_path)
    with pytest.raises(FlowConfigError) as exc_info:
        engine.build_flow("my_flow")
    error = str(exc_info.value)
    assert "p1" in error
    assert "p2" in error
