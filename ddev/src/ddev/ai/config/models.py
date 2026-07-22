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
from typing import TYPE_CHECKING, Annotated, Any, Literal, Mapping, assert_never, cast

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
    STRING = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    PATH = auto()
    OBJECT = auto()


type ScalarInputType = Literal[
    InputType.STRING,
    InputType.NUMBER,
    InputType.BOOLEAN,
    InputType.PATH,
]
type ScalarInputValue = str
type ObjectInputValue = dict[str, str]
type RuntimeInputValue = ScalarInputValue | ObjectInputValue | list[ScalarInputValue] | list[ObjectInputValue]
type RuntimeVariables = dict[str, RuntimeInputValue]


class FlowInputBase(BaseModel):
    """Describe fields shared by flow inputs."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str = Field(pattern=VARIABLE_NAME_PATTERN)
    label: str
    default: Any | None = None
    placeholder: str | None = None
    required: bool = True
    as_content: bool = False


class FlowInputField(FlowInputBase):
    """Describe one scalar field within an object input."""

    input_type: ScalarInputType = Field(alias="type")

    @model_validator(mode="after")
    def validate_input_options(self) -> FlowInputField:
        _validate_scalar_options(
            self.input_type,
            self.name,
            default=self.default,
            placeholder=self.placeholder,
            as_content=self.as_content,
        )
        return self

    def convert_runtime_value(self, value: object, *, error_path: str | None = None) -> str:
        """Convert one runtime value according to this input's declared type."""
        return _convert_scalar_runtime_value(
            self.input_type, error_path or self.name, value, as_content=self.as_content
        )


class FlowInput(FlowInputBase):
    """Describe a typed value supplied when launching a flow."""

    input_type: InputType = Field(alias="type")
    fields: list[FlowInputField] = Field(default_factory=list)
    multi: bool = False

    @model_validator(mode="after")
    def validate_input_options(self) -> FlowInput:
        defaults: list[object] = []
        if self.default is not None:
            if self.multi:
                if not isinstance(self.default, list):
                    raise ValueError(f"Default for multi input {self.name!r} must be a list")
                if not self.default:
                    raise ValueError(f"Default for multi input {self.name!r} must contain at least one item")
                defaults.extend(self.default)
            else:
                defaults.append(self.default)

        if self.input_type is InputType.OBJECT:
            _validate_object_options(
                self.name,
                self.fields,
                defaults=defaults,
                placeholder=self.placeholder,
                as_content=self.as_content,
                multi=self.multi,
            )
        else:
            if self.fields:
                raise ValueError("'fields' may only be used with object inputs")
            if defaults:
                for index, default in enumerate(defaults):
                    name = f"{self.name}[{index}]" if self.multi else self.name
                    _validate_scalar_options(
                        self.input_type,
                        name,
                        default=default,
                        placeholder=self.placeholder,
                        as_content=self.as_content,
                    )
            else:
                _validate_scalar_options(
                    self.input_type,
                    self.name,
                    default=None,
                    placeholder=self.placeholder,
                    as_content=self.as_content,
                )
        return self

    def convert_runtime_value(self, value: object) -> RuntimeInputValue:
        """Convert runtime values according to this input's type and cardinality."""
        if self.multi:
            if not isinstance(value, list):
                raise ValueError(f"Input {self.name!r} must be a list")
            if not value and self.required:
                raise ValueError(f"Required input {self.name!r} must contain at least one item")
            if self.input_type is InputType.OBJECT:
                return [
                    cast(ObjectInputValue, self.convert_single_runtime_value(item, error_path=f"{self.name}[{index}]"))
                    for index, item in enumerate(value)
                ]
            return [
                cast(ScalarInputValue, self.convert_single_runtime_value(item, error_path=f"{self.name}[{index}]"))
                for index, item in enumerate(value)
            ]
        return self.convert_single_runtime_value(value)

    def convert_single_runtime_value(
        self,
        value: object,
        *,
        error_path: str | None = None,
    ) -> ScalarInputValue | ObjectInputValue:
        """Convert one runtime value according to this input's declared type."""
        input_error_path = error_path or self.name
        if self.input_type is not InputType.OBJECT:
            return _convert_scalar_runtime_value(self.input_type, input_error_path, value, as_content=self.as_content)
        return {
            child.name: child.convert_runtime_value(child_value, error_path=qualified_name)
            for child, child_value, qualified_name in _resolve_object_field_values(input_error_path, self.fields, value)
        }


def _validate_object_options(
    error_path: str,
    fields: list[FlowInputField],
    *,
    defaults: list[object],
    placeholder: str | None,
    as_content: bool,
    multi: bool,
) -> None:
    if not fields:
        raise ValueError("Object inputs must declare at least one field")
    field_names = [field.name for field in fields]
    if len(field_names) != len(set(field_names)):
        raise ValueError("Object field names must be unique")
    if as_content:
        raise ValueError("'as_content' may only be used with path inputs")
    if placeholder is not None:
        raise ValueError("'placeholder' may not be set on object inputs; set it on individual object fields instead")
    for index, default in enumerate(defaults):
        object_error_path = f"{error_path}[{index}]" if multi else error_path
        for child, child_value, qualified_name in _resolve_object_field_values(object_error_path, fields, default):
            _validate_scalar_runtime_value(child.input_type, qualified_name, child_value)


def _resolve_object_field_values(
    error_path: str,
    fields: list[FlowInputField],
    value: object,
) -> list[tuple[FlowInputField, object, str]]:
    if not isinstance(value, Mapping):
        raise ValueError(f"Input {error_path!r} must be an object")

    field_names = {field.name for field in fields}
    unknown_fields = sorted(set(value) - field_names)
    if unknown_fields:
        raise ValueError(f"Unknown fields for input {error_path!r}: {unknown_fields}")

    values: list[tuple[FlowInputField, object, str]] = []
    for child in fields:
        child_value = value.get(child.name)
        qualified_name = f"{error_path}.{child.name}"
        if child_value is None:
            if child.required:
                raise ValueError(f"Required input {qualified_name!r} is missing")
            if child.default is None:
                continue
            child_value = child.default
        values.append((child, child_value, qualified_name))
    return values


def _validate_scalar_options(
    input_type: ScalarInputType,
    error_path: str,
    *,
    default: object | None,
    placeholder: str | None,
    as_content: bool,
) -> None:
    if as_content and input_type is not InputType.PATH:
        raise ValueError("'as_content' may only be used with path inputs")
    if placeholder is not None and input_type is InputType.BOOLEAN:
        raise ValueError("'placeholder' may not be used with boolean inputs")
    if default is None:
        return
    match input_type:
        case InputType.STRING | InputType.PATH:
            pass
        case InputType.NUMBER:
            _validate_number(error_path, default, prefix="Default for number input")
        case InputType.BOOLEAN:
            _convert_boolean(error_path, default, prefix="Default for boolean input")
        case unexpected:
            assert_never(unexpected)


def _convert_scalar_runtime_value(
    input_type: ScalarInputType,
    error_path: str,
    value: object,
    *,
    as_content: bool,
) -> str:
    match input_type:
        case InputType.STRING:
            return str(value)
        case InputType.NUMBER:
            _validate_number(error_path, value)
            return str(value)
        case InputType.BOOLEAN:
            return _convert_boolean(error_path, value)
        case InputType.PATH:
            if as_content:
                return _read_path_content(error_path, value)
            return str(value)
        case unexpected:
            assert_never(unexpected)


def _validate_scalar_runtime_value(input_type: ScalarInputType, error_path: str, value: object) -> None:
    match input_type:
        case InputType.STRING | InputType.PATH:
            pass
        case InputType.NUMBER:
            _validate_number(error_path, value)
        case InputType.BOOLEAN:
            _convert_boolean(error_path, value)
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
        reserved_names = {flow_input.name for flow_input in BUILT_IN_FLOW_INPUTS}
        collisions = sorted(reserved_names.intersection(names))
        if collisions:
            raise ValueError(
                f"Input names cannot use reserved names {collisions}; reserved inputs are added to every flow"
            )
        if len(names) != len(set(names)):
            raise ValueError("Input names must be unique")
        return [*inputs, *BUILT_IN_FLOW_INPUTS]


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

    def convert_inputs(self, values: Mapping[str, object]) -> RuntimeVariables:
        """Convert declared launch inputs to canonical runtime values."""
        converted: RuntimeVariables = {}
        for flow_input in self.inputs:
            value = values.get(flow_input.name)
            if value is None:
                if flow_input.required:
                    raise ValueError(f"Required input {flow_input.name!r} is missing")
                if flow_input.default is None:
                    continue
                value = flow_input.default

            if flow_input.multi and isinstance(value, list) and not value and not flow_input.required:
                if flow_input.default is None:
                    continue
                value = flow_input.default
            converted[flow_input.name] = flow_input.convert_runtime_value(value)
        return converted


def _convert_boolean(error_path: str, value: object, *, prefix: str = "Input") -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str) and (lower := value.lower()) in {"true", "false"}:
        return lower
    raise ValueError(f"{prefix} {error_path!r} must be a boolean")


def _validate_number(error_path: str, value: object, *, prefix: str = "Input") -> None:
    if isinstance(value, bool):
        raise ValueError(f"{prefix} {error_path!r} must be a number")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{prefix} {error_path!r} must be a number") from None
    if not number.is_finite():
        raise ValueError(f"{prefix} {error_path!r} must be a number")


def _read_path_content(error_path: str, value: object) -> str:
    """Read an existing regular UTF-8 file supplied as a path input."""
    if not isinstance(value, (str, PathLike)) or not str(value):
        raise ValueError(f"Input {error_path!r} must be a valid path")
    path = Path(value)
    if not path.exists():
        raise ValueError(f"Input {error_path!r} path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input {error_path!r} path is not a file: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"Input {error_path!r} path could not be read: {path}: {error}") from error


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
