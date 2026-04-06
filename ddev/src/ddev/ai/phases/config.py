# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class PhaseConfigError(Exception):
    """Raised when a phase configuration file is invalid or missing required fields."""


@dataclass
class AgentConfig:
    # None means "use the agent implementation's own default" — keeps phases model-agnostic.
    model: str | None = None
    max_tokens: int | None = None
    context_reset_threshold_pct: int = 80  # phase-level policy for when to reset agent history


@dataclass
class ReactConfig:
    max_iterations: int = 50


@dataclass
class PhaseConfig:
    name: str
    depends_on: list[str]
    agent: AgentConfig
    react: ReactConfig
    tools: list[str]
    system_prompt_path: Path
    task_prompt_paths: list[Path]
    checkpoint_schema: dict[str, Any]
    config_dir: Path

    @classmethod
    def from_yaml(cls, config_path: Path) -> "PhaseConfig":
        """Load and validate a PhaseConfig from a YAML file.

        Raises PhaseConfigError if the config is missing required fields or has no task prompts.
        """
        try:
            raw = yaml.safe_load(config_path.read_text())
        except (OSError, yaml.YAMLError) as e:
            raise PhaseConfigError(f"Failed to load phase config {config_path}: {e}")

        if not isinstance(raw, dict):
            raise PhaseConfigError(f"Phase config must be a YAML mapping: {config_path}")

        try:
            name = raw["name"]
        except KeyError:
            raise PhaseConfigError(f"Phase config missing required field 'name': {config_path}")

        config_dir = config_path.parent
        depends_on: list[str] = raw.get("depends_on") or []

        agent_raw = raw.get("agent") or {}
        agent = AgentConfig(
            model=agent_raw.get("model"),
            max_tokens=agent_raw.get("max_tokens"),
            context_reset_threshold_pct=agent_raw.get("context_reset_threshold_pct", 80),
        )

        react_raw = raw.get("react") or {}
        react = ReactConfig(
            max_iterations=react_raw.get("max_iterations", 50),
        )

        tools: list[str] = raw.get("tools") or []

        prompts_raw = raw.get("prompts") or {}
        try:
            system_prompt_path = config_dir / prompts_raw["system"]
        except KeyError:
            raise PhaseConfigError(f"Phase config missing 'prompts.system': {config_path}")

        task_paths_raw: list[str] = prompts_raw.get("tasks") or []
        task_prompt_paths = [config_dir / p for p in task_paths_raw]

        if not task_prompt_paths:
            raise PhaseConfigError(f"Phase '{name}' has no task prompts configured under 'prompts.tasks'")

        checkpoint_schema: dict[str, Any] = raw.get("checkpoint_schema") or {}

        return cls(
            name=name,
            depends_on=depends_on,
            agent=agent,
            react=react,
            tools=tools,
            system_prompt_path=system_prompt_path,
            task_prompt_paths=task_prompt_paths,
            checkpoint_schema=checkpoint_schema,
            config_dir=config_dir,
        )
