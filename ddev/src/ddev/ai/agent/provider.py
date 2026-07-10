# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from functools import cached_property
from typing import Any, Protocol

import anthropic

from ddev.ai.agent.anthropic_client import AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.registry import ToolRegistry


class AgentProvider(Protocol):
    """Provider-specific agent construction and configuration validation."""

    def validate_config(self, agent_config: AgentConfig): ...

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]: ...


class AnthropicProvider:
    """Builds Anthropic agents and lazily owns their shared SDK client."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    @cached_property
    def client(self) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(api_key=self._api_key)

    def validate_config(self, agent_config: AgentConfig):
        """Validate Anthropic-specific agent configuration."""

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]:
        kwargs: dict[str, Any] = {}
        if agent_config.model is not None:
            kwargs["model"] = agent_config.model
        if agent_config.max_tokens is not None:
            kwargs["max_tokens"] = agent_config.max_tokens
        return AnthropicAgent(
            client=self.client,
            tools=tools,
            system_prompt=system_prompt,
            name=owner_id,
            **kwargs,
        )
