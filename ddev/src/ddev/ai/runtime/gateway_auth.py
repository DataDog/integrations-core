# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import time
from dataclasses import dataclass, field

from ddev.ai.errors import RunAbortError
from ddev.ai.model_catalog import Route
from ddev.ai.run_events import RunEvents
from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
from ddev.utils import dd_auth

# Allow for up to 8 hours of reuse on a 24-hour PAT, with an hour of margin.
TOKEN_USE_WINDOW = 15 * 60 * 60
LOGIN_HELP = "Run dd-auth -- /usr/bin/true in a terminal, then retry."
REPLACE_PAT_HELP = "Run dd-auth --no-cache -- /usr/bin/true in a terminal, then retry."
DD_AUTH_INSTALL_HELP = "Install dd-auth or run ddev config set ai.use_ai_gateway false."


class GatewayAuthError(RunAbortError):
    """A safe-to-display Gateway authentication failure."""


def gateway_refresh_error(cause: RefreshFailureCause) -> CredentialRefreshError:
    return CredentialRefreshError(
        Route.AI_GATEWAY,
        cause,
        "This run uses the AI Gateway. Its token expired or was rejected and could not be refreshed.",
        (
            "1. Run dd-auth -- true in a terminal to log in again. It opens a browser, or on a machine "
            "without one it prints a URL and curl instructions for the redirect.",
            "2. Open ddev meta ai, select the flow, then choose Resume. Completed phases are kept. "
            "The interrupted phase starts again from its first task and may redo work.",
        ),
    )


@dataclass(frozen=True)
class GatewayToken:
    """An in-memory PAT with a local use cutoff, not the issuer's expiry time."""

    value: str = field(repr=False)
    use_until: float


class GatewayTokenProducer:
    """Share one Gateway PAT across providers and refresh it on demand."""

    def __init__(self, events: RunEvents) -> None:
        self._events = events
        self._executable = dd_auth.find_dd_auth()
        self._token: GatewayToken | None = None
        self._rejected = False
        self._refresh_lock = asyncio.Lock()
        self._refresh_failure: RefreshFailureCause | None = None
        self._closed = False

    @property
    def available(self) -> bool:
        return self._executable is not None

    async def token_for(self, provider: str) -> str:
        async with self._refresh_lock:
            self._ensure_open()
            if self._refresh_failure is not None:
                raise gateway_refresh_error(self._refresh_failure)
            previous = self._token
            if previous is not None and not self._rejected and time.time() < previous.use_until:
                return previous.value
            if self._executable is None:
                raise GatewayAuthError(DD_AUTH_INSTALL_HELP)

            rejected_pat = previous.value if previous is not None and self._rejected else None
            started = time.time()
            try:
                replacement = await dd_auth.acquire_datadog_pat(self._executable, rejected_pat=rejected_pat)
            except dd_auth.DdAuthError as error:
                self._ensure_open()
                if previous is None:
                    help_text = DD_AUTH_INSTALL_HELP if isinstance(error, dd_auth.DdAuthLaunchError) else LOGIN_HELP
                    raise GatewayAuthError(f"{error} {help_text}") from None
                if isinstance(error, dd_auth.DdAuthTimeoutError):
                    self._refresh_failure = RefreshFailureCause.LOGIN_TIMED_OUT
                elif isinstance(error, dd_auth.DdAuthLoginError):
                    self._refresh_failure = RefreshFailureCause.LOGIN_FAILED
                else:
                    self._refresh_failure = RefreshFailureCause.ACQUISITION_FAILED
                raise gateway_refresh_error(self._refresh_failure) from None
            except asyncio.CancelledError as error:
                if previous is not None:
                    error.add_note(f"AI Gateway credential refresh cancelled. {LOGIN_HELP}")
                raise

            self._ensure_open()
            if previous is not None and replacement == previous.value:
                self._refresh_failure = RefreshFailureCause.CREDENTIAL_UNCHANGED
                raise gateway_refresh_error(self._refresh_failure)
            self._token = GatewayToken(replacement, started + TOKEN_USE_WINDOW)
            self._rejected = False
            return replacement

    def reject(self, token: str) -> None:
        if self._token is not None and self._token.value == token:
            self._rejected = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise GatewayAuthError(f"AI Gateway credential is not available. {LOGIN_HELP}")

    def clear(self) -> None:
        self._closed = True
        self._token = None
        self._refresh_failure = None
