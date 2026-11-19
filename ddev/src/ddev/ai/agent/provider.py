# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Any, NamedTuple, Protocol

from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.model_catalog import Route
    from ddev.ai.runtime.connections import RouteConnection


class ModelAccessCheck(NamedTuple):
    """Startup probe status and whether the response named the requested model."""

    status: int
    requested_model: str
    model_confirmed: bool


class AgentProvider(Protocol):
    """Provider-specific agent construction and configuration validation."""

    def default_model(self) -> str:
        """The default model alias for this provider."""
        ...

    def supported_models(self) -> frozenset[str]:
        """The model aliases this provider handles."""
        ...

    def validate_config(self, agent_config: AgentConfig, *, route: Route | None = None) -> None: ...

    def for_run(self, connection: RouteConnection) -> AgentProvider:
        """Bind the adapter to a run without changing the configuration registry."""
        ...

    async def check_access(self, agent_config: AgentConfig) -> ModelAccessCheck:
        """Probe access to the configured model without exposing credentials or response bodies."""
        ...

    async def close(self) -> None:
        """Release resources opened by the run-bound adapter."""
        ...

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]: ...
