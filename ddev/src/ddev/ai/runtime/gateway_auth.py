# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import asyncio
import time
from dataclasses import dataclass, field

from ddev.ai.errors import RunAbortError
from ddev.ai.model_catalog import Route
from ddev.ai.runtime.errors import CredentialRefreshError, RefreshFailureCause
from ddev.ai.runtime.login_prompt import LoginAction, LoginProblem, LoginPrompt
from ddev.utils import dd_auth

# Allow for up to 8 hours of reuse on a 24-hour PAT, with an hour of margin.
TOKEN_USE_WINDOW = 15 * 60 * 60
LOGIN_HELP = "Run dd-auth -- /usr/bin/true in a terminal, then retry."
REPLACE_PAT_HELP = "Run dd-auth --no-cache -- /usr/bin/true in a terminal, then retry."
DD_AUTH_INSTALL_HELP = "Install dd-auth or run ddev config set ai.use_ai_gateway false."
STARTUP_RETRY_HELP = "Retry the same command or, in Togo, choose the same action as before (Launch or Resume)."
RESUME_RUN_HELP = (
    "Open ddev meta ai, select the flow, then choose Resume. Completed phases are kept. "
    "The interrupted phase starts again from its first task and may redo work."
)
LOGIN_INTERRUPTED_MESSAGE = "The run was waiting for the dd-auth login."
LOGIN_INTERRUPTED_NOTE = f"{LOGIN_INTERRUPTED_MESSAGE} {RESUME_RUN_HELP}"
LOGIN_PROBLEMS = {
    RefreshFailureCause.LOGIN_TIMED_OUT: LoginProblem(
        "dd-auth login timed out",
        "The dd-auth login was not completed in time. Retrying runs dd-auth again and may open a browser.",
    ),
    RefreshFailureCause.CALLBACK_PORTS_UNAVAILABLE: LoginProblem(
        "dd-auth callback ports are unavailable",
        "Another dd-auth login may be in progress. Finish or close it before retrying.",
    ),
}


class GatewayAuthError(RunAbortError):
    """A safe-to-display Gateway authentication failure."""


def gateway_refresh_error(
    cause: RefreshFailureCause,
    *,
    startup: bool = False,
    login_cancelled: bool = False,
    rejected: bool = False,
) -> CredentialRefreshError:
    if cause is RefreshFailureCause.NO_BROWSER:
        login_help = _no_browser_instructions(rejected)
    elif cause is RefreshFailureCause.LAUNCH_FAILED:
        login_help = DD_AUTH_INSTALL_HELP
    elif cause is RefreshFailureCause.PAT_MISSING:
        login_help = dd_auth.UPGRADE_HELP
    else:
        login_help = (
            f"Run {_manual_login_command(rejected)} in a terminal to log in again. It opens a browser, or on a machine "
            "without one it prints a URL and curl instructions for the redirect."
        )
    return CredentialRefreshError(
        Route.AI_GATEWAY,
        cause,
        "The run could not start on the AI Gateway without a usable credential."
        if startup
        else "This run uses the AI Gateway. Its token expired or was rejected and could not be refreshed.",
        (f"1. {login_help}", f"2. {STARTUP_RETRY_HELP if startup else RESUME_RUN_HELP}"),
        startup=startup,
        login_cancelled=login_cancelled,
    )


@dataclass(frozen=True)
class GatewayToken:
    """An in-memory PAT with a local use cutoff, not the issuer's expiry time."""

    value: str = field(repr=False)
    use_until: float


class GatewayTokenProducer:
    """Share one Gateway PAT across providers and refresh it on demand."""

    def __init__(self, login_prompt: LoginPrompt | None = None) -> None:
        self._executable = dd_auth.find_dd_auth()
        self._login_prompt = login_prompt
        self._token: GatewayToken | None = None
        self._rejected = False
        self._refresh_lock = asyncio.Lock()
        self._refresh_failure: RefreshFailureCause | None = None
        self._login_cancelled = False
        self.login_interrupted = False
        self._closed = False

    @property
    def available(self) -> bool:
        return self._executable is not None

    async def token_for(self, provider: str, *, startup: bool = False) -> str:
        async with self._refresh_lock:
            self._ensure_open()
            if self._refresh_failure is not None:
                raise gateway_refresh_error(
                    self._refresh_failure,
                    startup=startup,
                    login_cancelled=self._login_cancelled,
                    rejected=self._rejected,
                )
            previous = self._token
            if previous is not None and not self._rejected and time.time() < previous.use_until:
                return previous.value
            if self._executable is None:
                raise GatewayAuthError(DD_AUTH_INSTALL_HELP)

            rejected_pat = previous.value if previous is not None and self._rejected else None
            try:
                replacement, started = await self._acquire(self._executable, rejected_pat, startup=startup)
            except asyncio.CancelledError as error:
                self.login_interrupted = True
                note = f"{LOGIN_INTERRUPTED_MESSAGE} {STARTUP_RETRY_HELP}" if startup else LOGIN_INTERRUPTED_NOTE
                error.add_note(note)
                raise

            self._ensure_open()
            if previous is not None and replacement == previous.value:
                self._refresh_failure = RefreshFailureCause.CREDENTIAL_UNCHANGED
                raise gateway_refresh_error(self._refresh_failure, startup=startup)
            self._token = GatewayToken(replacement, started + TOKEN_USE_WINDOW)
            self._rejected = False
            return replacement

    async def _acquire(self, executable: str, rejected_pat: str | None, *, startup: bool) -> tuple[str, float]:
        prompt = self._login_prompt
        while True:
            self._ensure_open()
            started = time.time()
            try:
                if prompt is None:
                    token = await dd_auth.acquire_datadog_pat(executable, rejected_pat=rejected_pat)
                else:
                    token = await self._acquire_with_progress(executable, rejected_pat, prompt)
                return token, started
            except dd_auth.DdAuthError as error:
                self._ensure_open()
                cause = _login_failure(error)
                rejected = rejected_pat is not None
                problem = (
                    LoginProblem("dd-auth could not open a browser", f"{cause} {_no_browser_instructions(rejected)}")
                    if cause is RefreshFailureCause.NO_BROWSER
                    else LOGIN_PROBLEMS.get(cause)
                )
                prompted = prompt is not None and problem is not None
                if prompt is not None and problem is not None:
                    if await prompt.resolve(problem) is LoginAction.RETRY:
                        continue
                self._refresh_failure = cause
                self._login_cancelled = prompted
                raise gateway_refresh_error(
                    cause, startup=startup, login_cancelled=prompted, rejected=rejected
                ) from None

    @staticmethod
    async def _acquire_with_progress(executable: str, rejected_pat: str | None, prompt: LoginPrompt) -> str:
        pending = False

        def login_pending(_: dd_auth.DdAuthLoginPending) -> None:
            nonlocal pending
            if not pending:
                pending = True
                prompt.set_pending(True)

        try:
            return await dd_auth.acquire_datadog_pat(executable, rejected_pat=rejected_pat, on_progress=login_pending)
        finally:
            if pending:
                prompt.set_pending(False)

    def token_for_probe(self) -> str:
        """Return the pre-acquired credential without starting login inside the probe deadline."""
        self._ensure_open()
        if self._token is None or self._rejected:
            raise GatewayAuthError("AI Gateway startup probe requires a pre-acquired credential.")
        return self._token.value

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


def _manual_login_command(rejected: bool) -> str:
    return "dd-auth --no-cache -- true" if rejected else "dd-auth -- true"


def _no_browser_instructions(rejected: bool) -> str:
    command = _manual_login_command(rejected)
    return (
        f"Run {command} in a terminal on this machine and follow its instructions: open the URL it prints in any "
        "browser, then run the curl command it describes with the localhost address that failed to load."
    )


def _login_failure(error: dd_auth.DdAuthError) -> RefreshFailureCause:
    if isinstance(error, dd_auth.DdAuthLaunchError):
        return RefreshFailureCause.LAUNCH_FAILED
    if isinstance(error, dd_auth.DdAuthTimeoutError):
        return RefreshFailureCause.LOGIN_TIMED_OUT
    if isinstance(error, dd_auth.DdAuthNoBrowserError):
        return RefreshFailureCause.NO_BROWSER
    if isinstance(error, dd_auth.DdAuthCallbackPortsError):
        return RefreshFailureCause.CALLBACK_PORTS_UNAVAILABLE
    if isinstance(error, dd_auth.DdAuthMissingPatError):
        return RefreshFailureCause.PAT_MISSING
    if isinstance(error, dd_auth.DdAuthLoginError):
        return RefreshFailureCause.LOGIN_FAILED
    return RefreshFailureCause.ACQUISITION_FAILED
