# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import uuid
from datetime import UTC, datetime
from functools import cached_property, partial
from pathlib import Path
from typing import Final

from ddev.ai.agent.build import AgentRuntimeFactory, AgentRuntimeFactoryProtocol
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.ai.tools.http.http_get import HttpGetTool
from ddev.ai.tools.http.http_post import HttpPostTool
from ddev.ai.tools.http.response_store import ResponseStore

HTTP_RESPONSES_DIR_NAME: Final = "http_responses"


def new_execution_id() -> str:
    """A sortable, unique ID for one launch or resume of a run."""
    return f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


class RunResources:
    """Supplies the raw resources phases use to build their runtime factories."""

    def __init__(
        self,
        provider_registry: AgentProviderRegistry,
        file_access_policy: FileAccessPolicy,
        agents: dict[str, AgentConfig],
        callbacks: Callbacks,
        run_root: Path | None = None,
    ) -> None:
        self._provider_registry = provider_registry
        self._file_access_policy = file_access_policy
        self._agents = agents
        self._callbacks = callbacks
        self._run_root = run_root

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
        store = None
        if self._run_root is not None:
            # Each launch or resume writes to its own directory, so earlier executions' files are kept.
            store = ResponseStore(self._run_root / HTTP_RESPONSES_DIR_NAME / new_execution_id())
        return AgentRuntimeFactory(
            provider_registry=self._provider_registry,
            file_registry=self.file_registry,
            tool_factories={
                "http_get": partial(HttpGetTool, store=store),
                "http_post": partial(HttpPostTool, store=store),
            },
        )

    @cached_property
    def process_factory(self) -> ReActProcessFactory:
        """Run-wide factory that creates scoped ReActProcesses."""
        return ReActProcessFactory(
            self.agent_runtime_factory.build_runtime,
            self._callbacks,
        )
