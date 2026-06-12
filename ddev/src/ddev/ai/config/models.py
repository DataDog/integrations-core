# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ddev.ai.phases.config import CheckpointConfig, FlowEntry, TaskConfig
from ddev.ai.tools.registry import ToolRegistry


class VariableDeclaration(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    default: str | None = None


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str
    provider: str = "anthropic"
    model: str | None = None
    max_tokens: int | None = None
    tools: list[str] = []
    variables: list[VariableDeclaration] = []
    system_prompt_path: Path | None = None

    @field_validator("tools", mode="after")
    @classmethod
    def tools_must_be_known(cls, tools: list[str]) -> list[str]:
        unknown = set(tools) - set(ToolRegistry.available_tool_names())
        if unknown:
            raise ValueError(f"Unknown tool names: {sorted(unknown)}")
        return tools


class PhaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    name: str
    class_: str = Field(alias="class", default="AgenticPhase")
    agent: str | None = None
    tasks: list[TaskConfig] = []
    context_compact_threshold_pct: int = 80
    checkpoint: CheckpointConfig | None = None
    variables: list[VariableDeclaration] = []


class FlowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    variables: dict[str, str] = {}
    flow: list[FlowEntry]


class AgentEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["agent"]
    config: AgentConfig


class PhaseEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["phase"]
    config: PhaseConfig


class FlowEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["flow"]
    config: FlowConfig


ResourceEnvelope = Annotated[
    AgentEnvelope | PhaseEnvelope | FlowEnvelope,
    Field(discriminator="type"),
]


@dataclass(frozen=True)
class ResolvedFlow:
    """Fully validated, path-resolved flow ready for the orchestrator."""

    name: str
    agents: dict[str, AgentConfig]
    phases: dict[str, PhaseConfig]
    flow: list[FlowEntry]
    variables: dict[str, str]
