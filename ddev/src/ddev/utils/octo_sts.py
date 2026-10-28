# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Refreshing GitHub Actions credentials through the dd-octo-sts exchange."""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import Callable
from time import monotonic, time
from typing import Any

import httpx

# https://github.com/DataDog/dd-octo-sts-action/blob/96a25462dbcb10ebf0bfd6e2ccc917d2ab235b9a/index.js
STS_EXCHANGE_URL = "https://webhooks.build.datadoghq.com/sts/exchange"
OCTO_STS_AUDIENCE = "dd-octo-sts"
STS_TARGET_RELEASE = "dd-octo-sts.dd-octo-sts"
MINT_ATTEMPTS = 5
MINT_RETRY_BASE_SECONDS = 10.0
MINT_RETRY_MAX_SECONDS = 60.0
MINT_TIMEOUT_SECONDS = 15.0
TOKEN_LIFETIME_SECONDS = 60 * 60.0
MINT_WORST_CASE_SECONDS = 2 * (
    MINT_ATTEMPTS * MINT_TIMEOUT_SECONDS
    + sum(min(MINT_RETRY_BASE_SECONDS * 2**attempt, MINT_RETRY_MAX_SECONDS) for attempt in range(MINT_ATTEMPTS - 1))
)
REFRESH_MARGIN_SECONDS = 120.0
# Reserve both endpoint retry budgets plus two minutes before the token's one-hour expiry.
TOKEN_REFRESH_AGE_SECONDS = TOKEN_LIFETIME_SECONDS - MINT_WORST_CASE_SECONDS - REFRESH_MARGIN_SECONDS

# Set only by the Dispatcher workflow. Ambient Actions OIDC alone never enables refresh.
SCOPE_ENV = "DD_DISPATCHER_OCTO_STS_SCOPE"
POLICY_ENV = "DD_DISPATCHER_OCTO_STS_POLICY"
MINTED_AT_ENV = "DD_DISPATCHER_OCTO_STS_MINTED_AT"
ACTIONS_ID_TOKEN_REQUEST_URL_ENV = "ACTIONS_ID_TOKEN_REQUEST_URL"
ACTIONS_ID_TOKEN_REQUEST_TOKEN_ENV = "ACTIONS_ID_TOKEN_REQUEST_TOKEN"


class OctoStsTokenProvider:
    """Supplies a current octo-sts GitHub token, minting a fresh one before the cached one expires.

    Tokens minted here are not revoked by the action's post step; they expire on their own.
    """

    def __init__(
        self,
        *,
        scope: str,
        policy: str,
        oidc_url: str,
        oidc_token: str,
        initial_token: str = "",
        initial_token_minted_at: float | None = None,
        logger: logging.Logger | None = None,
        clock: Callable[[], float] = monotonic,
        wall_clock: Callable[[], float] = time,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._exchange_url = httpx.URL(STS_EXCHANGE_URL, params={"scope": scope, "identity": policy})
        self._oidc_url = httpx.URL(oidc_url).copy_set_param("audience", OCTO_STS_AUDIENCE)
        self._oidc_token = oidc_token
        self._logger = logger
        self._clock = clock
        self._transport = transport
        self._refresh_task: asyncio.Task[str] | None = None
        self._token = initial_token
        self._refresh_at: float | None = None
        if initial_token and initial_token_minted_at is not None:
            remaining = initial_token_minted_at + TOKEN_REFRESH_AGE_SECONDS - wall_clock()
            if 0 < remaining <= TOKEN_REFRESH_AGE_SECONDS:
                self._refresh_at = self._clock() + remaining

    async def __call__(self) -> str:
        """Refresh before expiry; surface exchange failures rather than send a stale token."""
        if self._is_fresh():
            return self._token
        refresh = self._refresh_task
        if refresh is None or refresh.done():
            refresh = asyncio.create_task(self._refresh())
            self._refresh_task = refresh
            refresh.add_done_callback(self._refresh_finished)
        # Cancelling one caller must not interrupt the refresh for the others.
        return await asyncio.shield(refresh)

    async def _refresh(self) -> str:
        if self._logger is not None:
            self._logger.info("Refreshing octo-sts GitHub token")
        minted_at = self._clock()
        self._token = await self._mint()
        self._refresh_at = minted_at + TOKEN_REFRESH_AGE_SECONDS
        return self._token

    def _refresh_finished(self, task: asyncio.Task[str]) -> None:
        if self._refresh_task is task:
            self._refresh_task = None
        # Observe failures even if every caller was cancelled.
        if not task.cancelled():
            task.exception()

    def _is_fresh(self) -> bool:
        return self._refresh_at is not None and self._clock() < self._refresh_at

    async def _mint(self) -> str:
        async with httpx.AsyncClient(timeout=MINT_TIMEOUT_SECONDS, transport=self._transport) as http:
            oidc = await self._fetch_json(
                http, "the Actions OIDC token", self._oidc_url, {"Authorization": f"Bearer {self._oidc_token}"}
            )
            if not isinstance(oidc.get("value"), str) or not oidc["value"]:
                raise RuntimeError("the Actions OIDC token response carried no token value")
            exchange = await self._fetch_json(
                http,
                "the octo-sts token exchange",
                self._exchange_url,
                {
                    "Authorization": f"Bearer {oidc['value']}",
                    "x-datadog-target-release": STS_TARGET_RELEASE,
                },
            )
        token = exchange.get("token")
        if not isinstance(token, str) or not token:
            raise RuntimeError("the octo-sts token exchange returned no token")
        return token

    async def _fetch_json(
        self, http: httpx.AsyncClient, description: str, url: httpx.URL, headers: dict[str, str]
    ) -> dict[str, Any]:
        """GET `url` as JSON with bounded retries. Raised errors carry no body or credential."""
        error: Exception | None = None
        for attempt in range(1, MINT_ATTEMPTS + 1):
            try:
                async with asyncio.timeout(MINT_TIMEOUT_SECONDS):
                    response = await http.get(url, headers=headers)
            except (httpx.HTTPError, TimeoutError) as exc:
                # Class name only: the message can quote the URL.
                error = RuntimeError(f"{description} request failed: {type(exc).__name__}")
            else:
                if response.is_success:
                    try:
                        body = response.json()
                    except ValueError:
                        error = RuntimeError(f"{description} returned an unreadable body")
                    else:
                        if isinstance(body, dict):
                            return body
                        error = RuntimeError(f"{description} returned an unexpected body")
                else:
                    # The body can echo credentials back.
                    error = RuntimeError(f"{description} failed: HTTP {response.status_code}")
            if attempt < MINT_ATTEMPTS:
                if self._logger is not None:
                    self._logger.warning(
                        "octo-sts request failed; retrying after attempt %s/%s: %s", attempt, MINT_ATTEMPTS, error
                    )
                await asyncio.sleep(min(MINT_RETRY_BASE_SECONDS * 2 ** (attempt - 1), MINT_RETRY_MAX_SECONDS))
        assert error is not None
        raise error


def octo_sts_token_provider_from_env(
    *, initial_token: str = "", logger: logging.Logger | None = None
) -> OctoStsTokenProvider | None:
    """Build the provider when both opt-in variables are set, or None when neither is."""
    scope = os.environ.get(SCOPE_ENV, "")
    policy = os.environ.get(POLICY_ENV, "")
    if not scope and not policy:
        return None
    if not scope or not policy:
        raise ValueError(f"Token refresh needs both {SCOPE_ENV} and {POLICY_ENV} set, or neither.")
    oidc_url = os.environ.get(ACTIONS_ID_TOKEN_REQUEST_URL_ENV, "")
    oidc_token = os.environ.get(ACTIONS_ID_TOKEN_REQUEST_TOKEN_ENV, "")
    if not oidc_url or not oidc_token:
        raise ValueError(
            "Token refresh needs the Actions OIDC request URL and token, which the 'id-token: write' "
            "permission provides."
        )
    try:
        initial_token_minted_at = float(os.environ.get(MINTED_AT_ENV, ""))
    except ValueError:
        initial_token_minted_at = None
    return OctoStsTokenProvider(
        scope=scope,
        policy=policy,
        oidc_url=oidc_url,
        oidc_token=oidc_token,
        initial_token=initial_token,
        initial_token_minted_at=initial_token_minted_at,
        logger=logger,
    )
