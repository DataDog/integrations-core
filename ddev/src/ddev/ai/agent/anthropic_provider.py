# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from functools import cached_property
from typing import Any, Final

import anthropic

from ddev.ai.agent.anthropic_agent import AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.tools.registry import ToolRegistry

# Friendly model aliases users write in agent configs, mapped to concrete Anthropic model strings.
MODEL_ALIASES: Final[dict[str, str]] = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-5",
    "haiku": "claude-haiku-4-5",
}
DEFAULT_MODEL: Final[str] = "sonnet"


class AnthropicProvider:
    """Builds Anthropic agents and lazily owns their shared SDK client."""

    def __init__(self, api_key: str):
        self._api_key = api_key

    @cached_property
    def client(self) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(api_key=self._api_key)

    def default_model(self) -> str:
        return DEFAULT_MODEL

    def supported_models(self) -> frozenset[str]:
        """The model aliases this provider handles."""
        return frozenset(MODEL_ALIASES)

    def _cast_model(self, model: str) -> str:
        """Resolve a model alias to its concrete Anthropic model string."""
        if resolved_model := MODEL_ALIASES.get(model.lower()):
            return resolved_model
        valid = ", ".join(sorted(MODEL_ALIASES))
        raise ValueError(f"Unknown model {model!r} for the anthropic provider. Valid models: {valid}")

    def validate_config(self, agent_config: AgentConfig):
        """Validate Anthropic-specific agent configuration."""
        self._cast_model(agent_config.model)

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]:
        kwargs: dict[str, Any] = {"model": self._cast_model(agent_config.model)}
        if agent_config.max_tokens is not None:
            kwargs["max_tokens"] = agent_config.max_tokens
        return AnthropicAgent(
            client=self.client,
            tools=tools,
            system_prompt=system_prompt,
            name=owner_id,
            **kwargs,
        )
