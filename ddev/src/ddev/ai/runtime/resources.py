# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any

from ddev.ai.agent.build import AgentRuntimeFactory, DefaultAgentRuntimeFactory
from ddev.ai.phases.config import AgentConfig
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry


class RunResources:
    """Supplies the raw resources phases use to build their runtime factories."""

    def __init__(
        self,
        agent_clients: dict[str, Any],
        file_access_policy: FileAccessPolicy,
        agents: dict[str, AgentConfig],
        artifact_root: Path,
    ) -> None:
        self._agent_clients = agent_clients
        self._file_access_policy = file_access_policy
        self._agents = agents
        self._artifact_root = artifact_root
        self._file_registry: FileRegistry | None = None
        self._agent_runtime_factory: AgentRuntimeFactory | None = None

    def agent_clients(self) -> dict[str, Any]:
        """Raw provider-name -> SDK client map."""
        return dict(self._agent_clients)

    def file_registry(self) -> FileRegistry:
        """Lazily-built, run-wide singleton FileRegistry."""
        if self._file_registry is None:
            self._file_registry = FileRegistry(policy=self._file_access_policy)
        return self._file_registry

    def agent_config(self, name: str) -> AgentConfig:
        """Resolve a flow agent definition by name; typed error if absent."""
        try:
            return self._agents[name]
        except KeyError as e:
            raise ResourceUnavailableError(
                f"No agent definition named {name!r}. Known: {sorted(self._agents)}"
            ) from e

    def agent_runtime_factory(self) -> AgentRuntimeFactory:
        """Return a ready-to-use generic runtime factory."""
        if self._agent_runtime_factory is None:
            self._agent_runtime_factory = DefaultAgentRuntimeFactory(
                agent_clients=self._agent_clients,
                file_registry=self.file_registry(),
                artifact_root=self._artifact_root,
            )
        return self._agent_runtime_factory
