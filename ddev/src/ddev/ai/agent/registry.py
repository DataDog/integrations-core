# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Protocol

from ddev.ai.agent.anthropic_provider import AnthropicProvider
from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.provider import AgentProvider, ModelAccessCheck
from ddev.ai.config.models import AgentConfig
from ddev.ai.model_catalog import ANTHROPIC, ModelResolver, Route
from ddev.ai.runtime.connections import RouteConnection
from ddev.ai.runtime.tokens import DirectTokenProducer
from ddev.ai.tools.registry import ToolRegistry


class AgentProviderConfig(Protocol):
    """App configuration needed to create the provider registry."""

    anthropic_api_key: str | None
    use_ai_gateway: bool
    models_catalog: str | None


class AgentProviderRegistry:
    """Dispatches agent construction to configured providers."""

    def __init__(
        self,
        *,
        requested_route: Route = Route.DIRECT,
        make_direct_tokens: Callable[[], DirectTokenProducer] | None = None,
    ) -> None:
        self._providers: dict[str, AgentProvider] = {}
        self._model_index: dict[str, set[str]] = {}
        self.requested_route = requested_route
        self._make_direct_tokens = make_direct_tokens

    def direct_tokens_for_run(self) -> DirectTokenProducer:
        return DirectTokenProducer({}) if self._make_direct_tokens is None else self._make_direct_tokens()

    def for_run(self, connection: RouteConnection) -> AgentProviderRegistry:
        """Bind providers to the effective connection without changing the config registry."""
        registry = AgentProviderRegistry(requested_route=self.requested_route)
        for name, provider in self._providers.items():
            registry.register(name, provider.for_run(connection))
        return registry

    async def check_access(self, config: AgentConfig) -> ModelAccessCheck:
        return await self._get_provider(config.provider).check_access(config)

    async def close(self) -> None:
        async with asyncio.TaskGroup() as group:
            for provider in self._providers.values():
                group.create_task(provider.close())

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

    def validate_config(self, agent_config: AgentConfig) -> None:
        # A Gateway request can still take the direct route at startup.
        route = Route.DIRECT if self.requested_route is Route.DIRECT else None
        self._get_provider(agent_config.provider).validate_config(agent_config, route=route)

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
    # Captured here so later config or file edits cannot reroute agents from this registry.
    route = Route.AI_GATEWAY if config.use_ai_gateway else Route.DIRECT
    resolver = ModelResolver(config.models_catalog) if config.models_catalog else ModelResolver()
    if route is Route.AI_GATEWAY:
        # Do not read direct credentials unless startup needs to fall back.
        registry = AgentProviderRegistry(
            requested_route=route,
            make_direct_tokens=lambda: DirectTokenProducer({ANTHROPIC: lambda: config.anthropic_api_key}),
        )
        registry.register(ANTHROPIC, AnthropicProvider(resolver=resolver))
    else:
        api_key = config.anthropic_api_key
        registry = AgentProviderRegistry(
            requested_route=route, make_direct_tokens=lambda: DirectTokenProducer({ANTHROPIC: lambda: api_key})
        )
        if api_key:
            registry.register(ANTHROPIC, AnthropicProvider(resolver=resolver))
    return registry
