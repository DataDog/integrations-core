# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from enum import StrEnum

from ddev.ai.errors import RunAbortError
from ddev.ai.model_catalog import Route


class RefreshFailureCause(StrEnum):
    LOGIN_TIMED_OUT = "dd-auth timed out before login completed."
    LOGIN_FAILED = "dd-auth requires login or could not complete it."
    ACQUISITION_FAILED = "dd-auth did not return a usable credential."
    CREDENTIAL_UNCHANGED = "dd-auth returned the same unusable credential."
    REPLACEMENT_REJECTED = "The AI Gateway rejected the replacement credential (HTTP 401)."


class CredentialRefreshError(RunAbortError):
    """No usable replacement was found for a credential past its use cutoff or rejected by the route.

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
    ) -> None:
        self.route = route
        self.cause = cause
        self.recovery_steps = recovery_steps
        self.startup = startup
        super().__init__("\n\n".join((f"{summary} {cause}", *recovery_steps)))
