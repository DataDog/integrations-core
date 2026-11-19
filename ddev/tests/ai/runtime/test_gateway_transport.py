# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest.mock import AsyncMock

import httpx2
import pytest

from ddev.ai.runtime.gateway_auth import GatewayAuthError
from ddev.ai.runtime.gateway_transport import GATEWAY_BASE_URL, GatewayTransport


@pytest.mark.parametrize("url", ["http://ai-gateway.datadoghq.com/ai/v1/messages", "https://other.example/messages"])
async def test_gateway_transport_refuses_non_gateway_origin(url):
    token = AsyncMock(return_value="ddpat_gateway_secret")
    handle = AsyncMock()
    transport = GatewayTransport(token, httpx2.MockTransport(handle))
    async with httpx2.AsyncClient(transport=transport) as client:
        with pytest.raises(GatewayAuthError, match="outside its HTTPS origin"):
            await client.post(url)
    token.assert_not_awaited()
    handle.assert_not_awaited()


@pytest.mark.parametrize("location", ["https://other.example/messages", "/ai/v1/other"])
async def test_gateway_does_not_follow_redirects(location):
    handle = AsyncMock(return_value=httpx2.Response(307, headers={"Location": location}))
    transport = GatewayTransport(AsyncMock(return_value="ddpat_gateway_secret"), httpx2.MockTransport(handle))
    async with httpx2.AsyncClient(transport=transport, follow_redirects=True) as client:
        with pytest.raises(GatewayAuthError, match="redirect .*was not followed"):
            await client.post(f"{GATEWAY_BASE_URL}/messages")
    handle.assert_awaited_once()
