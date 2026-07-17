# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Any, Protocol

from ddev.ai.agent.anthropic_provider import AnthropicProvider
from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.provider import AgentProvider
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.registry import ToolRegistry


class AgentProviderConfig(Protocol):
    """App configuration needed to create the provider registry."""

    anthropic_api_key: str | None


class AgentProviderRegistry:
    """Dispatches agent construction to configured providers."""

    def __init__(self):
        self._providers: dict[str, AgentProvider] = {}
        self._model_index: dict[str, set[str]] = {}

    def register(self, name: str, provider: AgentProvider):
        if name in self._providers:
            raise ValueError(f"Agent provider {name!r} is already registered")
        for model in provider.supported_models():
            self._model_index.setdefault(model.lower(), set()).add(name)
        self._providers[name] = provider

    def contains(self, name: str) -> bool:
        return name in self._providers

    def provider_for_model(self, model: str) -> str:
        providers = self._model_index.get(model.lower())
        if not providers:
            raise ValueError(f"Unknown model {model!r}")
        if len(providers) > 1:
            owners = ", ".join(repr(owner) for owner in sorted(providers))
            raise ValueError(f"Model {model!r} is served by multiple providers ({owners}); specify a provider")
        return next(iter(providers))

    def default_model_for_provider(self, name: str) -> str:
        return self._get_provider(name).default_model()

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
