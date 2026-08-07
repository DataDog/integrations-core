# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import math

import httpx

GITHUB_AUTHENTICATION_STATUS_CODES = frozenset((401, 403))
DEFAULT_SECONDARY_RATE_LIMIT_WAIT_SECONDS = 60


def github_authentication_error_message(status_code: int, *, action: str = 'requested operation') -> str:
    """Return actionable guidance for a GitHub authentication failure."""
    return (
        f'GitHub denied the {action} (HTTP {status_code}). The configured token may be invalid, expired, '
        'or missing required permissions. Run `ddev config set github.token` to configure a valid token.'
    )


def github_secondary_rate_limit_wait(response: httpx.Response) -> float | None:
    """Return the requested wait for a GitHub secondary-limit response."""
    if response.status_code not in (403, 429):
        return None

    retry_after = response.headers.get('retry-after')
    if retry_after is not None:
        try:
            wait = float(retry_after)
        except ValueError:
            return DEFAULT_SECONDARY_RATE_LIMIT_WAIT_SECONDS
        return wait if math.isfinite(wait) and wait > 0 else DEFAULT_SECONDARY_RATE_LIMIT_WAIT_SECONDS

    try:
        data = response.json()
    except ValueError:
        return None

    if isinstance(data, dict) and 'secondary rate limit' in str(data.get('message', '')).lower():
        return DEFAULT_SECONDARY_RATE_LIMIT_WAIT_SECONDS
    return None


class GitHubAuthenticationError(httpx.HTTPStatusError):
    """A GitHub HTTP failure caused by invalid authentication or insufficient permissions."""

    def __init__(self, message: str, *, request: httpx.Request, response: httpx.Response) -> None:
        super().__init__(message, request=request, response=response)

    @classmethod
    def from_http_status_error(cls, error: httpx.HTTPStatusError) -> GitHubAuthenticationError:
        """Build an authentication error while retaining the original HTTP context."""
        return cls(
            github_authentication_error_message(error.response.status_code),
            request=error.request,
            response=error.response,
        )
