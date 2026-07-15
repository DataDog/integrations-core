# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from functools import cached_property

from ddev.ai.agent.build import AgentRuntimeFactory, AgentRuntimeFactoryProtocol
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry


class RunResources:
    """Supplies the raw resources phases use to build their runtime factories."""

    def __init__(
        self,
        provider_registry: AgentProviderRegistry,
        file_access_policy: FileAccessPolicy,
        agents: dict[str, AgentConfig],
        callbacks: Callbacks,
    ) -> None:
        self._provider_registry = provider_registry
        self._file_access_policy = file_access_policy
        self._agents = agents
        self._callbacks = callbacks

    @cached_property
    def file_registry(self) -> FileRegistry:
        """Lazily-built, run-wide singleton FileRegistry."""
        return FileRegistry(policy=self._file_access_policy)

    def agent_config(self, name: str) -> AgentConfig:
        """Resolve a flow agent definition by name; typed error if absent."""
        try:
            return self._agents[name]
        except KeyError as e:
            raise ResourceUnavailableError(f"No agent definition named {name!r}. Known: {sorted(self._agents)}") from e

    @cached_property
    def agent_runtime_factory(self) -> AgentRuntimeFactoryProtocol:
        """Ready-to-use generic runtime factory."""
        return AgentRuntimeFactory(
            provider_registry=self._provider_registry,
            file_registry=self.file_registry,
        )

    @cached_property
    def process_factory(self) -> ReActProcessFactory:
        """Run-wide factory that creates scoped ReActProcesses."""
        return ReActProcessFactory(
            self.agent_runtime_factory.build_runtime,
            self._callbacks,
        )
