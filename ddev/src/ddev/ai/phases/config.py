# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, field_validator, model_validator

from ddev.ai.tools.registry import ToolRegistry


def parse_md_file(path: Path) -> tuple[dict[str, Any], str]:
    """Parse a Markdown file with YAML front matter.

    Returns (front_matter_dict, body_str). Raises FlowConfigError on any problem.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise FlowConfigError(f"Cannot read {path}: {e}") from e

    if not text.startswith("---"):
        raise FlowConfigError(f"{path}: missing YAML front matter (file must start with '---')")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise FlowConfigError(f"{path}: missing YAML front matter closing '---'")

    _, raw_yaml, raw_body = parts
    try:
        meta = yaml.safe_load(raw_yaml) or {}
    except yaml.YAMLError as e:
        raise FlowConfigError(f"{path}: Invalid YAML in front matter: {e}") from e

    return meta, raw_body.strip()


class FlowConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""


def _detect_cycles(
    dependency_map: dict[str, list[str]],
    limit: int = 50,
) -> tuple[list[list[str]], bool]:
    """Return every simple cycle in the dependency graph, each as an ordered list of phase IDs."""
    # Enumerate every simple cycle exactly once: from each node, DFS only through
    # higher-ranked nodes, so each cycle is reported only when started from its
    # lowest-ranked member. (Tiernan-style enumeration with rank canonicalization.)
    rank = {n: i for i, n in enumerate(dependency_map)}
    cycles: list[list[str]] = []

    class _LimitReached(Exception):
        """Raised when the cycle limit is reached."""

        pass

    def dfs(start: str, current: str, path: list[str], on_path: set[str]):
        for dep in dependency_map.get(current, []):
            if dep == start:
                cycles.append(path + [start])
                if len(cycles) >= limit:
                    raise _LimitReached
            elif dep in rank and rank[dep] > rank[start] and dep not in on_path:
                on_path.add(dep)
                dfs(start, dep, path + [dep], on_path)
                on_path.discard(dep)

    try:
        for start in dependency_map:
            dfs(start, start, [start], {start})
    except _LimitReached:
        return cycles, True
    return cycles, False


class TaskConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(pattern=r"^[A-Za-z0-9._-]{1,64}$")
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
    """Optional extra instructions for the memory step. If omitted, only a summary is written."""

    model_config = ConfigDict(extra="forbid")
    memory_prompt: str | None = None
    memory_prompt_path: Path | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> CheckpointConfig:
        if (self.memory_prompt is None) == (self.memory_prompt_path is None):
            raise ValueError("Exactly one of 'memory_prompt' or 'memory_prompt_path' must be set")
        return self


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider: str = "anthropic"
    model: str | None = None
    max_tokens: int | None = None
    tools: list[str] = []
    system_prompt: str = ""

    @field_validator("tools", mode="after")
    @classmethod
    def tools_must_be_known(cls, tools: list[str]) -> list[str]:
        unknown = set(tools) - set(ToolRegistry.available_tool_names())
        if unknown:
            raise ValueError(f"Unknown tool names: {sorted(unknown)}")
        return tools


class PhaseConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: str = "AgenticPhase"
    agent: str | None = None
    tasks: list[TaskConfig] = []
    context_compact_threshold_pct: int = 80
    checkpoint: CheckpointConfig | None = None


class FlowEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str
    dependencies: list[str] = []


class FlowConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    variables: dict[str, str] = {}
    phases: dict[str, PhaseConfig]
    flow: list[FlowEntry]

    _agents: dict[str, AgentConfig] = PrivateAttr(default_factory=dict)
    _prompts: dict[str, str] = PrivateAttr(default_factory=dict)
    _goals: dict[str, str] = PrivateAttr(default_factory=dict)

    @property
    def agents(self) -> dict[str, AgentConfig]:
        return self._agents

    @property
    def prompts(self) -> dict[str, str]:
        return self._prompts

    @property
    def goals(self) -> dict[str, str]:
        return self._goals

    @model_validator(mode="after")
    def cross_references(self) -> FlowConfig:
        """Validate all cross-references between phases and dependencies."""
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

        dependency_map = {entry.phase: entry.dependencies for entry in self.flow}
        cycles, truncated = _detect_cycles(dependency_map)
        if cycles:
            formatted = "\n  ".join(" → ".join(c) for c in cycles)
            suffix = f"\n  (showing first {len(cycles)}; more cycles exist)" if truncated else ""
            raise ValueError(f"Cycle(s) detected in flow:\n  {formatted}{suffix}")

        return self

    @classmethod
    def from_yaml(cls, path: Path, config_dir: Path) -> FlowConfig:
        """Load, parse, and validate flow.yaml. Raises FlowConfigError on any problem."""
        try:
            raw = yaml.safe_load(path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise FlowConfigError(f"Failed to load {path}: {e}") from e

        try:
            config = cls.model_validate(raw)
        except ValidationError as e:
            raise FlowConfigError(f"Invalid flow config:\n{e}") from e

        # Scan agents/ directory
        agents: dict[str, AgentConfig] = {}
        agents_dir = config_dir / "agents"
        if agents_dir.is_dir():
            for md_file in sorted(agents_dir.glob("*.md")):
                meta, body = parse_md_file(md_file)
                fm = {k: v for k, v in meta.items() if k != "type"}
                fm["system_prompt"] = body
                try:
                    agents[md_file.stem] = AgentConfig.model_validate(fm)
                except ValidationError as e:
                    raise FlowConfigError(f"Invalid agent config in {md_file}:\n{e}") from e
        config._agents = agents

        # Scan prompts/ directory — build separate indexes for type:prompt and type:goal
        prompts: dict[str, str] = {}
        goals: dict[str, str] = {}
        prompts_dir = config_dir / "prompts"
        if prompts_dir.is_dir():
            for md_file in sorted(prompts_dir.glob("*.md")):
                meta, body = parse_md_file(md_file)
                file_type = meta.get("type")
                if file_type == "prompt":
                    prompts[md_file.stem] = body
                elif file_type == "goal":
                    goals[md_file.stem] = body
                else:
                    raise FlowConfigError(
                        f"{md_file}: expected 'type: prompt' or 'type: goal' in front matter, got {file_type!r}"
                    )
        config._prompts = prompts
        config._goals = goals

        # Validate cross-file references
        for phase_id, phase in config.phases.items():
            if phase.agent is not None and phase.agent not in agents:
                raise FlowConfigError(
                    f"Phase {phase_id!r} references unknown agent: {phase.agent!r} "
                    f"(No agent file found for {phase.agent!r})"
                )
            for i, task in enumerate(phase.tasks):
                if task.prompt_ref is not None and task.prompt_ref not in prompts:
                    raise FlowConfigError(
                        f"Phase {phase_id!r} task {i} ({task.name!r}): "
                        f"No prompt file found for prompt_ref {task.prompt_ref!r}"
                    )
                if task.goal_ref is not None and task.goal_ref not in goals:
                    raise FlowConfigError(
                        f"Phase {phase_id!r} task {i} ({task.name!r}): "
                        f"No goal file found for goal_ref {task.goal_ref!r}"
                    )
            if phase.checkpoint is not None and phase.checkpoint.memory_prompt_path is not None:
                resolved = config_dir / phase.checkpoint.memory_prompt_path
                if not resolved.exists():
                    raise FlowConfigError(f"Phase {phase_id!r} checkpoint memory_prompt_path not found: {resolved}")

        return config
