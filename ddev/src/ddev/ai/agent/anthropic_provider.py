# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from functools import cached_property
from typing import Any, Final

import anthropic

from ddev.ai.agent.anthropic_agent import DEFAULT_MAX_TOKENS, AnthropicAgent
from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.model_catalog import ANTHROPIC, RESOLVER, ModelResolver, ResolvedModel, Route
from ddev.ai.tools.registry import ToolRegistry

DEFAULT_MODEL: Final[str] = "sonnet"
GATEWAY_EXECUTION_PENDING: Final[str] = (
    "Executing models through AI Gateway is not implemented yet; gateway mode currently "
    "supports model resolution and flow validation only"
)


class AnthropicProvider:
    """Builds Anthropic agents and lazily owns their shared SDK client."""

    def __init__(self, api_key: str | None, *, route: Route = Route.DIRECT, resolver: ModelResolver = RESOLVER):
        self._api_key = api_key
        self._route = route
        self._resolver = resolver

    @cached_property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._api_key is None:
            raise ValueError("Direct Anthropic execution requires an API key")
        return anthropic.AsyncAnthropic(api_key=self._api_key)

    def default_model(self) -> str:
        return DEFAULT_MODEL

    def supported_models(self) -> frozenset[str]:
        """The names this provider handles: aliases and canonical models."""
        return self._resolver.names_for(ANTHROPIC)

    def resolve_model(self, model: str) -> ResolvedModel:
        """Resolve a model name to its binding on the captured route."""
        return self._resolver.resolve(model, route=self._route, provider=ANTHROPIC)

    def validate_config(self, agent_config: AgentConfig):
        """Validate Anthropic-specific agent configuration."""
        resolved = self.resolve_model(agent_config.model)
        # Unset falls back to the agent default.
        requested = DEFAULT_MAX_TOKENS if agent_config.max_tokens is None else agent_config.max_tokens
        output_limit = resolved.model.max_output_tokens
        if output_limit is not None and requested > output_limit:
            raise ValueError(
                f"max_tokens {requested} exceeds the {output_limit}-token output limit of model {resolved.canonical!r}"
            )

    def build_agent(
        self,
        agent_config: AgentConfig,
        *,
        tools: ToolRegistry,
        system_prompt: str,
        owner_id: str,
    ) -> BaseAgent[Any]:
        resolved = self.resolve_model(agent_config.model)
        if self._route is Route.AI_GATEWAY:
            raise ValueError(GATEWAY_EXECUTION_PENDING)
        kwargs: dict[str, Any] = {}
        if agent_config.max_tokens is not None:
            kwargs["max_tokens"] = agent_config.max_tokens
        return AnthropicAgent(
            client=self.client,
            tools=tools,
            system_prompt=system_prompt,
            name=owner_id,
            model=resolved,
            **kwargs,
        )
