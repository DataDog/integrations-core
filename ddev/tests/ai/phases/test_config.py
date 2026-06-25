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
    assert tc.prompt_ref is None


def test_task_config_with_prompt_ref():
    tc = TaskConfig(name="t1", prompt_ref="my_prompt")
    assert tc.prompt_ref == "my_prompt"
    assert tc.prompt is None


def test_task_config_both_prompt_and_ref_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        TaskConfig(name="t1", prompt="Do it.", prompt_ref="my_prompt")


def test_task_config_neither_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        TaskConfig(name="t1")


def test_task_config_extra_field_raises():
    with pytest.raises(ValidationError, match="extra"):
        TaskConfig(name="t1", prompt="Do it.", unknown_field="x")


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"name": "t", "prompt": "x", "goal": "g", "goal_ref": "g_ref"}, "At most one of 'goal' or 'goal_ref'"),
        ({"name": "t", "prompt": "x", "max_goal_attempts": 3}, "'max_goal_attempts' may only be set"),
        ({"name": "t", "prompt": "x", "goal": "g", "max_goal_attempts": 0}, "must be at least 1"),
    ],
    ids=["both_goal_sources", "attempts_without_goal", "attempts_below_one"],
)
def test_task_config_goal_validation_rejects(kwargs, match):
    with pytest.raises(ValidationError, match=match):
        TaskConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": "t", "prompt": "x", "goal": "verify it"},
        {"name": "t", "prompt": "x", "goal_ref": "my_goal"},
        {"name": "t", "prompt": "x", "goal": "verify it", "max_goal_attempts": 7},
    ],
    ids=["goal", "goal_ref", "goal_with_custom_attempts"],
)
def test_task_config_goal_accepts_valid(kwargs):
    tc = TaskConfig(**kwargs)
    assert (tc.goal is not None) ^ (tc.goal_ref is not None)
    assert tc.max_goal_attempts == kwargs.get("max_goal_attempts", 5)


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


def test_agent_config_defaults():
    ac = AgentConfig()
    assert ac.tools == []
    assert ac.provider == "anthropic"
    assert ac.model is None
    assert ac.max_tokens is None
    assert ac.system_prompt == ""


def test_agent_config_web_search_validates():
    ac = AgentConfig(tools=["read_file", "web_search"])
    assert "web_search" in ac.tools


def test_agent_config_web_fetch_validates():
    ac = AgentConfig(tools=["read_file", "web_fetch"])
    assert "web_fetch" in ac.tools


def test_agent_config_unknown_tool_raises():
    with pytest.raises(ValidationError, match="Unknown tool names"):
        AgentConfig(tools=["teleport"])


def test_agent_config_system_prompt_set():
    ac = AgentConfig(system_prompt="You are a writer.")
    assert ac.system_prompt == "You are a writer."


# ---------------------------------------------------------------------------
# PhaseConfig
# ---------------------------------------------------------------------------


def test_phase_config_defaults():
    pc = PhaseConfig(agent="writer", tasks=[TaskConfig(name="t1", prompt="Do it.")])
    assert pc.type == "AgenticPhase"
    assert pc.context_compact_threshold_pct == 80
    assert pc.checkpoint is None


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


def test_flow_config_dependency_not_scheduled_in_flow():
    raw = {
        "agents": {"writer": {"tools": []}},
        "phases": {
            "p1": {"agent": "writer", "tasks": [{"name": "t1", "prompt": "Do it."}]},
            "p2": {"agent": "writer", "tasks": [{"name": "t2", "prompt": "Review it."}]},
        },
        "flow": [{"phase": "p2", "dependencies": ["p1"]}],
    }
    with pytest.raises(ValidationError, match="not scheduled in flow"):
        FlowConfig.model_validate(raw)


def test_flow_config_duplicate_phase_raises():
    raw = _minimal_config()
    raw["flow"] = [{"phase": "p1"}, {"phase": "p1"}]
    with pytest.raises(ValidationError, match="Duplicate phase"):
        FlowConfig.model_validate(raw)


def test_flow_config_unknown_agent_in_phase():
    raw = _minimal_config()
    raw["phases"]["p1"]["agent"] = "nonexistent"
    with pytest.raises(ValidationError, match="unknown agent"):
        FlowConfig.model_validate(raw)


def test_flow_config_phase_without_agent_validates():
    raw = {
        "agents": {"writer": {"tools": []}},
        "phases": {
            "p1": {"agent": "writer", "tasks": [{"name": "t1", "prompt": "Do it."}]},
            "noop": {"type": "SomeCustomPhase"},
        },
        "flow": [
            {"phase": "p1"},
            {"phase": "noop", "dependencies": ["p1"]},
        ],
    }
    config = FlowConfig.model_validate(raw)
    assert config.phases["noop"].agent is None
    assert config.phases["noop"].tasks == []


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


def test_from_yaml_invalid_yaml(tmp_path):
    flow_yaml = tmp_path / "flow.yaml"
    flow_yaml.write_text(": invalid: yaml: [")
    with pytest.raises(FlowConfigError, match="Failed to load"):
        FlowConfig.from_yaml(flow_yaml, tmp_path)


def test_from_yaml_missing_file(tmp_path):
    with pytest.raises(FlowConfigError, match="Failed to load"):
        FlowConfig.from_yaml(tmp_path / "nonexistent.yaml", tmp_path)


# ---------------------------------------------------------------------------
# FlowConfig cycle detection via model_validate
# ---------------------------------------------------------------------------


def _three_phase_config() -> dict:
    agent = {"tools": []}
    task = {"name": "t", "prompt": "Do it."}
    return {
        "agents": {"writer": agent},
        "phases": {
            "p1": {"agent": "writer", "tasks": [task]},
            "p2": {"agent": "writer", "tasks": [task]},
            "p3": {"agent": "writer", "tasks": [task]},
        },
    }


def test_flow_config_direct_cycle_raises():
    raw = _three_phase_config()
    raw["flow"] = [
        {"phase": "p1", "dependencies": ["p2"]},
        {"phase": "p2", "dependencies": ["p1"]},
    ]
    with pytest.raises(ValidationError, match="Cycle"):
        FlowConfig.model_validate(raw)


def test_flow_config_three_node_cycle_raises():
    raw = _three_phase_config()
    raw["flow"] = [
        {"phase": "p1", "dependencies": ["p3"]},
        {"phase": "p2", "dependencies": ["p1"]},
        {"phase": "p3", "dependencies": ["p2"]},
    ]
    with pytest.raises(ValidationError, match="Cycle"):
        FlowConfig.model_validate(raw)


def test_flow_config_acyclic_chain_ok():
    raw = _three_phase_config()
    raw["flow"] = [
        {"phase": "p1"},
        {"phase": "p2", "dependencies": ["p1"]},
        {"phase": "p3", "dependencies": ["p1"]},
    ]
    config = FlowConfig.model_validate(raw)
    assert len(config.flow) == 3


def test_flow_disjoined_graphs_ok():
    agent = {"tools": []}
    task = {"name": "t", "prompt": "Do it."}
    raw = {
        "agents": {"writer": agent},
        "phases": {
            "p1": {"agent": "writer", "tasks": [task]},
            "p2": {"agent": "writer", "tasks": [task]},
            "p3": {"agent": "writer", "tasks": [task]},
            "p4": {"agent": "writer", "tasks": [task]},
        },
        "flow": [
            {"phase": "p1"},
            {"phase": "p2", "dependencies": ["p1"]},
            {"phase": "p3"},
            {"phase": "p4", "dependencies": ["p3"]},
        ],
    }
    config = FlowConfig.model_validate(raw)
    assert len(config.flow) == 4


def test_flow_config_self_dependency_raises():
    raw = _minimal_config()
    raw["flow"] = [{"phase": "p1", "dependencies": ["p1"]}]
    with pytest.raises(ValidationError, match="Cycle"):
        FlowConfig.model_validate(raw)


def test_flow_config_two_independent_cycles_reports_both():
    agent = {"tools": []}
    task = {"name": "t", "prompt": "Do it."}
    raw = {
        "agents": {"writer": agent},
        "phases": {
            "p1": {"agent": "writer", "tasks": [task]},
            "p2": {"agent": "writer", "tasks": [task]},
            "p3": {"agent": "writer", "tasks": [task]},
            "p4": {"agent": "writer", "tasks": [task]},
        },
        "flow": [
            # dependency edges: p1→p3→p2→p1 and p1→p4→p2→p1
            {"phase": "p1", "dependencies": ["p3", "p4"]},
            {"phase": "p2", "dependencies": ["p1"]},
            {"phase": "p3", "dependencies": ["p2"]},
            {"phase": "p4", "dependencies": ["p2"]},
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        FlowConfig.model_validate(raw)
    error = str(exc_info.value)
    assert "Cycle" in error
    assert "p1 → p3 → p2 → p1" in error
    assert "p1 → p4 → p2 → p1" in error
