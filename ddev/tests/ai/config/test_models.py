# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ddev.ai.config.models import (
    AgentConfig,
    CheckpointConfig,
    TaskConfig,
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


@pytest.mark.parametrize("flag", ["clear_context_before", "compact_context_before"], ids=["clear", "compact"])
def test_task_accepts_single_context_flag(flag):
    t = TaskConfig(name="t", prompt="p", **{flag: True})
    other = "compact_context_before" if flag == "clear_context_before" else "clear_context_before"
    assert getattr(t, flag) is True
    assert getattr(t, other) is False


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


def test_checkpoint_memory_source_validation_accepts_exactly_one():
    CheckpointConfig(memory_prompt="hi")
    CheckpointConfig(memory_prompt_ref="m")


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


def test_agent_rejects_unknown_tools():
    with pytest.raises(ValidationError):
        AgentConfig(tools=["nonexistent_tool"])
