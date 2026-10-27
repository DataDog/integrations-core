# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio

import httpx
import pytest
from aiolimiter import AsyncLimiter

from ddev.utils.github_async import async_github_client
from ddev.utils.rate_limiting import InstrumentedAsyncLimiter
from tests.helpers.clock import FakeClock, advance_clock_on_sleep
from tests.utils.github_async.helpers import TOKEN, RecordingObserver, governed_client, json_response
from tests.utils.github_async.payloads import workflow_run_payload


async def test_requests_and_views_use_provider_token():
    supplied = iter(["token-one", "token-two"])
    authorizations: list[str] = []

    async def token_provider() -> str:
        return next(supplied)

    def handler(request: httpx.Request) -> httpx.Response:
        authorizations.append(request.headers["Authorization"])
        return json_response(workflow_run_payload())

    async with async_github_client(
        token=TOKEN, transport=httpx.MockTransport(handler), token_provider=token_provider
    ) as client:
        await client.get_workflow_run("o", "r", 42)
        view = client.with_rate_limit(InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1)))
        await view.get_workflow_run("o", "r", 42)

    assert authorizations == ["Bearer token-one", "Bearer token-two"]


async def test_shutdown_bounds_hanging_token_provider(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("ddev.utils.github_async.client.SHUTDOWN_REQUEST_TIMEOUT", 0.01)
    observer = RecordingObserver()

    async def token_provider() -> str:
        await asyncio.Event().wait()
        return TOKEN

    async with async_github_client(
        token=TOKEN,
        transport=httpx.MockTransport(lambda _: httpx.Response(202)),
        token_provider=token_provider,
        observer=observer,
    ) as client:
        client.enter_shutdown_mode()
        async with asyncio.timeout(1):
            with pytest.raises(TimeoutError) as caught:
                await client.cancel_workflow_run("o", "r", 42, timeout=60)

    [failure] = observer.failures
    assert failure.error is caught.value
    assert failure.last_attempt is None


async def test_token_resolved_after_governor_wait(monkeypatch: pytest.MonkeyPatch):
    """A rate-limit pause must elapse before the token is resolved, or the pause ages the token."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    resolutions: list[float] = []

    async def token_provider() -> str:
        resolutions.append(clock())
        return "current-token"

    responses = [
        httpx.Response(403, headers={"retry-after": "5"}),
        json_response(workflow_run_payload()),
    ]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        response = responses[min(len(calls), len(responses) - 1)]
        calls.append(request)
        return response

    client = governed_client(clock, httpx.MockTransport(handler), token_provider=token_provider)
    start = clock.current

    try:
        await client.get_workflow_run("o", "r", 42)
    finally:
        await client.aclose()

    assert len(calls) == 2
    assert resolutions[0] == start
    assert resolutions[1] >= start + 5
