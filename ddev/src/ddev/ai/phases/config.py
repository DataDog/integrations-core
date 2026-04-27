# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from ddev.ai.tools.core.registry import ToolRegistry


class FlowConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""


class TaskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    prompt_path: Path | None = None
    prompt: str | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> "TaskConfig":
        if (self.prompt_path is None) == (self.prompt is None):
            raise ValueError("Exactly one of 'prompt_path' or 'prompt' must be set")
        return self


class CheckpointConfig(BaseModel):
    """Optional extra instructions for the memory step. If omitted, only a summary is written."""

    model_config = ConfigDict(extra="forbid")
    memory_prompt: str | None = None
    memory_prompt_path: Path | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> "CheckpointConfig":
        if (self.memory_prompt is None) == (self.memory_prompt_path is None):
            raise ValueError("Exactly one of 'memory_prompt' or 'memory_prompt_path' must be set")
        return self


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str | None = None
    max_tokens: int | None = None
    tools: list[str] = []

    @field_validator("tools", mode="after")
    @classmethod
    def tools_must_be_known(cls, tools: list[str]) -> list[str]:
        unknown = set(tools) - set(ToolRegistry.available_tool_names())
        if unknown:
            raise ValueError(f"Unknown tool names: {sorted(unknown)}")
        return tools


class PhaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = "Phase"
    agent: str
    tasks: list[TaskConfig]
    context_compact_threshold_pct: int = 80
    checkpoint: CheckpointConfig | None = None

    @field_validator("tasks", mode="after")
    @classmethod
    def at_least_one_task(cls, tasks: list[TaskConfig]) -> list[TaskConfig]:
        if not tasks:
            raise ValueError("A phase must have at least one task")
        return tasks


class FlowEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str
    dependencies: list[str] = []


class FlowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variables: dict[str, str] = {}
    agents: dict[str, AgentConfig]
    phases: dict[str, PhaseConfig]
    flow: list[FlowEntry]

    @model_validator(mode="after")
    def cross_references(self) -> "FlowConfig":
        """Validate all cross-references between agents, phases, and dependencies."""
        scheduled = {entry.phase for entry in self.flow}
        seen: set[str] = set()
        for entry in self.flow:
            if entry.phase in seen:
                raise ValueError(f"Duplicate phase in flow: {entry.phase!r}")
            seen.add(entry.phase)
            if entry.phase not in self.phases:
                raise ValueError(f"Flow references unknown phase: {entry.phase!r}")
            for dep in entry.dependencies:
                if dep not in self.phases:
                    raise ValueError(f"Phase {entry.phase!r} depends on unknown phase: {dep!r}")
                if dep not in scheduled:
                    raise ValueError(f"Phase {entry.phase!r} depends on {dep!r} which is not scheduled in flow")

        for phase_id, phase in self.phases.items():
            if phase.agent not in self.agents:
                raise ValueError(f"Phase {phase_id!r} references unknown agent: {phase.agent!r}")
        return self

    @classmethod
    def from_yaml(cls, path: Path, config_dir: Path) -> "FlowConfig":
        """Load, parse, and validate flow.yaml. Raises FlowConfigError on any problem."""
        try:
            raw = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise FlowConfigError(f"Failed to load {path}: {e}") from e

        try:
            config = cls.model_validate(raw)
        except ValidationError as e:
            raise FlowConfigError(f"Invalid flow config:\n{e}") from e

        config._validate_files(config_dir)
        return config

    def _validate_files(self, config_dir: Path) -> None:
        """Check all referenced files exist."""
        for agent_name in self.agents:
            system_prompt = config_dir / "prompts" / f"{agent_name}.md"
            if not system_prompt.exists():
                raise FlowConfigError(f"System prompt not found for agent {agent_name!r}: {system_prompt}")

        for phase_id, phase in self.phases.items():
            for i, task in enumerate(phase.tasks):
                if task.prompt_path is not None:
                    resolved = config_dir / task.prompt_path
                    if not resolved.exists():
                        raise FlowConfigError(
                            f"Phase {phase_id!r} task {i} ({task.name!r}): prompt_path not found: {resolved}"
                        )

            if phase.checkpoint is not None and phase.checkpoint.memory_prompt_path is not None:
                resolved = config_dir / phase.checkpoint.memory_prompt_path
                if not resolved.exists():
                    raise FlowConfigError(f"Phase {phase_id!r} checkpoint memory_prompt_path not found: {resolved}")
