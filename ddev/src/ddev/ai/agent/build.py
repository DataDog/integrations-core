# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.phases.config import AgentConfig

AgentBuilder = Callable[[str, str], tuple[BaseAgent[Any], ToolRegistry]]


def _resolve_client(agent_clients: dict[str, Any], provider: str) -> Any:
    client = agent_clients.get(provider)
    if client is None:
        raise ValueError(f"No client provided for agent provider {provider!r}")
    return client


def build_agent(
    agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    system_prompt: str,
    owner_id: str,
    file_registry: FileRegistry,
) -> tuple[BaseAgent[Any], ToolRegistry]:
    """Construct a provider-specific BaseAgent and its ToolRegistry from an AgentConfig."""

    tool_registry = ToolRegistry.from_names(
        agent_config.tools,
        owner_id=owner_id,
        file_registry=file_registry,
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


def make_agent_builder(
    agent_config: AgentConfig,
    agent_clients: dict[str, Any],
    file_registry: FileRegistry,
) -> AgentBuilder:
    """Return a closure that builds an agent+registry given a rendered system_prompt and owner_id."""

    def builder(system_prompt: str, owner_id: str) -> tuple[BaseAgent[Any], ToolRegistry]:
        return build_agent(
            agent_config=agent_config,
            agent_clients=agent_clients,
            system_prompt=system_prompt,
            owner_id=owner_id,
            file_registry=file_registry,
        )

    return builder
