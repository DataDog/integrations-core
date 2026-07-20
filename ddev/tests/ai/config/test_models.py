# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Never

import pytest
from pydantic import ValidationError

from ddev.ai.agent.anthropic_provider import DEFAULT_MODEL
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config import models
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
        AgentConfig(provider="custom")


def test_agent_runs_provider_config_validation():
    class CustomProvider:
        def default_model(self) -> str:
            return "supported-model"

        def supported_models(self) -> frozenset[str]:
            return frozenset()

        def validate_config(self, agent_config: AgentConfig) -> None:
            if agent_config.model != "supported-model":
                raise ValueError("Custom provider rejected model")

        def build_agent(self, *_args: object, **_kwargs: object) -> Never:
            raise NotImplementedError

    registry = AgentProviderRegistry()
    registry.register("custom", CustomProvider())

    with pytest.raises(ValidationError, match="Custom provider rejected model"):
        AgentConfig.model_validate(
            {"provider": "custom", "model": "unsupported-model"}, context={"provider_registry": registry}
        )


def test_agent_validates_provider_against_registry():
    registry = make_provider_registry("custom")

    config = AgentConfig.model_validate({"provider": "custom"}, context={"provider_registry": registry})

    assert config.provider == "custom"
    assert config.model == "default-model"


def test_agent_rejects_provider_when_not_configured():
    with pytest.raises(ValidationError, match="Agent provider 'custom' is not available"):
        AgentConfig.model_validate({"provider": "custom"}, context={"provider_registry": AgentProviderRegistry()})


def test_agent_infers_provider_from_model():
    registry = make_provider_registry("anthropic")

    config = AgentConfig.model_validate({"model": "opus"}, context={"provider_registry": registry})

    assert config.provider == "anthropic"
    assert config.model == "opus"


def test_agent_infers_provider_from_differently_cased_model_alias():
    registry = make_provider_registry("anthropic")

    config = AgentConfig.model_validate({"model": "OPUS"}, context={"provider_registry": registry})

    assert config.provider == "anthropic"


def test_agent_uses_provider_default_model_when_model_is_unset():
    registry = make_provider_registry("anthropic")

    config = AgentConfig.model_validate({"provider": "anthropic"}, context={"provider_registry": registry})

    assert config.provider == "anthropic"
    assert config.model == DEFAULT_MODEL


def test_agent_requires_provider_or_model():
    registry = make_provider_registry("anthropic")

    with pytest.raises(ValidationError, match="At least one of 'provider' or 'model' must be set"):
        AgentConfig.model_validate({}, context={"provider_registry": registry})


def test_agent_rejects_unknown_tools():
    with pytest.raises(ValidationError):
        make_agent_config(tools=["nonexistent_tool"])


def test_agent_rejects_unknown_model():
    registry = make_provider_registry("anthropic")

    with pytest.raises(ValidationError, match="Unknown model"):
        AgentConfig.model_validate({"model": "bogus"}, context={"provider_registry": registry})


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


def test_flow_config_accepts_tui_metadata():
    config = FlowConfig.model_validate(
        {
            "name": "demo",
            "description": "Generate an integration",
            "inputs": [
                {
                    "name": "specification",
                    "label": "Specification",
                    "type": "path",
                    "placeholder": "/path/to/spec.md",
                    "required": True,
                    "as_content": True,
                }
            ],
            "flow": [],
        }
    )

    assert config.description == "Generate an integration"
    assert config.inputs[0].input_type is models.InputType.PATH
    assert config.inputs[0].model_dump(by_alias=True)["type"] == "path"
    assert config.inputs == [
        models.FlowInput(
            name="specification",
            label="Specification",
            input_type=models.InputType.PATH,
            placeholder="/path/to/spec.md",
            required=True,
            as_content=True,
        ),
        *models.BUILT_IN_FLOW_INPUTS,
    ]


def test_flow_config_rejects_duplicate_input_names():
    with pytest.raises(ValidationError, match="Input names must be unique"):
        FlowConfig.model_validate(
            {
                "name": "demo",
                "inputs": [
                    {"name": "subject", "label": "Subject", "type": "string"},
                    {"name": "subject", "label": "Other subject", "type": "string"},
                ],
                "flow": [],
            }
        )


def test_flow_config_injects_missing_built_in_inputs():
    config = FlowConfig(name="demo", flow=[])

    assert config.inputs == list(models.BUILT_IN_FLOW_INPUTS)


def test_flow_config_does_not_replace_declared_built_in_input():
    prd = models.FlowInput(name="prd", label="Custom PRD", input_type="path", as_content=True)

    config = FlowConfig(name="demo", inputs=[prd], flow=[])
    built_in_prd = next(input for input in models.BUILT_IN_FLOW_INPUTS if input.name == "prd")

    assert prd in config.inputs
    assert built_in_prd not in config.inputs


def test_flow_input_rejects_as_content_for_non_path():
    with pytest.raises(ValidationError, match="'as_content' may only be used with path inputs"):
        models.FlowInput(name="subject", label="Subject", input_type="string", as_content=True)


def test_flow_input_rejects_placeholder_for_boolean():
    with pytest.raises(ValidationError, match="'placeholder' may not be used with boolean inputs"):
        models.FlowInput(name="enabled", label="Enabled", input_type="boolean", placeholder="Enabled")


def resolved_with_inputs(*inputs: models.FlowInput) -> models.ResolvedFlow:
    return models.ResolvedFlow(
        name="demo",
        description=None,
        inputs=list(inputs),
        agents={},
        phases={},
        flow=[],
        variables={},
    )


def test_resolved_flow_converts_typed_runtime_inputs(tmp_path):
    source = tmp_path / "spec.md"
    source.write_text("specification text", encoding="utf-8")
    resolved = resolved_with_inputs(
        models.FlowInput(name="name", label="Name", input_type="string"),
        models.FlowInput(name="count", label="Count", input_type="number"),
        models.FlowInput(name="enabled", label="Enabled", input_type="boolean"),
        models.FlowInput(name="source", label="Source", input_type="path", as_content=True),
    )

    assert resolved.convert_inputs({"name": "example", "count": 3.5, "enabled": True, "source": source}) == {
        "name": "example",
        "count": "3.5",
        "enabled": "true",
        "source": "specification text",
    }


def test_resolved_flow_boolean_false_is_lowercase():
    resolved = resolved_with_inputs(models.FlowInput(name="enabled", label="Enabled", input_type="boolean"))

    assert resolved.convert_inputs({"enabled": False}) == {"enabled": "false"}


def test_resolved_flow_boolean_string_false_is_false():
    resolved = resolved_with_inputs(models.FlowInput(name="enabled", label="Enabled", input_type="boolean"))

    assert resolved.convert_inputs({"enabled": "false"}) == {"enabled": "false"}


def test_resolved_flow_rejects_invalid_boolean():
    resolved = resolved_with_inputs(models.FlowInput(name="enabled", label="Enabled", input_type="boolean"))

    with pytest.raises(ValueError, match="Input 'enabled' must be a boolean"):
        resolved.convert_inputs({"enabled": "sometimes"})


def test_resolved_flow_requires_required_input_even_with_default():
    resolved = resolved_with_inputs(
        models.FlowInput(name="topic", label="Topic", input_type="string", default="metrics", required=True)
    )

    with pytest.raises(ValueError, match="Required input 'topic' is missing"):
        resolved.convert_inputs({})


def test_resolved_flow_uses_optional_default_and_omits_unset_optional():
    resolved = resolved_with_inputs(
        models.FlowInput(name="topic", label="Topic", input_type="string", default="metrics", required=False),
        models.FlowInput(name="count", label="Count", input_type="number", default=3, required=False),
        models.FlowInput(name="enabled", label="Enabled", input_type="boolean", default="false", required=False),
        models.FlowInput(name="notes", label="Notes", input_type="string", required=False),
    )

    assert resolved.convert_inputs({}) == {"topic": "metrics", "count": "3", "enabled": "false"}


@pytest.mark.parametrize("default", ["many", True])
def test_flow_input_rejects_invalid_number_default(default):
    with pytest.raises(ValidationError, match="Default for number input 'count' must be a number"):
        models.FlowInput(name="count", label="Count", input_type="number", default=default, required=False)


def test_resolved_flow_validates_number_values():
    resolved = resolved_with_inputs(models.FlowInput(name="count", label="Count", input_type="number"))

    assert resolved.convert_inputs({"count": "3.5"}) == {"count": "3.5"}
    with pytest.raises(ValueError, match="Input 'count' must be a number"):
        resolved.convert_inputs({"count": "many"})


def test_resolved_flow_reads_optional_path_default_as_content(tmp_path):
    source = tmp_path / "spec.md"
    source.write_text("default specification", encoding="utf-8")
    resolved = resolved_with_inputs(
        models.FlowInput(
            name="source",
            label="Source",
            input_type="path",
            default=source,
            required=False,
            as_content=True,
        )
    )

    assert resolved.convert_inputs({}) == {"source": "default specification"}


def test_resolved_flow_path_content_reports_missing_file(tmp_path):
    resolved = resolved_with_inputs(models.FlowInput(name="source", label="Source", input_type="path", as_content=True))

    with pytest.raises(ValueError, match="Input 'source' path does not exist"):
        resolved.convert_inputs({"source": tmp_path / "missing.md"})


def test_resolved_flow_path_content_rejects_directory(tmp_path):
    resolved = resolved_with_inputs(models.FlowInput(name="source", label="Source", input_type="path", as_content=True))

    with pytest.raises(ValueError, match="Input 'source' path is not a file"):
        resolved.convert_inputs({"source": tmp_path})


def test_flow_input_path_without_content_accepts_nonexistent_path(tmp_path):
    missing = tmp_path / "output.md"
    flow_input = models.FlowInput(name="output", label="Output", input_type="path")

    assert flow_input.convert_runtime_value(missing) == str(missing)


def test_flow_input_path_as_content_rejects_nonexistent_path(tmp_path):
    missing = tmp_path / "missing.md"
    flow_input = models.FlowInput(name="source", label="Source", input_type="path", as_content=True)

    with pytest.raises(ValueError, match="Input 'source' path does not exist"):
        flow_input.convert_runtime_value(missing)
