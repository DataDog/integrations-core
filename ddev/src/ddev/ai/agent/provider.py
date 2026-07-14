# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import Any, Protocol

from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.registry import ToolRegistry


class AgentProvider(Protocol):
    """Provider-specific agent construction and configuration validation."""

    def supported_models(self) -> frozenset[str]:
        """The model aliases this provider handles."""
        ...

    def validate_config(self, agent_config: AgentConfig): ...

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]: ...
