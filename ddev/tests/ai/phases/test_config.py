# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from pydantic import ValidationError

from ddev.ai.phases.config import (
    AgentConfig,
    CheckpointConfig,
    FlowConfig,
    FlowConfigError,
    PhaseConfig,
    TaskConfig,
)

# ---------------------------------------------------------------------------
# TaskConfig
# ---------------------------------------------------------------------------


def test_task_config_with_prompt():
    tc = TaskConfig(name="t1", prompt="Do it.")
    assert tc.prompt == "Do it."
    assert tc.prompt_path is None


def test_task_config_with_prompt_path():
    tc = TaskConfig(name="t1", prompt_path="prompts/task.md")
    assert tc.prompt is None
    assert tc.prompt_path is not None


def test_task_config_both_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        TaskConfig(name="t1", prompt="Do it.", prompt_path="prompts/task.md")


def test_task_config_neither_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        TaskConfig(name="t1")


def test_task_config_extra_field_raises():
    with pytest.raises(ValidationError, match="extra"):
        TaskConfig(name="t1", prompt="Do it.", unknown_field="x")


# ---------------------------------------------------------------------------
# CheckpointConfig
# ---------------------------------------------------------------------------


def test_checkpoint_config_with_memory_prompt():
    cc = CheckpointConfig(memory_prompt="List files.")
    assert cc.memory_prompt == "List files."


def test_checkpoint_config_with_memory_prompt_path():
    cc = CheckpointConfig(memory_prompt_path="prompts/mem.md")
    assert cc.memory_prompt_path is not None


def test_checkpoint_config_both_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        CheckpointConfig(memory_prompt="List files.", memory_prompt_path="prompts/mem.md")


def test_checkpoint_config_neither_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        CheckpointConfig()


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


def test_agent_config_valid_tools():
    ac = AgentConfig(tools=["read_file", "grep"])
    assert ac.tools == ["read_file", "grep"]


def test_agent_config_unknown_tool_raises():
    with pytest.raises(ValidationError, match="Unknown tool names"):
        AgentConfig(tools=["read_file", "teleport"])


def test_agent_config_empty_tools():
    ac = AgentConfig()
    assert ac.tools == []


def test_agent_config_optional_fields():
    ac = AgentConfig(model="claude-opus-4-5", max_tokens=4096)
    assert ac.model == "claude-opus-4-5"
    assert ac.max_tokens == 4096


# ---------------------------------------------------------------------------
# PhaseConfig
# ---------------------------------------------------------------------------


def test_phase_config_defaults():
    pc = PhaseConfig(agent="writer", tasks=[TaskConfig(name="t1", prompt="Do it.")])
    assert pc.type == "Phase"
    assert pc.context_compact_threshold_pct == 80
    assert pc.checkpoint is None


def test_phase_config_empty_tasks_raises():
    with pytest.raises(ValidationError, match="at least one task"):
        PhaseConfig(agent="writer", tasks=[])


def test_phase_config_with_checkpoint():
    pc = PhaseConfig(
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Do it.")],
        checkpoint=CheckpointConfig(memory_prompt="List files."),
    )
    assert pc.checkpoint is not None


# ---------------------------------------------------------------------------
# FlowConfig cross-reference validation
# ---------------------------------------------------------------------------


def _minimal_config(**overrides) -> dict:
    base = {
        "agents": {"writer": {"tools": []}},
        "phases": {"p1": {"agent": "writer", "tasks": [{"name": "t1", "prompt": "Do it."}]}},
        "flow": [{"phase": "p1"}],
    }
    base.update(overrides)
    return base


def test_flow_config_minimal_valid():
    config = FlowConfig.model_validate(_minimal_config())
    assert "p1" in config.phases


def test_flow_config_unknown_phase_in_flow():
    raw = _minimal_config()
    raw["flow"] = [{"phase": "nonexistent"}]
    with pytest.raises(ValidationError, match="unknown phase"):
        FlowConfig.model_validate(raw)


def test_flow_config_unknown_dependency():
    raw = _minimal_config()
    raw["flow"] = [{"phase": "p1", "dependencies": ["nonexistent"]}]
    with pytest.raises(ValidationError, match="unknown phase"):
        FlowConfig.model_validate(raw)


def test_flow_config_unknown_agent_in_phase():
    raw = _minimal_config()
    raw["phases"]["p1"]["agent"] = "nonexistent"
    with pytest.raises(ValidationError, match="unknown agent"):
        FlowConfig.model_validate(raw)


def test_flow_config_with_variables():
    raw = _minimal_config(variables={"project": "myproj"})
    config = FlowConfig.model_validate(raw)
    assert config.variables["project"] == "myproj"


def test_flow_config_multiple_phases_and_deps():
    raw = {
        "agents": {"writer": {"tools": []}},
        "phases": {
            "p1": {"agent": "writer", "tasks": [{"name": "t1", "prompt": "Do it."}]},
            "p2": {"agent": "writer", "tasks": [{"name": "t2", "prompt": "Review it."}]},
        },
        "flow": [
            {"phase": "p1"},
            {"phase": "p2", "dependencies": ["p1"]},
        ],
    }
    config = FlowConfig.model_validate(raw)
    assert len(config.flow) == 2
    assert config.flow[1].dependencies == ["p1"]


def test_flow_config_extra_field_raises():
    raw = _minimal_config()
    raw["extra"] = "boom"
    with pytest.raises(ValidationError, match="extra"):
        FlowConfig.model_validate(raw)


# ---------------------------------------------------------------------------
# FlowConfig.from_yaml
# ---------------------------------------------------------------------------


def test_from_yaml_valid(tmp_path):
    # Set up PhaseRegistry so _validate_files passes
    from ddev.ai.phases.base import Phase, PhaseRegistry

    PhaseRegistry._registry["Phase"] = Phase

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "writer.md").write_text("system prompt")

    flow_yaml = tmp_path / "flow.yaml"
    flow_yaml.write_text(
        """\
agents:
  writer:
    tools: []
phases:
  p1:
    agent: writer
    tasks:
      - name: t1
        prompt: "Do it."
flow:
  - phase: p1
"""
    )
    config = FlowConfig.from_yaml(flow_yaml, tmp_path)
    assert "p1" in config.phases


def test_from_yaml_missing_system_prompt(tmp_path):
    from ddev.ai.phases.base import Phase, PhaseRegistry

    PhaseRegistry._registry["Phase"] = Phase

    (tmp_path / "prompts").mkdir()

    flow_yaml = tmp_path / "flow.yaml"
    flow_yaml.write_text(
        """\
agents:
  writer:
    tools: []
phases:
  p1:
    agent: writer
    tasks:
      - name: t1
        prompt: "Do it."
flow:
  - phase: p1
"""
    )
    with pytest.raises(FlowConfigError, match="System prompt not found"):
        FlowConfig.from_yaml(flow_yaml, tmp_path)


def test_from_yaml_unknown_phase_type(tmp_path):
    from ddev.ai.phases.base import Phase, PhaseRegistry

    PhaseRegistry._registry["Phase"] = Phase

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "writer.md").write_text("system prompt")

    flow_yaml = tmp_path / "flow.yaml"
    flow_yaml.write_text(
        """\
agents:
  writer:
    tools: []
phases:
  p1:
    type: NonexistentPhase
    agent: writer
    tasks:
      - name: t1
        prompt: "Do it."
flow:
  - phase: p1
"""
    )
    with pytest.raises(FlowConfigError, match="unknown type"):
        FlowConfig.from_yaml(flow_yaml, tmp_path)


def test_from_yaml_missing_task_prompt_path(tmp_path):
    from ddev.ai.phases.base import Phase, PhaseRegistry

    PhaseRegistry._registry["Phase"] = Phase

    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "writer.md").write_text("system prompt")

    flow_yaml = tmp_path / "flow.yaml"
    flow_yaml.write_text(
        """\
agents:
  writer:
    tools: []
phases:
  p1:
    agent: writer
    tasks:
      - name: t1
        prompt_path: prompts/nonexistent.md
flow:
  - phase: p1
"""
    )
    with pytest.raises(FlowConfigError, match="prompt_path not found"):
        FlowConfig.from_yaml(flow_yaml, tmp_path)


def test_from_yaml_invalid_yaml(tmp_path):
    flow_yaml = tmp_path / "flow.yaml"
    flow_yaml.write_text(": invalid: yaml: [")
    with pytest.raises(FlowConfigError, match="Failed to load"):
        FlowConfig.from_yaml(flow_yaml, tmp_path)


def test_from_yaml_missing_file(tmp_path):
    with pytest.raises(FlowConfigError, match="Failed to load"):
        FlowConfig.from_yaml(tmp_path / "nonexistent.yaml", tmp_path)
