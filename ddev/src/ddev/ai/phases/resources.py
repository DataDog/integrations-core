# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Protocol

from ddev.ai.agent.build import AgentRuntimeFactory
from ddev.ai.phases.config import AgentConfig
from ddev.ai.tools.fs.file_registry import FileRegistry


class ResourceUnavailableError(Exception):
    """Raised when a phase requests a resource the provider cannot supply."""


class PhaseResources(Protocol):
    """Run-scoped services available to phase builders."""

    def agent_config(self, name: str) -> AgentConfig: ...

    def agent_runtime_factory(self) -> AgentRuntimeFactory: ...

    def file_registry(self) -> FileRegistry: ...
