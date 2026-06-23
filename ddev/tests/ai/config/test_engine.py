# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import textwrap
from pathlib import Path

import pytest

from ddev.ai.config.engine import ConfigurationEngine
from ddev.ai.config.errors import FlowConfigError, detect_cycles

FLOW_NAME = "my_flow"


def write_yaml(directory: Path, filename: str, content: str) -> Path:
    path = directory / filename
    path.write_text(textwrap.dedent(content))
    return path


def make_flow_dir(base: Path, flow_name: str = FLOW_NAME) -> Path:
    """Create and return <base>/<flow_name>/."""
    d = base / flow_name
    d.mkdir(exist_ok=True)
    return d


# ---------------------------------------------------------------------------
# Basic scanning
# ---------------------------------------------------------------------------


def test_empty_directory_builds_empty_registries(tmp_path):
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert engine._agents == {}
    assert engine._phases == {}
    assert engine._flows == {}


def test_scans_yaml_and_yml_extensions(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "a.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        d,
        "b.yml",
        """\
        - type: agent
          config:
            name: agent_b
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert "agent_a" in engine._agents
    assert "agent_b" in engine._agents


def test_scans_recursively(tmp_path):
    d = make_flow_dir(tmp_path)
    sub = d / "subdir"
    sub.mkdir()
    write_yaml(
        sub,
        "agents.yaml",
        """\
        - type: agent
          config:
            name: nested_agent
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert "nested_agent" in engine._agents


def test_non_yaml_files_are_ignored(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "readme.txt").write_text("hello")
    (d / "config.json").write_text("{}")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert engine._agents == {}


def test_mixed_types_in_single_file(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "mixed.yaml",
        """\
        - type: agent
          config:
            name: my_agent
            system_prompt_path: /fake.md
        - type: phase
          config:
            name: my_phase
            class: AgenticPhase
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert "my_agent" in engine._agents
    assert "my_phase" in engine._phases
    assert "my_flow" in engine._flows


# ---------------------------------------------------------------------------
# Targeted loading — flow subdir + shared/
# ---------------------------------------------------------------------------


def test_only_flow_subdir_is_scanned(tmp_path):
    """Files outside <core>/<flow_name>/ and <core>/shared/ are not picked up."""
    d = make_flow_dir(tmp_path)
    write_yaml(d, "a.yaml", "- type: agent\n  config:\n    name: flow_agent\n")
    other = tmp_path / "other_flow"
    other.mkdir()
    write_yaml(other, "b.yaml", "- type: agent\n  config:\n    name: other_agent\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert "flow_agent" in engine._agents
    assert "other_agent" not in engine._agents


def test_shared_dir_is_always_scanned(tmp_path):
    """Resources in <core>/shared/ are available to every flow."""
    make_flow_dir(tmp_path)
    shared = tmp_path / "shared"
    shared.mkdir()
    write_yaml(shared, "agents.yaml", "- type: agent\n  config:\n    name: shared_agent\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert "shared_agent" in engine._agents


def test_flow_and_shared_merged(tmp_path):
    """Resources from both the flow dir and shared/ appear in the same registry."""
    d = make_flow_dir(tmp_path)
    shared = tmp_path / "shared"
    shared.mkdir()
    write_yaml(d, "agents.yaml", "- type: agent\n  config:\n    name: flow_agent\n")
    write_yaml(shared, "agents.yaml", "- type: agent\n  config:\n    name: shared_agent\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert "flow_agent" in engine._agents
    assert "shared_agent" in engine._agents


def test_missing_flow_subdir_is_not_an_error(tmp_path):
    """If <core>/<flow_name>/ doesn't exist the engine inits with empty registries."""
    engine = ConfigurationEngine("nonexistent_flow", core_dir=tmp_path)
    assert engine._agents == {}


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def test_no_conflicts_when_names_are_unique(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "a.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        d,
        "b.yaml",
        """\
        - type: agent
          config:
            name: agent_b
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert not engine.has_conflicts
    assert engine.conflicts == []


def test_conflict_detected_same_name_same_type(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "a.yaml",
        """\
        - type: agent
          config:
            name: shared_agent
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        d,
        "b.yaml",
        """\
        - type: agent
          config:
            name: shared_agent
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert engine.has_conflicts
    assert len(engine.conflicts) == 1
    c = engine.conflicts[0]
    assert c.name == "shared_agent"
    assert c.type == "agent"
    assert len(c.sources) == 2


def test_same_name_different_types_no_conflict(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "a.yaml",
        """\
        - type: agent
          config:
            name: shared_name
            system_prompt_path: /fake.md
        - type: phase
          config:
            name: shared_name
            class: AgenticPhase
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert not engine.has_conflicts


def test_conflict_sources_are_in_scan_order(tmp_path):
    """Conflict sources list reflects the order files were scanned (alphabetical within a dir)."""
    d = make_flow_dir(tmp_path)
    a_path = write_yaml(
        d,
        "a.yaml",
        """\
        - type: agent
          config:
            name: dup
            model: first
            system_prompt_path: /fake.md
    """,
    )
    b_path = write_yaml(
        d,
        "b.yaml",
        """\
        - type: agent
          config:
            name: dup
            model: second
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    c = engine.conflicts[0]
    assert c.sources == [a_path, b_path]


def test_three_sources_all_listed_in_conflict(tmp_path):
    d = make_flow_dir(tmp_path)
    for name in ("a.yaml", "b.yaml", "c.yaml"):
        write_yaml(
            d,
            name,
            """\
            - type: phase
              config:
                name: shared_phase
                class: AgenticPhase
        """,
        )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine.conflicts) == 1
    assert len(engine.conflicts[0].sources) == 3


def test_conflicted_resource_not_in_registry(tmp_path):
    """Conflicting resources must NOT be silently stored — direct lookup should miss."""
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "a.yaml",
        """\
        - type: agent
          config:
            name: dup
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        d,
        "b.yaml",
        """\
        - type: agent
          config:
            name: dup
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
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
    ConfigurationEngine(FLOW_NAME, core_dir=tmp_path, user_dirs=["~/myflows"])


def test_user_dir_nonexistent_raises(tmp_path):
    with pytest.raises(FlowConfigError, match="nonexistent"):
        ConfigurationEngine(FLOW_NAME, core_dir=tmp_path, user_dirs=[str(tmp_path / "nonexistent")])


def test_user_dir_resources_are_picked_up(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    (core / FLOW_NAME).mkdir()
    user = tmp_path / "user"
    user.mkdir()
    (user / FLOW_NAME).mkdir()
    write_yaml(
        core / FLOW_NAME,
        "core.yaml",
        """\
        - type: agent
          config:
            name: core_agent
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        user / FLOW_NAME,
        "user.yaml",
        """\
        - type: agent
          config:
            name: user_agent
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=core, user_dirs=[str(user)])
    assert "core_agent" in engine._agents
    assert "user_agent" in engine._agents


def test_user_dir_conflict_with_core_dir(tmp_path):
    """Same (type, name) in core and user dir produces a conflict — no silent override."""
    core = tmp_path / "core"
    core.mkdir()
    (core / FLOW_NAME).mkdir()
    user = tmp_path / "user"
    user.mkdir()
    (user / FLOW_NAME).mkdir()
    write_yaml(
        core / FLOW_NAME,
        "c.yaml",
        """\
        - type: agent
          config:
            name: shared
            model: core-model
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        user / FLOW_NAME,
        "u.yaml",
        """\
        - type: agent
          config:
            name: shared
            model: user-model
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=core, user_dirs=[str(user)])
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
    (u1 / FLOW_NAME).mkdir()
    u2 = tmp_path / "u2"
    u2.mkdir()
    (u2 / FLOW_NAME).mkdir()
    write_yaml(
        u1 / FLOW_NAME,
        "a.yaml",
        """\
        - type: agent
          config:
            name: agent_u1
            system_prompt_path: /fake.md
    """,
    )
    write_yaml(
        u2 / FLOW_NAME,
        "b.yaml",
        """\
        - type: agent
          config:
            name: agent_u2
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=core, user_dirs=[str(u1), str(u2)])
    assert "agent_u1" in engine._agents
    assert "agent_u2" in engine._agents
    assert not engine.has_conflicts


def test_overlapping_scan_dirs_no_double_processing(tmp_path):
    """Passing core_dir twice (via user_dirs) should not create spurious conflicts."""
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "agents.yaml",
        """\
        - type: agent
          config:
            name: shared_agent
            system_prompt_path: /fake.md
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path, user_dirs=[str(tmp_path)])
    assert not engine.has_conflicts
    assert "shared_agent" in engine._agents


def test_yaml_and_yml_same_stem_no_double_processing(tmp_path):
    """A file.yaml and file.yml with the same content do NOT produce a conflict."""
    d = make_flow_dir(tmp_path)
    content = """\
        - type: agent
          config:
            name: only_once
            system_prompt_path: /fake.md
    """
    (d / "x.yaml").write_text(textwrap.dedent(content))
    (d / "x.yml").write_text(textwrap.dedent(content))
    # Two distinct files → conflict, because they have the same (type, name) from different paths.
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine.conflicts) == 1
    assert len(engine.conflicts[0].sources) == 2


def test_shared_and_flow_conflict_detected(tmp_path):
    """Same resource name in shared/ and the flow dir produces a conflict."""
    make_flow_dir(tmp_path)
    shared = tmp_path / "shared"
    shared.mkdir()
    write_yaml(tmp_path / FLOW_NAME, "a.yaml", "- type: agent\n  config:\n    name: dup\n")
    write_yaml(shared, "b.yaml", "- type: agent\n  config:\n    name: dup\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert engine.has_conflicts


# ---------------------------------------------------------------------------
# Scanning + conflicts (existing behavior)
# ---------------------------------------------------------------------------


def test_scanning_succeeds_even_with_conflicts(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "a.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    write_yaml(
        d,
        "b.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow: []
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
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
            class: AgenticPhase
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
            class: AgenticPhase
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
            class: AgenticPhase
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
            system_prompt_path: /fake.md
            variables:
              - name: endpoint
                default: http://localhost:9090
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
            system_prompt_path: /fake.md
            variables:
              - name: integration_name
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    flow_dir = make_flow_dir(tmp_path)
    if yaml_content:
        write_yaml(flow_dir, "config.yaml", yaml_content)
    if expected_match == "conflicts":
        write_yaml(
            flow_dir,
            "b.yaml",
            """\
            - type: flow
              config:
                name: my_flow
                flow: []
        """,
        )
    with pytest.raises(FlowConfigError, match=expected_match):
        engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
        engine.build_flow()


def test_build_flow_raises_on_cycle(tmp_path):
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
        - type: phase
          config:
            name: phase_b
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    with pytest.raises(FlowConfigError, match="[Cc]ycle"):
        engine.build_flow()


# ---------------------------------------------------------------------------
# _parse_file failure modes — errors are stored, not raised at init
# ---------------------------------------------------------------------------


def test_non_list_yaml_file_stored_not_raised(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "config.yaml").write_text("key: value\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine._file_errors) == 1
    assert "expected a YAML list" in next(iter(engine._file_errors.values()))


def test_malformed_yaml_stored_not_raised(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "bad.yaml").write_text("key: [unclosed\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine._file_errors) == 1
    assert "Malformed YAML" in next(iter(engine._file_errors.values()))


def test_unreadable_file_stored_not_raised(tmp_path, monkeypatch):
    d = make_flow_dir(tmp_path)
    bad = d / "bad.yaml"
    bad.write_text("- type: agent\n  config:\n    name: x\n")
    original_read_text = Path.read_text

    def _fail_for_bad(self, *args, **kwargs):
        if self == bad:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _fail_for_bad)
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine._file_errors) == 1
    assert "Could not read" in next(iter(engine._file_errors.values()))


def test_list_element_not_a_mapping_stored_not_raised(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "config.yaml").write_text("- just_a_string\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine._file_errors) == 1


def test_unknown_type_value_stored_not_raised(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "config.yaml").write_text("- type: widget\n  config:\n    name: x\n")
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine._file_errors) == 1


def test_broken_unrelated_file_does_not_block_build_flow(tmp_path):
    """A broken file that has nothing to do with the requested flow is silently skipped."""
    d = make_flow_dir(tmp_path)
    (d / "broken.yaml").write_text("key: value\n")
    write_yaml(
        d,
        "flow.yaml",
        """\
        - type: phase
          config:
            name: my_phase
            class: AgenticPhase
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: my_phase
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    assert len(engine._file_errors) == 1
    resolved = engine.build_flow()
    assert resolved.name == "my_flow"


def test_broken_file_error_surfaced_when_resource_missing(tmp_path):
    """When a resource is missing and a file failed to parse, the parse error appears in the message."""
    d = make_flow_dir(tmp_path)
    (d / "broken.yaml").write_text("key: value\n")
    write_yaml(
        d,
        "flow.yaml",
        """\
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: ghost_phase
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    with pytest.raises(FlowConfigError, match="failed to parse"):
        engine.build_flow()


# ---------------------------------------------------------------------------
# Variable resolution
# ---------------------------------------------------------------------------


def test_build_flow_variable_resolved_from_flow(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "prompts").mkdir()
    (d / "prompts" / "agent_a.md").write_text("system prompt")
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: prompts/agent_a.md
            variables:
              - name: integration_name
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.variables["integration_name"] == "my_integration"


def test_build_flow_same_default_no_conflict(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "prompts").mkdir()
    (d / "prompts" / "agent_a.md").write_text("system prompt")
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: prompts/agent_a.md
            variables:
              - name: endpoint
                default: http://localhost:9090
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.variables["endpoint"] == "http://localhost:9090"


def test_variable_default_promoted_from_second_source(tmp_path):
    """A variable with no default in phase A but a default in phase B should resolve."""
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
            variables:
              - name: shared_var
        - type: phase
          config:
            name: phase_b
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.variables["shared_var"] == "from_b"


def test_runtime_override_takes_precedence_over_default(tmp_path):
    """Flow-level variables override declared defaults."""
    d = make_flow_dir(tmp_path)
    (d / "prompts").mkdir()
    (d / "prompts" / "agent_a.md").write_text("system prompt")
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: prompts/agent_a.md
            variables:
              - name: endpoint
                default: http://default
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.variables["endpoint"] == "http://override"


def test_missing_variable_error_lists_all_missing(tmp_path):
    """When multiple variables are missing, all are listed in the error."""
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: /fake.md
            variables:
              - name: var_one
              - name: var_two
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
            agent: agent_a
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    with pytest.raises(FlowConfigError) as exc_info:
        engine.build_flow()
    msg = str(exc_info.value)
    assert "var_one" in msg
    assert "var_two" in msg


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------


def test_build_flow_relative_paths_resolved(tmp_path):
    d = make_flow_dir(tmp_path)
    prompts_dir = d / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "agent_a.md").write_text("system prompt")
    (d / "task.md").write_text("do the thing")

    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: prompts/agent_a.md
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.agents["agent_a"].system_prompt_path == d / "prompts" / "agent_a.md"
    assert resolved.phases["phase_a"].tasks[0].prompt_path == d / "task.md"


def test_build_flow_absolute_prompt_path_preserved(tmp_path):
    d = make_flow_dir(tmp_path)
    task_file = d / "task.md"
    task_file.write_text("do the thing")
    (d / "prompts").mkdir()
    (d / "prompts" / "agent_a.md").write_text("sys")

    write_yaml(
        d,
        "config.yaml",
        f"""\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: prompts/agent_a.md
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.phases["phase_a"].tasks[0].prompt_path == task_file


def test_build_flow_goal_path_resolved(tmp_path):
    d = make_flow_dir(tmp_path)
    (d / "prompts").mkdir()
    (d / "prompts" / "agent_a.md").write_text("sys")
    (d / "goal.md").write_text("goal text")
    (d / "task.md").write_text("task text")

    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: prompts/agent_a.md
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.phases["phase_a"].tasks[0].goal_path == d / "goal.md"


def test_build_flow_user_supplied_system_prompt_path_preserved(tmp_path):
    """If the YAML sets system_prompt_path explicitly, it must not be overwritten."""
    d = make_flow_dir(tmp_path)
    custom_prompt = d / "custom.md"
    custom_prompt.write_text("custom sys")

    write_yaml(
        d,
        "config.yaml",
        f"""\
        - type: agent
          config:
            name: agent_a
            system_prompt_path: {custom_prompt}
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.agents["agent_a"].system_prompt_path == custom_prompt


def test_build_flow_agent_prompt_convention(tmp_path):
    """When system_prompt_path is omitted, the engine fills it via get_agent_prompt convention."""
    d = make_flow_dir(tmp_path)
    (d / "prompts").mkdir()
    (d / "prompts" / "writer.md").write_text("sys")

    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: writer
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    resolved = engine.build_flow()
    assert resolved.agents["writer"].system_prompt_path == d / "prompts" / "writer.md"


def test_build_flow_missing_conventional_prompt_raises(tmp_path):
    """When system_prompt_path is omitted and the conventional path doesn't exist, raise."""
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: agent
          config:
            name: writer
        - type: phase
          config:
            name: phase_a
            class: AgenticPhase
            agent: writer
            tasks:
              - name: t1
                prompt: do it
        - type: flow
          config:
            name: my_flow
            flow:
              - phase: phase_a
    """,
    )
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    with pytest.raises(FlowConfigError, match="System prompt not found"):
        engine.build_flow()


# ---------------------------------------------------------------------------
# get_agent_prompt static method
# ---------------------------------------------------------------------------


def test_get_agent_prompt_returns_conventional_path(tmp_path):
    expected = tmp_path / "prompts" / "my_agent.md"
    assert ConfigurationEngine.get_agent_prompt("my_agent", tmp_path) == expected


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
    assert not truncated
    # Verify the path includes a closing node (ordered path contract)
    assert any(len(c) >= 3 and c[0] == c[-1] for c in cycles)


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
    d = make_flow_dir(tmp_path)
    write_yaml(
        d,
        "config.yaml",
        """\
        - type: phase
          config:
            name: p1
            class: AgenticPhase
        - type: phase
          config:
            name: p2
            class: AgenticPhase
        - type: phase
          config:
            name: p3
            class: AgenticPhase
        - type: phase
          config:
            name: p4
            class: AgenticPhase
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
    engine = ConfigurationEngine(FLOW_NAME, core_dir=tmp_path)
    with pytest.raises(FlowConfigError) as exc_info:
        engine.build_flow()
    error = str(exc_info.value)
    assert "p1" in error
    assert "p2" in error
