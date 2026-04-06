# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
import yaml

from ddev.ai.phases.config import PhaseConfig, PhaseConfigError

# ---------------------------------------------------------------------------
# Valid config
# ---------------------------------------------------------------------------


def test_from_yaml_loads_name(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "my_phase",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.name == "my_phase"


def test_from_yaml_loads_depends_on(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": ["phase_1", "phase_2"],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.depends_on == ["phase_1", "phase_2"]


def test_from_yaml_resolves_prompt_paths_relative_to_config(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.system_prompt_path == phase_dir / "prompts" / "system.md"
    assert config.task_prompt_paths == [phase_dir / "prompts" / "task.md"]


def test_from_yaml_loads_checkpoint_schema(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {"items": 0, "done": False},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.checkpoint_schema == {"items": 0, "done": False}


# ---------------------------------------------------------------------------
# AgentConfig defaults
# ---------------------------------------------------------------------------


def test_agent_config_defaults_to_none(tmp_path):
    """Omitting the agent block means model and max_tokens are None — let the agent use its own defaults."""
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.agent.model is None
    assert config.agent.max_tokens is None
    assert config.agent.context_reset_threshold_pct == 80


def test_agent_config_explicit_values(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
                "agent": {"model": "claude-haiku-4-5", "max_tokens": 4096, "context_reset_threshold_pct": 70},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.agent.model == "claude-haiku-4-5"
    assert config.agent.max_tokens == 4096
    assert config.agent.context_reset_threshold_pct == 70


def test_react_config_default(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.react.max_iterations == 50


def test_react_config_explicit_value(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "prompts" / "task.md").write_text("task")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
                "react": {"max_iterations": 10},
            }
        )
    )
    config = PhaseConfig.from_yaml(phase_dir / "config.yaml")
    assert config.react.max_iterations == 10


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_missing_name_raises(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": ["prompts/task.md"]},
            }
        )
    )
    with pytest.raises(PhaseConfigError, match="name"):
        PhaseConfig.from_yaml(phase_dir / "config.yaml")


def test_missing_system_prompt_raises(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"tasks": ["prompts/task.md"]},
                "checkpoint_schema": {},
            }
        )
    )
    with pytest.raises(PhaseConfigError, match="prompts.system"):
        PhaseConfig.from_yaml(phase_dir / "config.yaml")


def test_empty_task_prompts_raises(tmp_path):
    phase_dir = tmp_path / "p"
    phase_dir.mkdir()
    (phase_dir / "prompts").mkdir()
    (phase_dir / "prompts" / "system.md").write_text("sys")
    (phase_dir / "config.yaml").write_text(
        yaml.dump(
            {
                "name": "p",
                "depends_on": [],
                "tools": [],
                "prompts": {"system": "prompts/system.md", "tasks": []},
                "checkpoint_schema": {},
            }
        )
    )
    with pytest.raises(PhaseConfigError, match="no task prompts"):
        PhaseConfig.from_yaml(phase_dir / "config.yaml")


def test_nonexistent_file_raises(tmp_path):
    with pytest.raises(PhaseConfigError):
        PhaseConfig.from_yaml(tmp_path / "does_not_exist.yaml")


def test_invalid_yaml_raises(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text(": : : invalid yaml : : :")
    with pytest.raises(PhaseConfigError):
        PhaseConfig.from_yaml(bad)


def test_non_mapping_yaml_raises(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text("- item1\n- item2\n")
    with pytest.raises(PhaseConfigError, match="mapping"):
        PhaseConfig.from_yaml(bad)
