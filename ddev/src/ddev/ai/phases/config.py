# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FlowConfigError(Exception):
    """Wraps Pydantic ValidationError or YAML errors with a user-friendly message."""


def _detect_cycles(
    dependency_map: dict[str, list[str]],
    limit: int = 50,
) -> tuple[list[list[str]], bool]:
    """Return every simple cycle in the dependency graph, each as an ordered list of phase IDs."""
    rank = {n: i for i, n in enumerate(dependency_map)}
    cycles: list[list[str]] = []

    class _LimitReached(Exception):
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
    prompt_path: Path | None = None
    prompt: str | None = None
    goal: str | None = None
    goal_path: Path | None = None
    max_goal_attempts: int = 5
    clear_context_before: bool = False
    compact_context_before: bool = False

    @model_validator(mode="after")
    def exactly_one_prompt_source(self) -> TaskConfig:
        if (self.prompt_path is None) == (self.prompt is None):
            raise ValueError("Exactly one of 'prompt_path' or 'prompt' must be set")
        return self

    @model_validator(mode="after")
    def context_flags_mutually_exclusive(self) -> TaskConfig:
        if self.clear_context_before and self.compact_context_before:
            raise ValueError("'clear_context_before' and 'compact_context_before' are mutually exclusive")
        return self

    @model_validator(mode="after")
    def goal_consistency(self) -> TaskConfig:
        if self.goal is not None and self.goal_path is not None:
            raise ValueError("At most one of 'goal' or 'goal_path' may be set")
        has_goal = self.goal is not None or self.goal_path is not None
        if not has_goal and "max_goal_attempts" in self.model_fields_set:
            raise ValueError("'max_goal_attempts' may only be set when 'goal' or 'goal_path' is set")
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


class FlowEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: str
    dependencies: list[str] = []
