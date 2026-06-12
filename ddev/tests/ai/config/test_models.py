# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import TypeAdapter, ValidationError

from ddev.ai.config.models import (
    AgentConfig,
    AgentEnvelope,
    FlowConfig,
    FlowEnvelope,
    PhaseConfig,
    PhaseEnvelope,
    ResourceEnvelope,
    VariableDeclaration,
)


def test_variable_declaration_with_default():
    v = VariableDeclaration.model_validate({"name": "endpoint", "default": "http://localhost"})
    assert v.name == "endpoint"
    assert v.default == "http://localhost"


def test_variable_declaration_without_default():
    v = VariableDeclaration.model_validate({"name": "integration_name"})
    assert v.default is None


def test_agent_config_requires_name():
    with pytest.raises(ValidationError):
        AgentConfig.model_validate({"provider": "anthropic"})


def test_agent_config_minimal():
    a = AgentConfig.model_validate({"name": "my_agent"})
    assert a.name == "my_agent"
    assert a.provider == "anthropic"
    assert a.variables == []


def test_phase_config_class_field():
    p = PhaseConfig.model_validate({"name": "my_phase", "class": "AgenticPhase"})
    assert p.name == "my_phase"
    assert p.class_ == "AgenticPhase"


def test_phase_config_requires_name():
    with pytest.raises(ValidationError):
        PhaseConfig.model_validate({"class": "AgenticPhase"})


def test_flow_config_requires_name():
    with pytest.raises(ValidationError):
        FlowConfig.model_validate({"flow": []})


def test_flow_config_variables_are_values():
    f = FlowConfig.model_validate(
        {
            "name": "my_flow",
            "variables": {"integration_name": "my_integration"},
            "flow": [],
        }
    )
    assert f.variables == {"integration_name": "my_integration"}


def test_agent_config_unknown_tool_raises():
    with pytest.raises(ValidationError, match="Unknown tool names"):
        AgentConfig.model_validate({"name": "a", "tools": ["teleport"]})


def test_resource_envelope_agent_type():
    adapter = TypeAdapter(ResourceEnvelope)
    result = adapter.validate_python({"type": "agent", "config": {"name": "a"}})
    assert isinstance(result, AgentEnvelope)


def test_resource_envelope_phase_type():
    adapter = TypeAdapter(ResourceEnvelope)
    result = adapter.validate_python({"type": "phase", "config": {"name": "p"}})
    assert isinstance(result, PhaseEnvelope)


def test_resource_envelope_flow_type():
    adapter = TypeAdapter(ResourceEnvelope)
    result = adapter.validate_python({"type": "flow", "config": {"name": "f", "flow": []}})
    assert isinstance(result, FlowEnvelope)


def test_resource_envelope_unknown_type_raises():
    adapter = TypeAdapter(ResourceEnvelope)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "widget", "config": {"name": "x"}})
