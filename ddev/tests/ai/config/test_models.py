# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ddev.ai.config.models import (
    AgentConfig,
    CheckpointConfig,
    FlowEnvelope,
    PhaseConfig,
    PhaseEnvelope,
    ResourceEnvelope,
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


# ---------------------------------------------------------------------------
# PhaseConfig
# ---------------------------------------------------------------------------


def test_phase_class_alias():
    p = PhaseConfig.model_validate({"name": "p", "class": "InspectEndpointPhase"})
    assert p.class_ == "InspectEndpointPhase"


def test_phase_defaults_class_to_agentic():
    assert PhaseConfig(name="p").class_ == "AgenticPhase"


# ---------------------------------------------------------------------------
# PhaseEnvelope / FlowEnvelope / ResourceEnvelope discriminated union
# ---------------------------------------------------------------------------


def test_resource_envelope_phase():
    from pydantic import TypeAdapter

    ta = TypeAdapter(ResourceEnvelope)
    env = ta.validate_python({"type": "phase", "config": {"name": "p"}})
    assert isinstance(env, PhaseEnvelope)


def test_resource_envelope_flow():
    from pydantic import TypeAdapter

    ta = TypeAdapter(ResourceEnvelope)
    env = ta.validate_python({"type": "flow", "config": {"name": "f", "flow": [{"phase": "x"}]}})
    assert isinstance(env, FlowEnvelope)
