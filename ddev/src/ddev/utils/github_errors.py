# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import math
from typing import Self

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


class GitHubUnexpectedRedirectError(httpx.HTTPStatusError):
    """A GitHub endpoint answered with a redirect that is not part of its contract.

    The client never follows redirects, because the `Authorization` header would travel to whatever
    host `Location` names. One endpoint, the artifact download, does expect a redirect and asks for
    it; anywhere else a redirect means our assumption about the endpoint is wrong, so it is surfaced
    rather than followed or retried.
    """

    @classmethod
    def from_response(cls, method: str, endpoint: str, response: httpx.Response) -> Self:
        """Build the error for an unexpected redirect returned by *method* *endpoint*."""
        location = response.headers.get('location') or '<no Location header>'
        return cls(
            f'{method} {endpoint} returned an unexpected redirect (HTTP {response.status_code}) to '
            f'{location}. This endpoint is not expected to redirect, so the client did not follow it '
            f'and the GitHub token was not sent to the target.',
            request=response.request,
            response=response,
        )


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


# GitHub answers an over-long body with this status, and also every other validation failure and a
# body it judges to be spam. Which one it is shows only in the response body.
VALIDATION_FAILED_STATUS = 422

# Matched as a substring because there is no dedicated error code: this arrives as `custom` with the
# explanation in a free-text message, for example 'body is too long (maximum is 65536 characters)'.
# https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api
BODY_TOO_LONG_MESSAGE = 'too long'


def github_body_too_long_message(response: httpx.Response) -> str | None:
    """Return GitHub's explanation if *response* is it refusing a body for length, else `None`.

    Reading every 422 as 'too long' would answer a spam rejection by sending less, which cannot fix it
    and hides the real cause. An unreadable 422 counts as not too long for the same reason.
    """
    if response.status_code != VALIDATION_FAILED_STATUS:
        return None

    try:
        payload = response.json()
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None

    # The top-level message is the generic 'Validation Failed' and the specific one is per-error, but
    # only one of the two is documented to exist, so both are read.
    messages = [payload.get('message')]
    if isinstance(entries := payload.get('errors'), list):
        messages.extend(entry.get('message') for entry in entries if isinstance(entry, dict))

    return next(
        (message for message in messages if isinstance(message, str) and BODY_TOO_LONG_MESSAGE in message.lower()), None
    )


class GitHubBodyTooLongError(ValueError):
    """A body GitHub will not accept because it is too long.

    One type for both raise sites -- the client's pre-request measurement and GitHub's own 422 -- so a
    caller has one thing to catch and one action to take: send less. Not an `httpx.HTTPStatusError`,
    because the pre-request case has no response to carry; `github_message` is set only by the server.
    """

    def __init__(self, message: str, *, limit: int, size: int | None = None, github_message: str | None = None):
        super().__init__(message)
        self.limit = limit
        self.size = size
        self.github_message = github_message

    @classmethod
    def from_response(cls, github_message: str, *, limit: int) -> GitHubBodyTooLongError:
        """Build the error for a body GitHub itself refused."""
        return cls(f'GitHub refused the body: {github_message}', limit=limit, github_message=github_message)

    @classmethod
    def from_measurement(cls, size: int, *, limit: int) -> GitHubBodyTooLongError:
        """Build the error for a body the client refused before spending a request."""
        return cls(
            f'Body is {size} bytes, over the {limit} GitHub accepts; not sent.',
            limit=limit,
            size=size,
        )
