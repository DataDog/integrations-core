# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, Mock, call

import httpx2
import pytest

from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
from ddev.ai.runtime.gateway_auth import GatewayAuthError, GatewayTokenProducer
from ddev.ai.runtime.gateway_transport import GATEWAY_BASE_URL, GatewayTransport
from ddev.ai.runtime.tokens import TokenProducer
from ddev.utils import dd_auth


@pytest.mark.parametrize("url", ["http://ai-gateway.datadoghq.com/ai/v1/messages", "https://other.example/messages"])
async def test_gateway_transport_refuses_non_gateway_origin(url):
    tokens = Mock(spec=TokenProducer)
    handle = AsyncMock()
    transport = GatewayTransport(tokens, httpx2.MockTransport(handle), provider="test")
    async with httpx2.AsyncClient(transport=transport) as client:
        with pytest.raises(GatewayAuthError, match="outside its HTTPS origin"):
            await client.post(url)
    tokens.token_for.assert_not_awaited()
    handle.assert_not_awaited()


@pytest.mark.parametrize("location", ["https://other.example/messages", "/ai/v1/other"])
async def test_gateway_does_not_follow_redirects(location):
    handle = AsyncMock(return_value=httpx2.Response(307, headers={"Location": location}))
    tokens = Mock(spec=TokenProducer)
    tokens.token_for.return_value = "ddpat_gateway_secret"
    transport = GatewayTransport(tokens, httpx2.MockTransport(handle), provider="test")
    async with httpx2.AsyncClient(transport=transport, follow_redirects=True) as client:
        with pytest.raises(GatewayAuthError, match="redirect .*was not followed"):
            await client.post(f"{GATEWAY_BASE_URL}/messages")
    handle.assert_awaited_once()


async def test_gateway_reuses_replacement_when_an_old_request_is_rejected_late(monkeypatch):
    acquire_pat = AsyncMock(side_effect=["ddpat_old", "ddpat_new"])
    monkeypatch.setattr(dd_auth, "find_dd_auth", lambda: "/auth-bin/dd-auth")
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    tokens = GatewayTokenProducer()
    late_request_started = asyncio.Event()
    deliver_late_rejection = asyncio.Event()
    requests = []

    async def handle(request: httpx2.Request) -> httpx2.Response:
        token = request.headers["authorization"]
        requests.append((request.url.path, request.content, token))
        if token == "Bearer ddpat_old":
            if request.url.path.endswith("/messages"):
                late_request_started.set()
                await deliver_late_rejection.wait()
            return httpx2.Response(401)
        return httpx2.Response(200)

    network = httpx2.MockTransport(handle)
    async with (
        httpx2.AsyncClient(transport=GatewayTransport(tokens, network, provider="one")) as first,
        httpx2.AsyncClient(transport=GatewayTransport(tokens, network, provider="two")) as second,
        asyncio.timeout(2),
        asyncio.TaskGroup() as group,
    ):
        late = group.create_task(first.post(f"{GATEWAY_BASE_URL}/messages", content=b"generation"))
        await late_request_started.wait()
        auxiliary = await second.post(f"{GATEWAY_BASE_URL}/messages/count_tokens", content=b"count")
        deliver_late_rejection.set()

    assert late.result().status_code == auxiliary.status_code == 200
    assert requests == [
        ("/ai/v1/messages", b"generation", "Bearer ddpat_old"),
        ("/ai/v1/messages/count_tokens", b"count", "Bearer ddpat_old"),
        ("/ai/v1/messages/count_tokens", b"count", "Bearer ddpat_new"),
        ("/ai/v1/messages", b"generation", "Bearer ddpat_new"),
    ]
    assert acquire_pat.await_args_list == [
        call("/auth-bin/dd-auth", rejected_pat=None),
        call("/auth-bin/dd-auth", rejected_pat="ddpat_old"),
    ]


class RejectedBody(httpx2.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    def __aiter__(self) -> AsyncIterator[bytes]:
        raise AssertionError("A rejected Gateway response must not be read")

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("status", "stream_request", "sent", "rejected"),
    [
        (401, False, ["ddpat_old", "ddpat_new"], ["ddpat_old", "ddpat_new"]),
        (401, True, ["ddpat_old"], ["ddpat_old"]),
        (403, False, ["ddpat_old"], []),
    ],
    ids=["retry-once", "no-replay-of-streamed-upload", "permission-denial"],
)
async def test_gateway_bounds_recovery_to_replayable_requests_on_401(status, stream_request, sent, rejected):
    tokens = Mock(spec=TokenProducer)
    tokens.token_for.side_effect = ["ddpat_old", "ddpat_new"]
    bodies = []
    sent_tokens = []

    def handle(request: httpx2.Request) -> httpx2.Response:
        assert all(body.closed for body in bodies)
        sent_tokens.append(request.headers["authorization"].removeprefix("Bearer "))
        body = RejectedBody()
        bodies.append(body)
        return httpx2.Response(status, stream=body)

    async def stream() -> AsyncIterator[bytes]:
        yield b"upload"

    transport = GatewayTransport(tokens, httpx2.MockTransport(handle), provider="test")
    async with httpx2.AsyncClient(transport=transport) as client:
        error_type = CredentialRefreshError if status == 401 and not stream_request else GatewayAuthError
        with pytest.raises(error_type, match=rf"HTTP {status}") as caught:
            await client.post(f"{GATEWAY_BASE_URL}/messages", content=stream() if stream_request else b"upload")

    if isinstance(caught.value, CredentialRefreshError):
        assert caught.value.cause is RefreshFailureCause.REPLACEMENT_REJECTED
    assert all(body.closed for body in bodies)
    assert sent_tokens == sent
    assert [call.args[0] for call in tokens.reject.call_args_list] == rejected
