# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import (
    AgentConfig,
    CheckpointConfig,
    FlowConfig,
    PhaseConfig,
    TaskConfig,
    VariableDeclaration,
)

from .utils import make_agent_config, make_provider_registry

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


def test_agent_requires_provider_registry_context():
    with pytest.raises(ValidationError, match="Agent provider registry is required"):
        AgentConfig()


def test_agent_validates_default_provider_against_registry():
    registry = make_provider_registry("anthropic")

    config = AgentConfig.model_validate({}, context={"provider_registry": registry})

    assert config.provider == "anthropic"


def test_agent_rejects_default_provider_when_not_configured():
    with pytest.raises(ValidationError, match="Agent provider 'anthropic' is not available"):
        AgentConfig.model_validate({}, context={"provider_registry": AgentProviderRegistry()})


def test_agent_rejects_unknown_tools():
    with pytest.raises(ValidationError):
        make_agent_config(tools=["nonexistent_tool"])


# ---------------------------------------------------------------------------
# Name pattern (shared across identity fields)
# ---------------------------------------------------------------------------


def test_phase_name_pattern_rejects_invalid():
    with pytest.raises(ValidationError):
        PhaseConfig(name="invalid/name")


def test_flow_name_pattern_rejects_invalid():
    with pytest.raises(ValidationError):
        FlowConfig(name="invalid name!", flow=[])


@pytest.mark.parametrize("name", ["invalid name!", "my-var", "my.var", "1var", ""])
def test_variable_name_rejects_non_template_identifiers(name):
    with pytest.raises(ValidationError):
        VariableDeclaration(name=name)


@pytest.mark.parametrize("name", ["x", "my_var", "_hidden", "var1", "API_KEY", "MyVar"])
def test_variable_name_accepts_template_identifiers(name):
    assert VariableDeclaration(name=name).name == name


@pytest.mark.parametrize("bad_key", ["my-var", "my.var", "1var"])
def test_flow_variables_reject_non_template_identifiers(bad_key):
    with pytest.raises(ValidationError):
        FlowConfig(name="demo", variables={bad_key: "v"}, flow=[])


def test_flow_variables_accept_template_identifiers():
    fc = FlowConfig(name="demo", variables={"topic": "cats", "_n": "1", "API_KEY": "v"}, flow=[])
    assert fc.variables == {"topic": "cats", "_n": "1", "API_KEY": "v"}
