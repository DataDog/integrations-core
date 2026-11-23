# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import AsyncMock, Mock

import httpx2
import pytest

from ddev.ai.runtime.connections import DirectAuthScheme, DirectConnection, GatewayConnection, RouteConnection
from ddev.ai.runtime.gateway_transport import GATEWAY_BASE_URL
from ddev.ai.runtime.tokens import DirectTokenProducer, TokenProducer


async def test_direct_connection_applies_the_adapters_auth_scheme():
    def handle(request: httpx2.Request) -> httpx2.Response:
        assert request.headers.get_list("x-provider-key") == ["selected-key"]
        assert "authorization" not in request.headers
        assert "x-api-key" not in request.headers
        return httpx2.Response(200)

    tokens = DirectTokenProducer({"other": lambda: "other-key", "selected": lambda: "selected-key"})
    connection = DirectConnection(tokens, transport=httpx2.MockTransport(handle))
    try:
        transport = connection.transport("selected", direct_auth=DirectAuthScheme("X-Provider-Key"))
        async with httpx2.AsyncClient(transport=transport) as client:
            response = await client.get(
                "https://provider.example",
                headers={"Authorization": "Bearer sdk-placeholder", "X-Provider-Key": "old", "X-Api-Key": "old"},
            )
        assert response.status_code == 200
    finally:
        await connection.aclose()


@pytest.mark.parametrize("gateway", [True, False], ids=["gateway", "direct"])
async def test_closing_one_client_leaves_the_run_connection_open(gateway, monkeypatch):
    network = httpx2.MockTransport(lambda _: httpx2.Response(200))
    close = AsyncMock(wraps=network.aclose)
    monkeypatch.setattr(network, "aclose", close)
    connection: RouteConnection
    if gateway:
        tokens = Mock(spec=TokenProducer)
        tokens.token_for.return_value = "ddpat_token"
        connection = GatewayConnection(tokens, transport=network)
        base_url = GATEWAY_BASE_URL
    else:
        connection = DirectConnection(DirectTokenProducer({"test": lambda: "key"}), transport=network)
        base_url = "https://provider.example"

    def client() -> httpx2.AsyncClient:
        return httpx2.AsyncClient(
            base_url=base_url,
            transport=connection.transport("test", direct_auth=DirectAuthScheme("Authorization", "Bearer ")),
        )

    try:
        async with client() as remaining:
            async with client() as first:
                assert (await first.get("/models")).status_code == 200
            assert (await remaining.get("/models")).status_code == 200
        close.assert_not_awaited()
    finally:
        await connection.aclose()
    close.assert_awaited_once()
