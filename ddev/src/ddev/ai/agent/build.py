# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Protocol

import anthropic

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.react.factory import ReActProcessFactory


class AgentProviderConfig(Protocol):
    """App configuration needed to create the provider registry."""

    anthropic_api_key: str | None


@dataclass(frozen=True)
class AgentRuntime:
    agent: BaseAgent[Any]
    tool_registry: ToolRegistry


class AgentRuntimeFactoryProtocol(Protocol):
    """Interface for constructing an agent runtime from explicit runtime inputs."""

    def build_runtime(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
        process_factory: ReActProcessFactory,
    ) -> AgentRuntime: ...


class AgentProvider(Protocol):
    """Provider-specific agent construction and configuration validation."""

    def validate_config(self, agent_config: AgentConfig) -> None: ...

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]: ...


class AgentProviderRegistry:
    """Dispatches agent construction to configured providers."""

    def __init__(self) -> None:
        self._providers: dict[str, AgentProvider] = {}

    def register(self, name: str, provider: AgentProvider) -> None:
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

    def validate_config(self, agent_config: AgentConfig) -> None:
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
        provider.validate_config(agent_config)
        return provider.build_agent(
            agent_config,
            tools=tools,
            system_prompt=system_prompt,
            owner_id=owner_id,
        )


class AnthropicProvider:
    """Builds Anthropic agents and lazily owns their shared SDK client."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    @cached_property
    def client(self) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(api_key=self._api_key)

    def validate_config(self, agent_config: AgentConfig) -> None:
        """Validate Anthropic-specific agent configuration."""

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]:
        kwargs: dict[str, Any] = {}
        if agent_config.model is not None:
            kwargs["model"] = agent_config.model
        if agent_config.max_tokens is not None:
            kwargs["max_tokens"] = agent_config.max_tokens
        return AnthropicAgent(
            client=self.client,
            tools=tools,
            system_prompt=system_prompt,
            name=owner_id,
            **kwargs,
        )


def build_agent_provider_registry(config: AgentProviderConfig) -> AgentProviderRegistry:
    """Build the provider registry from ddev app configuration."""
    registry = AgentProviderRegistry()
    if config.anthropic_api_key:
        registry.register("anthropic", AnthropicProvider(config.anthropic_api_key))
    return registry


class AgentRuntimeBuilder(Protocol):
    """Callable interface for building an AgentRuntime from explicit keyword inputs."""

    def __call__(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
        process_factory: ReActProcessFactory,
    ) -> AgentRuntime: ...


class AgentRuntimeFactory:
    """Build tool registries and provider-specific agents for a run."""

    def __init__(
        self,
        *,
        provider_registry: AgentProviderRegistry,
        file_registry: FileRegistry,
    ) -> None:
        self._provider_registry = provider_registry
        self._file_registry = file_registry

    def build_runtime(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
        process_factory: ReActProcessFactory,
    ) -> AgentRuntime:
        """Build an AgentRuntime from the given configuration."""
        tool_registry = ToolRegistry.from_names(
            agent_config.tools,
            owner_id=owner_id,
            file_registry=self._file_registry,
            agent_config=agent_config,
            # forwarded untouched to tools that spawn child agents
            process_factory=process_factory,
        )
        agent = self._provider_registry.build_agent(
            agent_config,
            tools=tool_registry,
            system_prompt=system_prompt,
            owner_id=owner_id,
        )
        return AgentRuntime(agent=agent, tool_registry=tool_registry)
