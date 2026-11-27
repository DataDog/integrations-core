# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from ddev.ai.model_catalog import Route
from ddev.ai.run_events import RunEvents
from ddev.ai.runtime import gateway_auth
from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
from ddev.utils import dd_auth


@pytest.fixture
def find_dd_auth(monkeypatch) -> Mock:
    find = Mock(return_value="/auth-bin/dd-auth")
    monkeypatch.setattr(dd_auth, "find_dd_auth", find)
    return find


async def test_gateway_producer_shares_refresh_at_use_cutoff(monkeypatch, find_dd_auth):
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(gateway_auth, "time", SimpleNamespace(time=lambda: clock.now))
    refresh_started = asyncio.Event()
    second_request = asyncio.Event()
    finish_refresh = asyncio.Event()

    async def refresh(_: str, *, rejected_pat: str | None) -> str:
        refresh_started.set()
        await finish_refresh.wait()
        return "ddpat_new"

    acquire_pat = AsyncMock(return_value="ddpat_old")
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    producer = gateway_auth.GatewayTokenProducer(RunEvents())

    assert await producer.token_for("provider-a") == "ddpat_old"
    clock.now = 100.0 + gateway_auth.TOKEN_USE_WINDOW - 1
    assert await producer.token_for("provider-b") == "ddpat_old"
    acquire_pat.assert_awaited_once()

    clock.now += 1
    acquire_pat.side_effect = refresh

    async def request_from_second_provider() -> str:
        second_request.set()
        return await producer.token_for("provider-b")

    async with asyncio.timeout(2), asyncio.TaskGroup() as group:
        first = group.create_task(producer.token_for("provider-a"))
        await refresh_started.wait()
        second = group.create_task(request_from_second_provider())
        await second_request.wait()
        finish_refresh.set()

    assert first.result() == second.result() == "ddpat_new"
    assert acquire_pat.await_count == 2


async def test_gateway_producer_shares_one_token_and_drops_it_on_clear(monkeypatch, find_dd_auth):
    acquire_pat = AsyncMock(return_value="ddpat_developer")
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    producer = gateway_auth.GatewayTokenProducer(RunEvents())

    assert producer.available
    assert await producer.token_for("provider-a") == "ddpat_developer"
    assert await producer.token_for("provider-b") == "ddpat_developer"

    producer.clear()
    with pytest.raises(gateway_auth.GatewayAuthError, match="AI Gateway credential is not available"):
        await producer.token_for("provider-a")
    find_dd_auth.assert_called_once_with()
    acquire_pat.assert_awaited_once_with("/auth-bin/dd-auth", rejected_pat=None)


@pytest.mark.parametrize(
    ("error", "guidance"),
    [
        (dd_auth.DdAuthLaunchError("Could not launch dd-auth."), "Install dd-auth"),
        (dd_auth.DdAuthError("dd-auth failed."), "Run dd-auth -- /usr/bin/true"),
    ],
)
async def test_gateway_auth_adds_recovery_guidance(monkeypatch, find_dd_auth, error, guidance):
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", AsyncMock(side_effect=error))

    with pytest.raises(gateway_auth.GatewayAuthError) as caught:
        await gateway_auth.GatewayTokenProducer(RunEvents()).token_for("provider-a")

    assert str(error) in str(caught.value)
    assert guidance in str(caught.value)


@pytest.mark.parametrize(
    ("error_type", "cause"),
    [
        (dd_auth.DdAuthLoginError, RefreshFailureCause.LOGIN_FAILED),
        (dd_auth.DdAuthTimeoutError, RefreshFailureCause.LOGIN_TIMED_OUT),
        (dd_auth.DdAuthError, RefreshFailureCause.ACQUISITION_FAILED),
    ],
)
async def test_gateway_refresh_failure_is_actionable_and_not_retried(monkeypatch, find_dd_auth, error_type, cause):
    acquire_pat = AsyncMock(side_effect=["ddpat_old", error_type("private login detail")])
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    producer = gateway_auth.GatewayTokenProducer(RunEvents())

    producer.reject(await producer.token_for("provider-a"))
    for provider in ("provider-a", "provider-b"):
        with pytest.raises(CredentialRefreshError) as caught:
            await producer.token_for(provider)
        assert caught.value.route is Route.AI_GATEWAY
        assert caught.value.cause is cause
        assert "private login detail" not in str(caught.value)
    assert acquire_pat.await_count == 2
