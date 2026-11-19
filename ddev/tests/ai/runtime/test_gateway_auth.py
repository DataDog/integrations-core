# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from ddev.ai.runtime import gateway_auth
from ddev.utils import dd_auth


@pytest.fixture
def find_dd_auth(monkeypatch) -> Mock:
    find = Mock(return_value="/auth-bin/dd-auth")
    monkeypatch.setattr(dd_auth, "find_dd_auth", find)
    return find


async def test_gateway_producer_enforces_cutoff_from_start_of_acquisition(monkeypatch, find_dd_auth):
    clock = SimpleNamespace(now=100.0)
    monkeypatch.setattr(gateway_auth, "time", SimpleNamespace(time=lambda: clock.now))

    async def acquire(executable: str) -> str:
        clock.now += 10.0
        return "ddpat_developer"

    acquire_pat = AsyncMock(side_effect=acquire)
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    producer = gateway_auth.GatewayTokenProducer()

    assert await producer.token_for("provider-a") == "ddpat_developer"
    clock.now = 100.0 + gateway_auth.TOKEN_USE_WINDOW
    with pytest.raises(gateway_auth.GatewayAuthError, match="usage cutoff"):
        await producer.token_for("provider-a")
    acquire_pat.assert_awaited_once()


async def test_gateway_producer_shares_one_token_and_drops_it_on_clear(monkeypatch, find_dd_auth):
    acquire_pat = AsyncMock(return_value="ddpat_developer")
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", acquire_pat)
    producer = gateway_auth.GatewayTokenProducer()

    assert producer.available
    assert await producer.token_for("provider-a") == "ddpat_developer"
    assert await producer.token_for("provider-b") == "ddpat_developer"

    producer.clear()
    with pytest.raises(gateway_auth.GatewayAuthError, match="AI Gateway credential is not available"):
        await producer.token_for("provider-a")
    find_dd_auth.assert_called_once_with()
    acquire_pat.assert_awaited_once_with("/auth-bin/dd-auth")


@pytest.mark.parametrize(
    ("error", "guidance"),
    [
        (dd_auth.DdAuthLaunchError("Could not launch dd-auth."), "Install `dd-auth`"),
        (dd_auth.DdAuthError("dd-auth failed."), "Run `dd-auth -- /usr/bin/true`"),
    ],
)
async def test_gateway_auth_adds_recovery_guidance(monkeypatch, find_dd_auth, error, guidance):
    monkeypatch.setattr(dd_auth, "acquire_datadog_pat", AsyncMock(side_effect=error))

    with pytest.raises(gateway_auth.GatewayAuthError) as caught:
        await gateway_auth.GatewayTokenProducer().token_for("provider-a")

    assert str(error) in str(caught.value)
    assert guidance in str(caught.value)
