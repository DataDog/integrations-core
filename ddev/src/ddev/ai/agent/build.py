# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from ddev.ai.agent.base import BaseAgent
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.agent.scope import AgentScope
    from ddev.ai.react.factory import ReActProcessFactory


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
        process_factory: ReActProcessFactory,
        scope: AgentScope,
    ) -> AgentRuntime: ...


class AgentRuntimeBuilder(Protocol):
    """Callable interface for building an AgentRuntime from explicit keyword inputs."""

    def __call__(
        self,
        *,
        agent_config: AgentConfig,
        system_prompt: str,
        process_factory: ReActProcessFactory,
        scope: AgentScope,
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
        process_factory: ReActProcessFactory,
        scope: AgentScope,
    ) -> AgentRuntime:
        """Build an AgentRuntime from the given configuration."""
        tool_registry = ToolRegistry.from_names(
            agent_config.tools,
            scope=scope,
            file_registry=self._file_registry,
            agent_config=agent_config,
            # forwarded untouched to tools that spawn child agents
            process_factory=process_factory,
        )
        agent = self._provider_registry.build_agent(
            agent_config,
            tools=tool_registry,
            system_prompt=system_prompt,
            owner_id=scope.owner_id,
        )
        return AgentRuntime(agent=agent, tool_registry=tool_registry)
