# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import httpx2

from ddev.ai.model_catalog import Route
from ddev.ai.runtime.gateway_transport import (
    ATTRIBUTION_HEADER,
    CREDENTIAL_HEADERS,
    GATEWAY_BASE_URL,
    PROVIDER_HEADER,
    GatewayTransport,
)
from ddev.ai.runtime.tokens import TokenProducer


@dataclass(frozen=True)
class DirectAuthScheme:
    """The header and optional value prefix required by a provider's direct API."""

    header: str
    prefix: str = ""


class RouteConnection(Protocol):
    """Supply transport policy to SDK clients without giving them credentials."""

    @property
    def route(self) -> Route: ...

    @property
    def max_retries(self) -> int: ...

    def base_url(self, protocol: str) -> str | None:
        """Return the route's endpoint, or None to retain the SDK default."""
        ...

    def transport(self, provider: str, *, direct_auth: DirectAuthScheme) -> httpx2.AsyncBaseTransport:
        """Return a client transport borrowing the connection's network resources."""
        ...

    async def aclose(self) -> None: ...


class GatewayConnection:
    route = Route.AI_GATEWAY
    max_retries = 0

    def __init__(
        self,
        tokens: TokenProducer,
        *,
        transport: httpx2.AsyncBaseTransport | None = None,
        token_for_probe: Callable[[], str] | None = None,
    ) -> None:
        self._tokens = tokens
        self._transport = transport
        self._probe_token = token_for_probe

    def finish_startup(self) -> None:
        self._probe_token = None

    def _token_for_probe(self) -> str | None:
        return self._probe_token() if self._probe_token is not None else None

    def base_url(self, protocol: str) -> str:
        return GATEWAY_BASE_URL

    def transport(self, provider: str, *, direct_auth: DirectAuthScheme) -> httpx2.AsyncBaseTransport:
        if self._transport is None:
            self._transport = httpx2.AsyncHTTPTransport(trust_env=False)
        return GatewayTransport(
            self._tokens,
            self._transport,
            provider=provider,
            direct_auth_header=direct_auth.header,
            token_for_probe=self._token_for_probe,
        )

    async def aclose(self) -> None:
        if self._transport is not None:
            await self._transport.aclose()


class DirectConnection:
    route = Route.DIRECT
    max_retries = 2

    def __init__(self, tokens: TokenProducer, *, transport: httpx2.AsyncBaseTransport | None = None) -> None:
        self._tokens = tokens
        self._transport = transport
        self._client: httpx2.AsyncClient | None = None

    def base_url(self, protocol: str) -> None:
        return None

    def transport(self, provider: str, *, direct_auth: DirectAuthScheme) -> httpx2.AsyncBaseTransport:
        # An inner client retains HTTPX's environment proxy handling; installing a custom transport disables it.
        if self._client is None:
            self._client = httpx2.AsyncClient(transport=self._transport, follow_redirects=False)
        return _DirectTransport(self._client, self._tokens, provider, direct_auth)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
        elif self._transport is not None:
            await self._transport.aclose()


class _DirectTransport(httpx2.AsyncBaseTransport):
    def __init__(
        self, client: httpx2.AsyncClient, tokens: TokenProducer, provider: str, scheme: DirectAuthScheme
    ) -> None:
        self._client = client
        self._tokens = tokens
        self._provider = provider
        self._scheme = scheme

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        header = self._scheme.header
        for name in (*CREDENTIAL_HEADERS, PROVIDER_HEADER, ATTRIBUTION_HEADER, header):
            request.headers.pop(name, None)
        request.headers[header] = self._scheme.prefix + await self._tokens.token_for(self._provider)
        try:
            return await self._client.send(request, stream=True)
        finally:
            request.headers.pop(header, None)
