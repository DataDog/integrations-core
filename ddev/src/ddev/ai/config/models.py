# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import StrEnum, auto
from os import PathLike
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal, Mapping, assert_never

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.agent.registry import AgentProviderRegistry
    from ddev.ai.config.errors import FlowError

NAME_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"
# Variable names are interpolated via ``string.Template``, so they must be legal
# ``$identifier`` placeholders: start with a letter/underscore, then letters/digits/underscores.
VARIABLE_NAME_PATTERN = r"^[_a-zA-Z][_a-zA-Z0-9]{0,63}$"


def validate_variable_names(variables: dict[str, str]) -> dict[str, str]:
    """Ensure every variable name is a legal ``string.Template`` placeholder."""
    invalid = sorted(name for name in variables if re.match(VARIABLE_NAME_PATTERN, name) is None)
    if invalid:
        raise ValueError(f"Invalid variable names (must match {VARIABLE_NAME_PATTERN}): {invalid}")
    return variables


class VariableDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=VARIABLE_NAME_PATTERN)
    default: str | None = None


class InputType(StrEnum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    PATH = "path"


class FlowInput(BaseModel):
    """Describe a typed value supplied when launching a flow."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str = Field(pattern=VARIABLE_NAME_PATTERN)
    label: str
    input_type: InputType = Field(alias="type")
    default: Any | None = None
    placeholder: str | None = None
    required: bool = True
    as_content: bool = False

    @model_validator(mode="after")
    def validate_input_options(self) -> FlowInput:
        if self.as_content and self.input_type is not InputType.PATH:
            raise ValueError("'as_content' may only be used with path inputs")
        if self.placeholder is not None and self.input_type is InputType.BOOLEAN:
            raise ValueError("'placeholder' may not be used with boolean inputs")
        if self.default is not None:
            match self.input_type:
                case InputType.STRING | InputType.PATH:
                    pass
                case InputType.NUMBER:
                    _validate_number(self.name, self.default, prefix="Default for number input")
                case InputType.BOOLEAN:
                    _convert_boolean(self.name, self.default, prefix="Default for boolean input")
                case unexpected:
                    assert_never(unexpected)
        return self

    def convert_runtime_value(self, value: object) -> str:
        """Convert one runtime value according to this input's declared type."""
        match self.input_type:
            case InputType.STRING:
                return str(value)
            case InputType.NUMBER:
                _validate_number(self.name, value)
                return str(value)
            case InputType.BOOLEAN:
                return _convert_boolean(self.name, value)
            case InputType.PATH:
                if self.as_content:
                    return _read_path_content(self.name, value)
                return str(value)
            case unexpected:
                assert_never(unexpected)


BUILT_IN_FLOW_INPUTS = (
    FlowInput(
        name="prd",
        label="Product requirements file",
        input_type=InputType.PATH,
        required=True,
        as_content=True,
    ),
    FlowInput(
        name="max_timeout",
        label="Max timeout (seconds)",
        input_type=InputType.NUMBER,
        placeholder="Leave empty for unbounded",
        required=False,
    ),
)


class TaskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=NAME_PATTERN)
    prompt: str | None = None
    prompt_ref: str | None = None
    goal: str | None = None
    goal_ref: str | None = None
    max_goal_attempts: int = 5
    clear_context_before: bool = False
    compact_context_before: bool = False

    @model_validator(mode="after")
    def exactly_one_prompt_source(self) -> TaskConfig:
        if (self.prompt is None) == (self.prompt_ref is None):
            raise ValueError("Exactly one of 'prompt' or 'prompt_ref' must be set")
        return self

    @model_validator(mode="after")
    def context_flags_mutually_exclusive(self) -> TaskConfig:
        if self.clear_context_before and self.compact_context_before:
            raise ValueError("'clear_context_before' and 'compact_context_before' are mutually exclusive")
        return self

    @model_validator(mode="after")
    def goal_consistency(self) -> TaskConfig:
        if self.goal is not None and self.goal_ref is not None:
            raise ValueError("At most one of 'goal' or 'goal_ref' may be set")
        has_goal = self.goal is not None or self.goal_ref is not None
        if not has_goal and "max_goal_attempts" in self.model_fields_set:
            raise ValueError("'max_goal_attempts' may only be set when 'goal' or 'goal_ref' is set")
        if has_goal and self.max_goal_attempts < 1:
            raise ValueError("'max_goal_attempts' must be at least 1")
        return self


class CheckpointConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_prompt: str | None = None
    memory_prompt_ref: str | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> CheckpointConfig:
        if (self.memory_prompt is None) == (self.memory_prompt_ref is None):
            raise ValueError("Exactly one of 'memory_prompt' or 'memory_prompt_ref' must be set")
        return self


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str | None = None
    model: str | None = None
    max_tokens: int | None = Field(default=None, ge=1)
    tools: list[str] = Field(default_factory=list)
    variables: list[VariableDeclaration] = Field(default_factory=list)
    system_prompt: str = ""

    @field_validator("tools", mode="after")
    @classmethod
    def tools_must_be_known(cls, tools: list[str]) -> list[str]:
        unknown = set(tools) - set(ToolRegistry.available_tool_names())
        if unknown:
            raise ValueError(f"Unknown tool names: {sorted(unknown)}")
        return tools

    @model_validator(mode="after")
    def resolve_and_validate_provider(self, info: ValidationInfo) -> AgentConfig:
        provider_registry: AgentProviderRegistry | None = (
            info.context.get("provider_registry") if info.context is not None else None
        )
        if provider_registry is None:
            raise ValueError("Agent provider registry is required")
        if self.provider is None:
            if self.model is None:
                raise ValueError("At least one of 'provider' or 'model' must be set")
            self.provider = provider_registry.provider_for_model(self.model)
        elif self.model is None:
            self.model = provider_registry.default_model_for_provider(self.provider)
        provider_registry.validate_config(self)
        return self


class PhaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str = Field(pattern=NAME_PATTERN)
    class_: str = Field(default="AgenticPhase", alias="class")
    agent: str | None = None
    tasks: list[TaskConfig] = Field(default_factory=list)
    context_compact_threshold_pct: int = Field(default=80, ge=0, le=100)
    checkpoint: CheckpointConfig | None = None
    variables: list[VariableDeclaration] = Field(default_factory=list)


class FlowEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str
    dependencies: list[str] = Field(default_factory=list)


class FlowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=NAME_PATTERN)
    description: str | None = None
    inputs: list[FlowInput] = Field(default_factory=list, validate_default=True)
    variables: Annotated[dict[str, str], AfterValidator(validate_variable_names)] = Field(default_factory=dict)
    flow: list[FlowEntry]

    @field_validator("inputs", mode="after")
    @classmethod
    def inject_built_in_inputs(cls, inputs: list[FlowInput]) -> list[FlowInput]:
        names = [flow_input.name for flow_input in inputs]
        if len(names) != len(set(names)):
            raise ValueError("Input names must be unique")
        return [*inputs, *(flow_input for flow_input in BUILT_IN_FLOW_INPUTS if flow_input.name not in names)]


class PhaseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["phase"]
    config: PhaseConfig


class FlowEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["flow"]
    config: FlowConfig


ResourceEnvelope = Annotated[PhaseEnvelope | FlowEnvelope, Field(discriminator="type")]


@dataclass(frozen=True)
class ResolvedFlow:
    name: str
    agents: dict[str, AgentConfig]
    phases: dict[str, PhaseConfig]
    flow: list[FlowEntry]
    variables: dict[str, str]
    description: str | None = None
    inputs: list[FlowInput] = field(default_factory=list)

    def convert_inputs(self, values: Mapping[str, object]) -> dict[str, str]:
        """Convert declared launch inputs to runtime variable strings."""
        converted: dict[str, str] = {}
        for flow_input in self.inputs:
            value = values.get(flow_input.name)
            if value is None:
                if flow_input.required:
                    raise ValueError(f"Required input {flow_input.name!r} is missing")
                if flow_input.default is None:
                    continue
                value = flow_input.default

            converted[flow_input.name] = flow_input.convert_runtime_value(value)
        return converted


def _convert_boolean(name: str, value: object, *, prefix: str = "Input") -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and (lower := value.lower()) in {"true", "false"}:
        return lower
    raise ValueError(f"{prefix} {name!r} must be a boolean")


def _validate_number(name: str, value: object, *, prefix: str = "Input") -> None:
    if isinstance(value, bool):
        raise ValueError(f"{prefix} {name!r} must be a number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{prefix} {name!r} must be a number") from None
    if not number.is_finite():
        raise ValueError(f"{prefix} {name!r} must be a number")


def _read_path_content(name: str, value: object) -> str:
    """Read an existing regular UTF-8 file supplied as a path input."""
    if not isinstance(value, (str, PathLike)) or not str(value):
        raise ValueError(f"Input {name!r} must be a valid path")
    path = Path(value)
    if not path.exists():
        raise ValueError(f"Input {name!r} path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input {name!r} path is not a file: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Input {name!r} path could not be read: {path}: {error}") from error


class ConfigStatus(StrEnum):
    OK = auto()
    BROKEN = auto()


@dataclass
class FlowResult:
    """The complete outcome of processing one flow: its status, any errors, and, when
    valid, the ready-to-execute :class:`ResolvedFlow`."""

    name: str
    status: ConfigStatus
    errors: list[FlowError] = field(default_factory=list)
    resolved: ResolvedFlow | None = None
