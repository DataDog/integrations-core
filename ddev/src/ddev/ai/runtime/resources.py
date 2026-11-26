# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from ddev.ai.agent.build import AgentRuntimeFactory, AgentRuntimeFactoryProtocol
from ddev.ai.agent.exceptions import AgentConnectionError, ModelAccessError
from ddev.ai.agent.provider import ModelAccessCheck
from ddev.ai.agent.registry import AgentProviderRegistry
from ddev.ai.callbacks.callbacks import Callbacks
from ddev.ai.config.models import AgentConfig
from ddev.ai.model_catalog import Route
from ddev.ai.phases.resources import ResourceUnavailableError
from ddev.ai.react.factory import ReActProcessFactory
from ddev.ai.runtime.connections import DirectConnection, GatewayConnection, RouteConnection
from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
from ddev.ai.runtime.gateway_auth import (
    DD_AUTH_INSTALL_HELP,
    LOGIN_HELP,
    REPLACE_PAT_HELP,
    GatewayAuthError,
    GatewayTokenProducer,
)
from ddev.ai.runtime.login_prompt import LoginPrompt
from ddev.ai.runtime.tokens import TokenProducer
from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy
from ddev.ai.tools.fs.file_registry import FileRegistry
from ddev.config.model import ConfigurationError


@dataclass(frozen=True)
class RunRoute:
    """Record the route requested in config and the route fixed at startup for the whole run.

    The routes differ only on fallback; the reason is shown in the run log and TUI.
    """

    requested: Route
    effective: Route
    fallback_reason: str | None = None

    def describe(self) -> str:
        """Summarize the route choice without including credentials."""
        description = f"Requested route: {self.requested}; effective route: {self.effective}."
        if self.fallback_reason:
            return f"{description} {self.fallback_reason} AI Gateway access was not checked."
        return description


class RunResources:
    """Owns a run's model clients and credentials and supplies resources to its phases."""

    def __init__(
        self,
        provider_registry: AgentProviderRegistry,
        file_access_policy: FileAccessPolicy,
        agents: dict[str, AgentConfig],
        callbacks: Callbacks,
        *,
        gateway_login_prompt: LoginPrompt | None = None,
    ) -> None:
        self._configured_registry = provider_registry
        self._run_registry: AgentProviderRegistry | None = None
        self._file_access_policy = file_access_policy
        self._agents = agents
        self._callbacks = callbacks
        self._tokens: TokenProducer | None = None
        self._gateway_tokens: GatewayTokenProducer | None = None
        self._gateway_login_prompt = gateway_login_prompt
        self._connection: RouteConnection | None = None
        self._route: RunRoute | None = None

    async def prepare(
        self, report_route: Callable[[RunRoute], None], *, initial_agent: AgentConfig | None
    ) -> ModelAccessCheck | None:
        """Validate every model on the chosen route, then probe the first scheduled Gateway model.

        Fall back to direct execution only when `dd-auth` is missing, not when the Gateway denies access.
        """
        requested = self._configured_registry.requested_route
        reason = None
        gateway_tokens = GatewayTokenProducer(self._gateway_login_prompt) if requested is Route.AI_GATEWAY else None
        if gateway_tokens is not None and not gateway_tokens.available:
            gateway_tokens = None
            reason = "dd-auth was not found on PATH."

        gateway_connection = None
        if gateway_tokens is None:
            direct_tokens = self._configured_registry.direct_tokens_for_run()
            tokens: TokenProducer = direct_tokens
            connection: RouteConnection = DirectConnection(direct_tokens)
        else:
            direct_tokens = None
            tokens = gateway_tokens
            gateway_connection = GatewayConnection(gateway_tokens, token_for_probe=gateway_tokens.token_for_probe)
            connection = gateway_connection
        self._tokens = tokens
        self._gateway_tokens = gateway_tokens
        self._connection = connection
        registry = self._configured_registry.for_run(connection)
        self._run_registry = registry
        try:
            for config in self._agents.values():
                registry.validate_config(config)
            if reason is not None and direct_tokens is not None:
                for provider in {config.provider for config in self._agents.values()}:
                    if not direct_tokens.has_key(provider):
                        raise GatewayAuthError(f"No direct credential is configured for {provider}.")
        except (ConfigurationError, GatewayAuthError, ValueError) as error:
            if reason is not None:
                raise GatewayAuthError(
                    f"Requested route: ai-gateway; no effective route. {reason} "
                    f"{DD_AUTH_INSTALL_HELP} Direct fallback unavailable: {error}"
                ) from None
            raise

        self._route = RunRoute(requested, connection.route, reason)
        report_route(self._route)
        if gateway_tokens is None or gateway_connection is None:
            return None
        check = await self._check_gateway_access(registry, gateway_tokens, initial_agent) if initial_agent else None
        gateway_connection.finish_startup()
        return check

    @staticmethod
    async def _check_gateway_access(
        registry: AgentProviderRegistry, tokens: GatewayTokenProducer, agent: AgentConfig
    ) -> ModelAccessCheck:
        try:
            token = await tokens.token_for(agent.provider, startup=True)
            try:
                return await registry.check_access(agent)
            except ModelAccessError as error:
                if error.status_code != 401:
                    raise
            tokens.reject(token)
            await tokens.token_for(agent.provider, startup=True)
            return await registry.check_access(agent)
        except CredentialRefreshError as error:
            if error.cause is RefreshFailureCause.CREDENTIAL_UNCHANGED:
                # No phase has started; give startup retry guidance instead of interrupted-phase Resume steps.
                raise GatewayAuthError(f"AI Gateway startup check failed. {error.cause} {REPLACE_PAT_HELP}") from None
            raise
        except AgentConnectionError as error:
            if error.timed_out:
                raise GatewayAuthError(f"AI Gateway startup check timed out. Retry the run. {LOGIN_HELP}") from None
            raise AgentConnectionError(f"AI Gateway startup connection failed. Retry the run. {LOGIN_HELP}") from None
        except ModelAccessError as error:
            if error.status_code == 401:
                cause = RefreshFailureCause.REPLACEMENT_REJECTED
                raise GatewayAuthError(f"AI Gateway startup check failed. {cause} {REPLACE_PAT_HELP}") from None
            raise GatewayAuthError(f"AI Gateway startup check failed. Retry the run. {LOGIN_HELP}") from None
        except asyncio.CancelledError as error:
            error.add_note(f"AI Gateway startup cancelled. {LOGIN_HELP}")
            raise

    @property
    def gateway_login_interrupted(self) -> bool:
        return self._gateway_tokens is not None and self._gateway_tokens.login_interrupted

    async def close(self) -> None:
        """Drop the run's credentials and close its bound providers."""
        tokens, self._tokens = self._tokens, None
        self._gateway_tokens = None
        if tokens is not None:
            tokens.clear()
        registry, self._run_registry = self._run_registry, None
        connection, self._connection = self._connection, None
        self._route = None
        try:
            if registry is not None:
                await registry.close()
        finally:
            if connection is not None:
                await connection.aclose()

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
        return AgentRuntimeFactory(
            provider_registry=self._run_registry or self._configured_registry,
            file_registry=self.file_registry,
        )

    @cached_property
    def process_factory(self) -> ReActProcessFactory:
        """Run-wide factory that creates scoped ReActProcesses."""
        return ReActProcessFactory(
            self.agent_runtime_factory.build_runtime,
            self._callbacks,
        )
