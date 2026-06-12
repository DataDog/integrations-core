# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from pydantic import ValidationError

from ddev.ai.config.models import AgentConfig, FlowConfig, PhaseConfig, VariableDeclaration


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
    # 'class' is the YAML key; Python attribute is 'class_'
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
