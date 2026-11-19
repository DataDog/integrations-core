# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import httpx2

from ddev.ai.runtime.connections import DirectAuthScheme, DirectConnection
from ddev.ai.runtime.tokens import DirectTokenProducer


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
