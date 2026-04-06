# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Shared fixtures and helpers for the phases test suite."""

from pathlib import Path
from typing import Any

import yaml

from ddev.ai.agent.types import AgentResponse, ContextUsage, StopReason, TokenUsage
from ddev.ai.phases.base import AgentFactory
from ddev.ai.phases.config import PhaseConfig
from ddev.ai.tools.core.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Mock agent
# ---------------------------------------------------------------------------


class MockAgent:
    """AgentProtocol implementation that replays a fixed list of responses."""

    def __init__(self, responses: list[AgentResponse]) -> None:
        self._responses = iter(responses)
        self.send_calls: list[Any] = []
        self.reset_count: int = 0

    async def send(self, content: Any, allowed_tools: Any = None) -> AgentResponse:
        self.send_calls.append(content)
        return next(self._responses)

    def reset(self) -> None:
        self.reset_count += 1


def make_response(
    text: str = "key: value",
    stop_reason: StopReason = StopReason.END_TURN,
    context_pct: float = 10.0,
    window_size: int = 200_000,
) -> AgentResponse:
    """Build an AgentResponse with controllable context usage percentage."""
    used = max(1, int(window_size * context_pct / 100))
    return AgentResponse(
        stop_reason=stop_reason,
        text=text,
        tool_calls=[],
        usage=TokenUsage(
            input_tokens=used,
            output_tokens=10,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            context_usage=ContextUsage(window_size=window_size, used_tokens=used),
        ),
    )


def make_agent_factory(agent: MockAgent) -> AgentFactory:
    """Wrap a MockAgent in an AgentFactory callable."""

    def factory(name: str, system_prompt: str, tool_registry: ToolRegistry) -> MockAgent:
        return agent

    return factory  # type: ignore[return-value]


def make_capturing_agent_factory(agent: MockAgent) -> tuple[AgentFactory, list[str]]:
    """Return a factory and a list that captures each rendered system_prompt on invocation."""
    captured: list[str] = []

    def factory(name: str, system_prompt: str, tool_registry: ToolRegistry) -> MockAgent:
        captured.append(system_prompt)
        return agent

    return factory, captured  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Phase config builder
# ---------------------------------------------------------------------------


def build_phase_config(
    tmp_path: Path,
    *,
    name: str = "test_phase",
    depends_on: list[str] | None = None,
    checkpoint_schema: dict[str, Any] | None = None,
    num_tasks: int = 1,
    system_prompt: str = "You are a test agent for {{ metadata.project }}.",
    task_prompt: str = "Run task. Previous context:\n{{ checkpoint_data }}",
    agent_overrides: dict[str, Any] | None = None,
    react_overrides: dict[str, Any] | None = None,
    tools: list[str] | None = None,
) -> PhaseConfig:
    """Write config.yaml + prompt files under tmp_path and return the loaded PhaseConfig."""
    phase_dir = tmp_path / name
    prompts_dir = phase_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    task_files = [f"prompts/task_{i}.md" for i in range(num_tasks)]
    config_data: dict[str, Any] = {
        "name": name,
        "depends_on": depends_on or [],
        "tools": tools or [],
        "prompts": {"system": "prompts/system.md", "tasks": task_files},
        "checkpoint_schema": checkpoint_schema or {},
    }
    if agent_overrides:
        config_data["agent"] = agent_overrides
    if react_overrides:
        config_data["react"] = react_overrides

    (phase_dir / "config.yaml").write_text(yaml.dump(config_data))
    (prompts_dir / "system.md").write_text(system_prompt)
    for i in range(num_tasks):
        (prompts_dir / f"task_{i}.md").write_text(task_prompt)

    return PhaseConfig.from_yaml(phase_dir / "config.yaml")
