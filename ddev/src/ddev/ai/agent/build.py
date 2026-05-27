# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.phases.config import AgentConfig
from ddev.ai.phases.goal import GOAL_REVIEWER_SYSTEM_PROMPT
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry, filter_read_only

SubagentBuilder = Callable[
    [str, str, list[str]],  # (system_prompt, owner_id, tool_names)
    tuple[BaseAgent[Any], ToolRegistry],
]
AgentBuilder = Callable[
    [str, str, SubagentBuilder | None, Path | None],  # system_prompt, owner_id, subagent_builder, log_dir
    tuple[BaseAgent[Any], ToolRegistry],
]
GoalAgentBuilder = Callable[
    [str],  # owner_id
    tuple[BaseAgent[Any], ToolRegistry],
]


def _resolve_client(agent_clients: dict[str, Any], provider: str) -> Any:
    client = agent_clients.get(provider)
    if client is None:
        raise ValueError(f"No client provided for agent provider {provider!r}")
    return client


def _build_agent_and_registry(
    agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    system_prompt: str,
    owner_id: str,
    tool_names: list[str],
    file_registry: FileRegistry,
    subagent_builder: SubagentBuilder | None = None,
    log_dir: Path | None = None,
) -> tuple[BaseAgent[Any], ToolRegistry]:
    tool_registry = ToolRegistry.from_names(
        tool_names,
        owner_id=owner_id,
        file_registry=file_registry,
        subagent_builder=subagent_builder,
        log_dir=log_dir,
    )

    if agent_config.provider == "anthropic":
        kwargs: dict[str, Any] = {}
        if agent_config.model is not None:
            kwargs["model"] = agent_config.model
        if agent_config.max_tokens is not None:
            kwargs["max_tokens"] = agent_config.max_tokens
        agent: BaseAgent[Any] = AnthropicAgent(
            client=_resolve_client(agent_clients, "anthropic"),
            tools=tool_registry,
            system_prompt=system_prompt,
            name=owner_id,
            **kwargs,
        )
        return agent, tool_registry

    raise ValueError(f"Unknown agent provider: {agent_config.provider!r}")


def build_agent(
    agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    system_prompt: str,
    owner_id: str,
    file_registry: FileRegistry,
    subagent_builder: SubagentBuilder | None = None,
    log_dir: Path | None = None,
) -> tuple[BaseAgent[Any], ToolRegistry]:
    """Construct a provider-specific BaseAgent and its ToolRegistry from an AgentConfig."""
    return _build_agent_and_registry(
        agent_config=agent_config,
        agent_clients=agent_clients,
        system_prompt=system_prompt,
        owner_id=owner_id,
        tool_names=agent_config.tools,
        file_registry=file_registry,
        subagent_builder=subagent_builder,
        log_dir=log_dir,
    )


def build_subagent(
    parent_agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    file_registry: FileRegistry,
    system_prompt: str,
    owner_id: str,
    tool_names: list[str],
) -> tuple[BaseAgent[Any], ToolRegistry]:
    """Build a subagent + ToolRegistry using the shared FileRegistry.

    Reuses the parent's provider/model/max_tokens. No subagent_builder or
    log_dir is forwarded, so the subagent cannot recursively spawn subagents —
    ToolRegistry.from_names will raise if spawn_subagent is in tool_names.
    """
    return _build_agent_and_registry(
        agent_config=parent_agent_config,
        agent_clients=agent_clients,
        system_prompt=system_prompt,
        owner_id=owner_id,
        tool_names=tool_names,
        file_registry=file_registry,
    )


def make_agent_builder(
    agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    file_registry: FileRegistry,
) -> AgentBuilder:
    """Return a closure that builds an agent+registry given system_prompt, owner_id, subagent_builder, log_dir."""

    def builder(
        system_prompt: str,
        owner_id: str,
        subagent_builder: SubagentBuilder | None,
        log_dir: Path | None,
    ) -> tuple[BaseAgent[Any], ToolRegistry]:
        return build_agent(
            agent_config=agent_config,
            agent_clients=agent_clients,
            system_prompt=system_prompt,
            owner_id=owner_id,
            file_registry=file_registry,
            subagent_builder=subagent_builder,
            log_dir=log_dir,
        )

    return builder


def make_subagent_builder(
    parent_agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    file_registry: FileRegistry,
) -> SubagentBuilder:
    """Return a closure that builds a subagent+registry given (system_prompt, owner_id, tool_names)."""

    def builder(system_prompt: str, owner_id: str, tool_names: list[str]) -> tuple[BaseAgent[Any], ToolRegistry]:
        return build_subagent(
            parent_agent_config=parent_agent_config,
            agent_clients=agent_clients,
            file_registry=file_registry,
            system_prompt=system_prompt,
            owner_id=owner_id,
            tool_names=tool_names,
        )

    return builder


def build_goal_agent(
    parent_agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    file_registry: FileRegistry,
    owner_id: str,
) -> tuple[BaseAgent[Any], ToolRegistry]:
    """Build the reviewer agent + its ToolRegistry.

    Uses the same provider as the parent agent. Model and max_tokens are left at
    provider defaults — the parent's overrides are intentionally not forwarded.
    Tools are filtered to the read-only subset of the parent's tool list.
    """
    read_only_tool_names = filter_read_only(parent_agent_config.tools)
    goal_agent_config = AgentConfig(
        provider=parent_agent_config.provider,
        tools=read_only_tool_names,
    )

    return _build_agent_and_registry(
        agent_config=goal_agent_config,
        agent_clients=agent_clients,
        system_prompt=GOAL_REVIEWER_SYSTEM_PROMPT,
        owner_id=owner_id,
        tool_names=read_only_tool_names,
        file_registry=file_registry,
    )


def make_goal_agent_builder(
    parent_agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    file_registry: FileRegistry,
) -> GoalAgentBuilder:
    """Return a closure that builds a (reviewer_agent, reviewer_registry) tuple."""

    def builder(owner_id: str) -> tuple[BaseAgent[Any], ToolRegistry]:
        return build_goal_agent(
            parent_agent_config=parent_agent_config,
            agent_clients=agent_clients,
            file_registry=file_registry,
            owner_id=owner_id,
        )

    return builder
