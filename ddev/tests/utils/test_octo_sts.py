# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest

from ddev.utils.octo_sts import (
    ACTIONS_ID_TOKEN_REQUEST_TOKEN_ENV,
    ACTIONS_ID_TOKEN_REQUEST_URL_ENV,
    MINT_ATTEMPTS,
    POLICY_ENV,
    SCOPE_ENV,
    OctoStsTokenProvider,
    octo_sts_token_provider_from_env,
)
from tests.helpers.clock import FakeClock, advance_clock_on_sleep


class Exchange:
    def __init__(self, calls: list[httpx.Request], responses: list[httpx.Response | Exception]) -> None:
        self.calls = calls
        self.responses = list(responses)

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        await asyncio.sleep(0)
        if request.url.host == "actions.example":
            return httpx.Response(200, json={"value": "oidc-value"})
        response = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(response, Exception):
            raise response
        return response


def make_provider(
    exchange: Callable[[httpx.Request], Awaitable[httpx.Response]],
    *,
    clock: FakeClock | None = None,
    logger: logging.Logger | None = None,
) -> OctoStsTokenProvider:
    return OctoStsTokenProvider(
        scope="DataDog/integrations-core",
        policy="self.test-dispatch",
        oidc_url="https://actions.example/oidc?api-version=1",
        oidc_token="oidc-bearer",
        logger=logger,
        clock=clock or FakeClock(),
        transport=httpx.MockTransport(exchange),
    )


async def test_first_use_mints_over_the_exchange_contract():
    calls: list[httpx.Request] = []
    provider = make_provider(Exchange(calls, [httpx.Response(200, json={"token": "minted-one"})]))

    assert await provider() == "minted-one"

    oidc, exchange = calls
    assert oidc.url.host == "actions.example"
    assert oidc.headers["Authorization"] == "Bearer oidc-bearer"
    assert dict(oidc.url.params) == {"api-version": "1", "audience": "dd-octo-sts"}
    assert exchange.url.host == "webhooks.build.datadoghq.com"
    assert exchange.url.path == "/sts/exchange"
    assert dict(exchange.url.params) == {"scope": "DataDog/integrations-core", "identity": "self.test-dispatch"}
    assert exchange.headers["Authorization"] == "Bearer oidc-value"
    assert exchange.headers["x-datadog-target-release"] == "dd-octo-sts.dd-octo-sts"


async def test_cached_token_is_refreshed_for_concurrent_callers():
    """A long run must share one refresh, including callers arriving while the exchange is in flight."""
    clock = FakeClock()
    calls: list[httpx.Request] = []
    exchange = Exchange(
        calls, [httpx.Response(200, json={"token": "minted-one"}), httpx.Response(200, json={"token": "minted-two"})]
    )
    provider = make_provider(exchange, clock=clock)

    assert await provider() == "minted-one"
    clock.advance(49 * 60)
    assert await provider() == "minted-one"
    assert len(calls) == 2

    clock.advance(12 * 60)
    tokens = await asyncio.gather(*(provider() for _ in range(5)))

    assert tokens == ["minted-two"] * 5
    assert len(calls) == 4


async def test_concurrent_failed_refresh_is_shared_and_later_call_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("ddev.utils.octo_sts.MINT_RETRY_BASE_SECONDS", 0)
    clock = FakeClock()
    calls: list[httpx.Request] = []
    exchange = Exchange(calls, [httpx.Response(200, json={"token": "minted-one"}), httpx.Response(503)])
    provider = make_provider(exchange, clock=clock)
    assert await provider() == "minted-one"
    clock.advance(61 * 60)
    calls.clear()

    results = await asyncio.gather(*(provider() for _ in range(5)), return_exceptions=True)

    assert all(
        isinstance(result, RuntimeError) and str(result) == "the octo-sts token exchange failed: HTTP 503"
        for result in results
    )
    assert sum(request.url.host == "webhooks.build.datadoghq.com" for request in calls) == MINT_ATTEMPTS

    exchange.responses = [httpx.Response(200, json={"token": "minted-two"})]
    assert await provider() == "minted-two"
    assert sum(request.url.host == "webhooks.build.datadoghq.com" for request in calls) == MINT_ATTEMPTS + 1


@pytest.mark.parametrize("cancelled_caller", [0, 1], ids=["initiator", "waiter"])
async def test_cancelling_token_caller_does_not_interrupt_shared_refresh(cancelled_caller: int):
    started = asyncio.Event()
    release = asyncio.Event()
    calls: list[httpx.Request] = []
    exchange = Exchange(calls, [httpx.Response(200, json={"token": "minted-one"})])

    async def blocked_exchange(request: httpx.Request) -> httpx.Response:
        if request.url.host == "webhooks.build.datadoghq.com":
            started.set()
            await release.wait()
        return await exchange(request)

    provider = make_provider(blocked_exchange)
    callers = [asyncio.create_task(provider()) for _ in range(2)]
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        callers[cancelled_caller].cancel()
        with pytest.raises(asyncio.CancelledError):
            await callers[cancelled_caller]
    finally:
        release.set()
        results = await asyncio.gather(*callers, return_exceptions=True)

    assert results[1 - cancelled_caller] == "minted-one"
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        pytest.param(httpx.Response(503, json={"message": "private-token"}), "HTTP 503", id="http_error"),
        pytest.param(httpx.ConnectError("private-token"), "ConnectError", id="transport_error"),
        pytest.param(httpx.Response(200, json={"message": "private-token"}), "returned no token", id="missing_token"),
    ],
)
async def test_failed_refresh_surfaces_a_sanitized_error(
    monkeypatch: pytest.MonkeyPatch, failure: httpx.Response | Exception, message: str
):
    """An exchange failure must not send an expired token or leak a response body through its error."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    calls: list[httpx.Request] = []
    provider = make_provider(Exchange(calls, [httpx.Response(200, json={"token": "minted-one"}), failure]), clock=clock)
    assert await provider() == "minted-one"
    clock.advance(61 * 60)

    with pytest.raises(RuntimeError, match=message) as caught:
        await provider()

    assert "private-token" not in str(caught.value)


async def test_transient_failure_is_retried(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    advance_clock_on_sleep(FakeClock(), monkeypatch)
    calls: list[httpx.Request] = []
    provider = make_provider(
        Exchange(calls, [httpx.Response(503, text="private-token"), httpx.Response(200, json={"token": "minted-one"})]),
        logger=logging.getLogger("octo-sts-test"),
    )

    with caplog.at_level(logging.INFO, logger="octo-sts-test"):
        assert await provider() == "minted-one"

    assert len(calls) == 3
    assert [record.getMessage() for record in caplog.records if record.name == "octo-sts-test"] == [
        "Refreshing octo-sts GitHub token",
        "octo-sts request failed; retrying after attempt 1/3: the octo-sts token exchange failed: HTTP 503",
    ]


@pytest.mark.parametrize(
    ("env", "expected"),
    [
        pytest.param({}, None, id="not_opted_in"),
        pytest.param(
            {
                ACTIONS_ID_TOKEN_REQUEST_URL_ENV: "https://actions.example/oidc",
                ACTIONS_ID_TOKEN_REQUEST_TOKEN_ENV: "oidc-bearer",
            },
            None,
            id="ambient_oidc_only",
        ),
        pytest.param(
            {
                SCOPE_ENV: "DataDog/integrations-core",
                POLICY_ENV: "self.test-dispatch",
                ACTIONS_ID_TOKEN_REQUEST_URL_ENV: "https://actions.example/oidc",
                ACTIONS_ID_TOKEN_REQUEST_TOKEN_ENV: "oidc-bearer",
            },
            OctoStsTokenProvider,
            id="opted_in",
        ),
        pytest.param({SCOPE_ENV: "DataDog/integrations-core"}, ValueError, id="half_opted_in"),
        pytest.param(
            {SCOPE_ENV: "DataDog/integrations-core", POLICY_ENV: "self.test-dispatch"},
            ValueError,
            id="opted_in_without_actions_oidc",
        ),
    ],
)
def test_provider_requires_explicit_opt_in(monkeypatch: pytest.MonkeyPatch, env: dict[str, str], expected: Any):
    for name in (SCOPE_ENV, POLICY_ENV, ACTIONS_ID_TOKEN_REQUEST_URL_ENV, ACTIONS_ID_TOKEN_REQUEST_TOKEN_ENV):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)

    if expected is ValueError:
        with pytest.raises(ValueError):
            octo_sts_token_provider_from_env()
    elif expected is None:
        assert octo_sts_token_provider_from_env() is None
    else:
        assert isinstance(octo_sts_token_provider_from_env(), expected)
