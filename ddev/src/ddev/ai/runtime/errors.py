# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from enum import StrEnum

from ddev.ai.errors import RunAbortError
from ddev.ai.model_catalog import Route


class RefreshFailureCause(StrEnum):
    LOGIN_TIMED_OUT = "dd-auth timed out before login completed."
    LOGIN_FAILED = "dd-auth requires login or could not complete it."
    NO_BROWSER = "dd-auth could not open a browser on this machine."
    CALLBACK_PORTS_UNAVAILABLE = "The dd-auth callback ports are unavailable."
    LAUNCH_FAILED = "Could not launch dd-auth."
    PAT_MISSING = "dd-auth did not return DD_PAT."
    ACQUISITION_FAILED = "dd-auth did not return a usable credential."
    CREDENTIAL_UNCHANGED = "dd-auth returned the same unusable credential."
    REPLACEMENT_REJECTED = "The AI Gateway rejected the replacement credential (HTTP 401)."


class CredentialRefreshError(RunAbortError):
    """A usable credential could not be acquired at startup or replaced during refresh.

    The cause and recovery steps let callers show credential-specific guidance.
    """

    def __init__(
        self,
        route: Route,
        cause: RefreshFailureCause,
        summary: str,
        recovery_steps: tuple[str, ...],
        *,
        startup: bool = False,
        login_cancelled: bool = False,
    ) -> None:
        self.route = route
        self.cause = cause
        self.recovery_steps = recovery_steps
        self.startup = startup
        self.login_cancelled = login_cancelled
        super().__init__("\n\n".join((f"{summary} {cause}", *recovery_steps)))
