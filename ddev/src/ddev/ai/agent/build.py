# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry


@dataclass(frozen=True)
class AgentRuntime:
    agent: BaseAgent[Any]
    tool_registry: ToolRegistry


class AgentRuntimeFactory(Protocol):
    """Interface for constructing an agent runtime from explicit runtime inputs."""

    def build_runtime(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
    ) -> AgentRuntime: ...


class AgentRuntimeBuilder(Protocol):
    """Callable interface for building an AgentRuntime from explicit keyword inputs."""

    def __call__(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
    ) -> AgentRuntime: ...


class DefaultAgentRuntimeFactory:
    """Builds provider-specific agent runtimes from explicit runtime inputs."""

    def __init__(
        self,
        *,
        agent_clients: dict[str, Any],
        file_registry: FileRegistry,
        artifact_root: Path,
    ) -> None:
        self._agent_clients = agent_clients
        self._file_registry = file_registry
        self._artifact_root = artifact_root

    def _resolve_client(self, provider: str) -> Any:
        client = self._agent_clients.get(provider)
        if client is None:
            raise ValueError(f"No client provided for agent provider {provider!r}")
        return client

    def _build_provider_agent(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
        tool_registry: ToolRegistry,
    ) -> BaseAgent[Any]:
        if agent_config.provider == "anthropic":
            kwargs: dict[str, Any] = {}
            if agent_config.model is not None:
                kwargs["model"] = agent_config.model
            if agent_config.max_tokens is not None:
                kwargs["max_tokens"] = agent_config.max_tokens
            return AnthropicAgent(
                client=self._resolve_client("anthropic"),
                tools=tool_registry,
                system_prompt=system_prompt,
                name=owner_id,
                **kwargs,
            )
        raise ValueError(f"Unknown agent provider: {agent_config.provider!r}")

    def build_runtime(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        owner_id: str,
    ) -> AgentRuntime:
        """Build an agent and its tools from the given configuration."""
        tool_registry = ToolRegistry.from_names(
            agent_config.tools,
            owner_id=owner_id,
            file_registry=self._file_registry,
            agent_config=agent_config,
            runtime_builder=self.build_runtime,
            artifact_root=self._artifact_root,
        )
        agent = self._build_provider_agent(
            agent_config=agent_config,
            system_prompt=system_prompt,
            owner_id=owner_id,
            tool_registry=tool_registry,
        )
        return AgentRuntime(agent=agent, tool_registry=tool_registry)
