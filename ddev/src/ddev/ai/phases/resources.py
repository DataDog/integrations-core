# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ddev.ai.agent.build import AgentRuntimeFactory
    from ddev.ai.phases.config import AgentConfig


class ResourceUnavailableError(Exception):
    """Raised when a phase requests a resource the provider cannot supply."""


class PhaseResources(Protocol):
    """Run-scoped services available to phase builders."""

    def agent_config(self, name: str) -> AgentConfig: ...

    def agent_runtime_factory(self) -> AgentRuntimeFactory: ...
