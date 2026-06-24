# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.models import (
    AgentConfig,
    AgentEnvelope,
    CheckpointConfig,
    FlowEnvelope,
    PhaseConfig,
    PhaseEnvelope,
    ResourceEnvelope,
    TaskConfig,
)


# ---------------------------------------------------------------------------
# AgentConfig — custom tools validator
# ---------------------------------------------------------------------------


def test_agent_config_unknown_tool_raises():
    with pytest.raises(ValidationError, match="Unknown tool names"):
        AgentConfig.model_validate({"name": "a", "tools": ["teleport"]})


# ---------------------------------------------------------------------------
# PhaseConfig — class alias
# ---------------------------------------------------------------------------


def test_phase_config_class_alias():
    p = PhaseConfig.model_validate({"name": "my_phase", "class": "AgenticPhase"})
    assert p.class_ == "AgenticPhase"


# ---------------------------------------------------------------------------
# ResourceEnvelope — discriminated union
# ---------------------------------------------------------------------------


def test_resource_envelope_agent_type():
    adapter = TypeAdapter(ResourceEnvelope)
    result = adapter.validate_python({"type": "agent", "config": {"name": "a", "system_prompt_path": "/p.md"}})
    assert isinstance(result, AgentEnvelope)


def test_resource_envelope_phase_type():
    adapter = TypeAdapter(ResourceEnvelope)
    result = adapter.validate_python({"type": "phase", "config": {"name": "p", "class": "AgenticPhase"}})
    assert isinstance(result, PhaseEnvelope)


def test_resource_envelope_flow_type():
    adapter = TypeAdapter(ResourceEnvelope)
    result = adapter.validate_python({"type": "flow", "config": {"name": "f", "flow": []}})
    assert isinstance(result, FlowEnvelope)


def test_resource_envelope_unknown_type_raises():
    adapter = TypeAdapter(ResourceEnvelope)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "widget", "config": {"name": "x"}})


# ---------------------------------------------------------------------------
# TaskConfig — custom model validators
# ---------------------------------------------------------------------------


def test_task_config_both_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        TaskConfig(name="t1", prompt="Do it.", prompt_path="prompts/task.md")


def test_task_config_context_flags_mutually_exclusive():
    with pytest.raises(ValidationError, match="mutually exclusive"):
        TaskConfig(name="t1", prompt="x", clear_context_before=True, compact_context_before=True)


def test_task_config_neither_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        TaskConfig(name="t1")


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
# CheckpointConfig — custom model validator
# ---------------------------------------------------------------------------


def test_checkpoint_config_both_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        CheckpointConfig(memory_prompt="List files.", memory_prompt_path="prompts/mem.md")


def test_checkpoint_config_neither_set_raises():
    with pytest.raises(ValidationError, match="Exactly one"):
        CheckpointConfig()
