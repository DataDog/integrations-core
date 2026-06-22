# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from pydantic import ValidationError

from ddev.ai.config.models import AgentConfig, CheckpointConfig, PhaseConfig, TaskConfig

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


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"name": "t", "prompt": "x", "goal": "g", "goal_path": "g.md"}, "At most one of 'goal' or 'goal_path'"),
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
        {"name": "t", "prompt": "x", "goal_path": "g.md"},
        {"name": "t", "prompt": "x", "goal": "verify it", "max_goal_attempts": 7},
    ],
    ids=["goal", "goal_path", "goal_with_custom_attempts"],
)
def test_task_config_goal_accepts_valid(kwargs):
    tc = TaskConfig(**kwargs)
    assert (tc.goal is not None) ^ (tc.goal_path is not None)
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


def test_agent_config_valid_tools():
    ac = AgentConfig(name="a", tools=["read_file", "grep"])
    assert ac.tools == ["read_file", "grep"]


def test_agent_config_unknown_tool_raises():
    with pytest.raises(ValidationError, match="Unknown tool names"):
        AgentConfig(name="a", tools=["read_file", "teleport"])


def test_agent_config_empty_tools():
    ac = AgentConfig(name="a")
    assert ac.tools == []


def test_agent_config_optional_fields():
    ac = AgentConfig(name="a", model="claude-opus-4-5", max_tokens=4096)
    assert ac.model == "claude-opus-4-5"
    assert ac.max_tokens == 4096


def test_agent_config_name_required():
    with pytest.raises(ValidationError):
        AgentConfig(tools=[])


# ---------------------------------------------------------------------------
# PhaseConfig
# ---------------------------------------------------------------------------


def test_phase_config_defaults():
    pc = PhaseConfig(
        name="my_phase", class_="AgenticPhase", agent="writer", tasks=[TaskConfig(name="t1", prompt="Do it.")]
    )
    assert pc.class_ == "AgenticPhase"
    assert pc.context_compact_threshold_pct == 80
    assert pc.checkpoint is None


def test_phase_config_with_checkpoint():
    pc = PhaseConfig(
        name="my_phase",
        class_="AgenticPhase",
        agent="writer",
        tasks=[TaskConfig(name="t1", prompt="Do it.")],
        checkpoint=CheckpointConfig(memory_prompt="List files."),
    )
    assert pc.checkpoint is not None


def test_phase_config_name_required():
    with pytest.raises(ValidationError):
        PhaseConfig(agent="writer")
