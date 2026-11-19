# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

import anthropic

from ddev.ai.agent.anthropic_agent import DEFAULT_MAX_TOKENS, AnthropicAgent
from ddev.ai.agent.anthropic_client import check_messages_access, messages_client
from ddev.ai.agent.base import BaseAgent
from ddev.ai.config.models import AgentConfig
from ddev.ai.model_catalog import ANTHROPIC, ModelResolver, ResolvedModel, Route
from ddev.ai.tools.registry import ToolRegistry

if TYPE_CHECKING:
    from ddev.ai.agent.provider import ModelAccessCheck
    from ddev.ai.runtime.connections import RouteConnection

DEFAULT_MODEL: Final[str] = "sonnet"


class AnthropicProvider:
    """Resolves model bindings and builds agents with an Anthropic Messages client."""

    def __init__(
        self,
        *,
        resolver: ModelResolver | None = None,
        connection: RouteConnection | None = None,
    ) -> None:
        self._resolver = ModelResolver() if resolver is None else resolver
        self._connection = connection
        self._client: anthropic.AsyncAnthropic | None = None

    def for_run(self, connection: RouteConnection) -> AnthropicProvider:
        return AnthropicProvider(resolver=self._resolver, connection=connection)

    @property
    def client(self) -> anthropic.AsyncAnthropic:
        if self._client is None:
            self._client = messages_client(self._run_connection())
        return self._client

    def _run_connection(self) -> RouteConnection:
        if self._connection is None:
            raise ValueError("Agent execution requires prepared run resources.")
        return self._connection

    async def check_access(self, agent_config: AgentConfig) -> ModelAccessCheck:
        model = self.resolve_model(agent_config.model)
        return await check_messages_access(self.client, model)

    async def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            await client.close()

    def default_model(self) -> str:
        return DEFAULT_MODEL

    def supported_models(self) -> frozenset[str]:
        """The names this provider handles: aliases and canonical models."""
        return self._resolver.names_for(ANTHROPIC)

    def resolve_model(self, model: str) -> ResolvedModel:
        """Resolve a model name to its binding on the captured route."""
        connection = self._run_connection()
        resolved = self._resolver.resolve(model, route=connection.route, provider=ANTHROPIC)
        connection.validate_binding(resolved)
        return resolved

    def validate_config(self, agent_config: AgentConfig, *, route: Route | None = None) -> None:
        """Validate model limits and, when known, the binding selected for execution."""
        if self._connection is not None:
            resolved = self.resolve_model(agent_config.model)
            canonical, spec = resolved.canonical, resolved.model
        elif route is not None:
            resolved = self._resolver.resolve(agent_config.model, route=route, provider=ANTHROPIC)
            canonical, spec = resolved.canonical, resolved.model
        else:
            canonical, spec = self._resolver.model_spec(agent_config.model, provider=ANTHROPIC)
        requested = DEFAULT_MAX_TOKENS if agent_config.max_tokens is None else agent_config.max_tokens
        if spec.max_output_tokens is not None and requested > spec.max_output_tokens:
            raise ValueError(
                f"max_tokens {requested} exceeds the {spec.max_output_tokens}-token output limit of model {canonical!r}"
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
