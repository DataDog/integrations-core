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
    ResolvedFlow,
    ResourceEnvelope,
    TaskConfig,
)

# ---------------------------------------------------------------------------
# TaskConfig
# ---------------------------------------------------------------------------


def test_task_rejects_both_prompt_and_ref():
    with pytest.raises(ValidationError):
        TaskConfig(name="t", prompt="x", prompt_ref="y")


def test_task_rejects_neither_prompt_nor_ref():
    with pytest.raises(ValidationError):
        TaskConfig(name="t")


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


def test_checkpoint_requires_exactly_one_memory_source():
    with pytest.raises(ValidationError):
        CheckpointConfig()  # neither
    CheckpointConfig(memory_prompt="hi")  # ok
    CheckpointConfig(memory_prompt_ref="m")  # ok


def test_checkpoint_rejects_both_sources():
    with pytest.raises(ValidationError):
        CheckpointConfig(memory_prompt="hi", memory_prompt_ref="ref")


# ---------------------------------------------------------------------------
# AgentConfig
# ---------------------------------------------------------------------------


def test_agent_rejects_unknown_tools():
    with pytest.raises(ValidationError):
        AgentConfig(tools=["nonexistent_tool"])


def test_agent_accepts_known_tools():
    from ddev.ai.tools.registry import ToolRegistry

    known_names = ToolRegistry.available_tool_names()
    assert known_names, "ToolRegistry exposes no tool names; cannot verify known-tool acceptance"
    known = next(iter(known_names))
    a = AgentConfig(tools=[known])
    assert known in a.tools


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


def test_resource_envelope_invalid_type():
    from pydantic import TypeAdapter

    ta = TypeAdapter(ResourceEnvelope)
    with pytest.raises(ValidationError):
        ta.validate_python({"type": "unknown", "config": {}})


# ---------------------------------------------------------------------------
# ResolvedFlow
# ---------------------------------------------------------------------------


def test_resolved_flow_is_frozen():
    rf = ResolvedFlow(
        name="flow",
        agents={},
        phases={},
        flow=[],
        variables={},
    )
    with pytest.raises((AttributeError, TypeError)):
        rf.name = "other"  # type: ignore[misc]
