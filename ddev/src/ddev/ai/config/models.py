# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.config.errors import FlowError

NAME_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"
# Variable names are interpolated via ``string.Template``, so they must be legal
# ``$identifier`` placeholders: start with a letter/underscore, then letters/digits/underscores.
VARIABLE_NAME_PATTERN = r"^[_a-z][_a-z0-9]{0,63}$"


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
    provider: str = "anthropic"
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
    variables: Annotated[dict[str, str], AfterValidator(validate_variable_names)] = Field(default_factory=dict)
    flow: list[FlowEntry]


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
