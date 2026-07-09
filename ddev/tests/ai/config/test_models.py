# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ddev.ai.config.models import (
    AgentConfig,
    CheckpointConfig,
    FlowConfig,
    PhaseConfig,
    TaskConfig,
    VariableDeclaration,
)

# ---------------------------------------------------------------------------
# TaskConfig
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [{"prompt": "x", "prompt_ref": "y"}, {}],
    ids=["both_set", "neither_set"],
)
def test_task_prompt_source_validation(kwargs):
    with pytest.raises(ValidationError):
        TaskConfig(name="t", **kwargs)


def test_task_context_flags_mutually_exclusive():
    with pytest.raises(ValidationError):
        TaskConfig(name="t", prompt="p", clear_context_before=True, compact_context_before=True)


def test_task_goal_consistency_both_set():
    with pytest.raises(ValidationError):
        TaskConfig(name="t", prompt="p", goal="g", goal_ref="r")


def test_task_max_goal_attempts_without_goal():
    with pytest.raises(ValidationError):
        TaskConfig(name="t", prompt="p", max_goal_attempts=3)


def test_task_max_goal_attempts_below_one():
    with pytest.raises(ValidationError):
        TaskConfig(name="t", prompt="p", goal="g", max_goal_attempts=0)


def test_task_name_pattern_rejects_invalid():
    with pytest.raises(ValidationError):
        TaskConfig(name="invalid name!", prompt="p")


# ---------------------------------------------------------------------------
# CheckpointConfig
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [{}, {"memory_prompt": "hi", "memory_prompt_ref": "ref"}],
    ids=["neither_set", "both_set"],
)
def test_checkpoint_memory_source_validation_rejects(kwargs):
    with pytest.raises(ValidationError):
        CheckpointConfig(**kwargs)


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


def test_agent_rejects_unknown_tools():
    with pytest.raises(ValidationError):
        AgentConfig(tools=["nonexistent_tool"])


# ---------------------------------------------------------------------------
# Name pattern (shared across identity fields)
# ---------------------------------------------------------------------------


def test_phase_name_pattern_rejects_invalid():
    with pytest.raises(ValidationError):
        PhaseConfig(name="invalid/name")


def test_flow_name_pattern_rejects_invalid():
    with pytest.raises(ValidationError):
        FlowConfig(name="invalid name!", flow=[])


def test_variable_name_pattern_rejects_invalid():
    with pytest.raises(ValidationError):
        VariableDeclaration(name="invalid name!")
