# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Awaitable, Callable

import httpx2

from ddev.ai.agent.exceptions import AgentAPIError, AgentConnectionError, AgentRateLimitError
from ddev.ai.runtime.gateway_auth import LOGIN_HELP, GatewayAuthError

GATEWAY_BASE_URL = "https://ai-gateway.datadoghq.com/ai/v1"
GATEWAY_URL = httpx2.URL(GATEWAY_BASE_URL)
TOGO_ML_APP_ID = "togo"
PROVIDER_HEADER = "x-ai-gateway-provider"
ATTRIBUTION_HEADER = "ml-app-id"
CREDENTIAL_HEADERS = ("authorization", "x-api-key", "x-goog-api-key", "dd-api-key", "dd-application-key")


class GatewayTransport(httpx2.AsyncBaseTransport):
    """Attach the PAT only to the public Gateway HTTPS origin and reject redirects."""

    def __init__(
        self,
        token: Callable[[], Awaitable[str]],
        transport: httpx2.AsyncBaseTransport,
        *,
        direct_auth_header: str = "authorization",
    ) -> None:
        self._token = token
        self._transport = transport
        self._direct_auth_header = direct_auth_header

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Send the request without exposing the PAT or error response body to the SDK."""
        url = request.url
        if (url.scheme, url.host, url.port) != (GATEWAY_URL.scheme, GATEWAY_URL.host, GATEWAY_URL.port):
            raise GatewayAuthError("Refusing to send an AI Gateway request outside its HTTPS origin.")

        # The model ID already selects the provider. Sending both selectors breaks routing.
        for header in (*CREDENTIAL_HEADERS, self._direct_auth_header, PROVIDER_HEADER, "cookie", "proxy-authorization"):
            request.headers.pop(header, None)
        request.headers[ATTRIBUTION_HEADER] = TOGO_ML_APP_ID
        request.headers["Authorization"] = f"Bearer {await self._token()}"
        try:
            response = await self._transport.handle_async_request(request)
        except httpx2.TransportError as error:
            raise AgentConnectionError(
                "AI Gateway connection failed.", timed_out=isinstance(error, httpx2.TimeoutException)
            ) from None
        finally:
            request.headers.pop("Authorization", None)

        status = response.status_code
        if 200 <= status < 300:
            return response
        # The SDK includes error bodies in exception messages and debug logs.
        await response.aclose()
        if status in (401, 403):
            raise GatewayAuthError(
                f"AI Gateway denied access (HTTP {status}). {LOGIN_HELP} Confirm the ai_gateway_usage permission."
            )
        if 300 <= status < 400:
            raise GatewayAuthError(f"AI Gateway returned a redirect (HTTP {status}); it was not followed.")
        if status == 429:
            raise AgentRateLimitError("AI Gateway rate limit exceeded (HTTP 429).")
        raise AgentAPIError(status, f"AI Gateway request failed (HTTP {status}).")
