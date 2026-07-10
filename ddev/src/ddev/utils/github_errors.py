# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import httpx

GITHUB_AUTHENTICATION_STATUS_CODES = frozenset((401, 403))


def github_authentication_error_message(status_code: int, *, action: str = 'requested operation') -> str:
    """Return actionable guidance for a GitHub authentication failure."""
    return (
        f'GitHub denied the {action} (HTTP {status_code}). The configured token may be invalid, expired, '
        'or missing required permissions. Run `ddev config set github.token` to configure a valid token.'
    )


class GitHubAuthenticationError(Exception):
    """A GitHub HTTP failure caused by invalid authentication or insufficient permissions."""

    def __init__(self, message: str, *, request: httpx.Request, response: httpx.Response) -> None:
        super().__init__(message)
        self.request = request
        self.response = response

    @classmethod
    def from_http_status_error(cls, error: httpx.HTTPStatusError) -> GitHubAuthenticationError:
        """Build an authentication error while retaining the original HTTP context."""
        return cls(
            github_authentication_error_message(error.response.status_code),
            request=error.request,
            response=error.response,
        )
