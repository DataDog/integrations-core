# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from dataclasses import dataclass, field

from ddev.ai.agent.exceptions import AgentError
from ddev.utils import dd_auth

# Allow for up to 8 hours of reuse on a 24-hour PAT, with an hour of margin.
TOKEN_USE_WINDOW = 15 * 60 * 60
LOGIN_HELP = "Run `dd-auth -- /usr/bin/true` in a terminal, then retry."
DD_AUTH_INSTALL_HELP = "Install `dd-auth` or run `ddev config set ai.use_ai_gateway false`."


class GatewayAuthError(AgentError):
    """A safe-to-display Gateway authentication failure."""


@dataclass(frozen=True)
class GatewayToken:
    """An in-memory PAT with a local use cutoff, not the issuer's expiry time."""

    value: str = field(repr=False)
    use_until: float

    def usable_value(self) -> str:
        """Return the PAT before the cutoff; require a run restart afterward."""
        if time.time() >= self.use_until:
            raise GatewayAuthError(f"AI Gateway credential reached Togo's usage cutoff. Restart the run. {LOGIN_HELP}")
        return self.value


class GatewayTokenProducer:
    """Acquire one Gateway PAT with `dd-auth` before a run's first model probe."""

    def __init__(self) -> None:
        self._executable = dd_auth.find_dd_auth()
        self._token: GatewayToken | None = None
        self._closed = False

    @property
    def available(self) -> bool:
        return self._executable is not None

    async def token_for(self, provider: str) -> str:
        """Return the same PAT for every provider without refreshing it after the cutoff."""
        if self._closed:
            raise GatewayAuthError(f"AI Gateway credential is not available. {LOGIN_HELP}")
        if self._token is None:
            self._token = await self._acquire()
        return self._token.usable_value()

    async def _acquire(self) -> GatewayToken:
        if self._executable is None:
            raise GatewayAuthError(DD_AUTH_INSTALL_HELP)
        started = time.time()
        try:
            token = await dd_auth.acquire_datadog_pat(self._executable)
        except dd_auth.DdAuthLaunchError as error:
            raise GatewayAuthError(f"{error} {DD_AUTH_INSTALL_HELP}") from None
        except dd_auth.DdAuthError as error:
            raise GatewayAuthError(f"{error} {LOGIN_HELP}") from None
        return GatewayToken(token, started + TOKEN_USE_WINDOW)

    def clear(self) -> None:
        self._closed = True
        self._token = None
