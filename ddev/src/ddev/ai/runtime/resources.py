# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from functools import cached_property
from typing import Any

from ddev.ai.agent.build import AgentRuntimeFactory, DefaultAgentRuntimeFactory
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.phases.config import AgentConfig
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry


class RunResources:
    """Supplies the raw resources phases use to build their runtime factories."""

    def __init__(
        self,
        agent_clients: dict[str, Any],
        file_access_policy: FileAccessPolicy,
        agents: dict[str, AgentConfig],
        callbacks: Callbacks,
    ) -> None:
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._agents = agents
        self._callbacks = callbacks

    def agent_clients(self) -> dict[str, Any]:
        """Raw provider-name -> SDK client map."""
        return dict(self._agent_clients)

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
    def agent_runtime_factory(self) -> AgentRuntimeFactory:
        """Ready-to-use generic runtime factory."""
        return DefaultAgentRuntimeFactory(
            agent_clients=self._agent_clients,
            file_registry=self.file_registry,
        )

    @cached_property
    def process_factory(self) -> ReActProcessFactory:
        """Run-wide factory that creates scoped ReActProcesses."""
        return ReActProcessFactory(
            self.agent_runtime_factory.build_runtime,
            self._callbacks,
        )
