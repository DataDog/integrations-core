# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Any, Protocol

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.provider import AgentProvider, AnthropicProvider
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.registry import ToolRegistry


class AgentProviderConfig(Protocol):
    """App configuration needed to create the provider registry."""

    anthropic_api_key: str | None


class AgentProviderRegistry:
    """Dispatches agent construction to configured providers."""

    def __init__(self):
        self._providers: dict[str, AgentProvider] = {}

    def register(self, name: str, provider: AgentProvider):
        if name in self._providers:
            raise ValueError(f"Agent provider {name!r} is already registered")
        self._providers[name] = provider

    def contains(self, name: str) -> bool:
        return name in self._providers

    def _get_provider(self, name: str) -> AgentProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ValueError(f"Agent provider {name!r} is not available")
        return provider

    def validate_config(self, agent_config: AgentConfig):
        self._get_provider(agent_config.provider).validate_config(agent_config)

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]:
        provider = self._get_provider(agent_config.provider)
        return provider.build_agent(
            agent_config,
            tools=tools,
            system_prompt=system_prompt,
            owner_id=owner_id,
        )


def build_agent_provider_registry(config: AgentProviderConfig) -> AgentProviderRegistry:
    """Build the provider registry from ddev app configuration."""
    registry = AgentProviderRegistry()
    if config.anthropic_api_key:
        registry.register("anthropic", AnthropicProvider(config.anthropic_api_key))
    return registry
