# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""What the client reports about the requests it sends, for a caller that monitors them."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Protocol

import httpx

from ddev.utils.github_errors import github_secondary_rate_limit_wait


class RequestFault(StrEnum):
    """Why an attempt did not succeed, in a small fixed set of categories.

    `CANCELLED` is the caller's own cancellation of a request in flight, not a failure of GitHub's.
    """

    NONE = auto()
    CANCELLED = auto()
    AUTHENTICATION = auto()
    PERMISSION = auto()
    PRIMARY_RATE_LIMIT = auto()
    SECONDARY_RATE_LIMIT = auto()
    UNKNOWN_RATE_LIMIT = auto()
    TIMEOUT = auto()
    TRANSPORT = auto()
    CLIENT_ERROR = auto()
    SERVER_ERROR = auto()
    UNEXPECTED_RESPONSE = auto()


@dataclass(frozen=True)
class RequestAttempt:
    """One request actually sent to the GitHub API, once it has a response, a transport failure or
    was cancelled in flight.

    `endpoint` has its query masked. `number` counts the sends of one logical request across every
    retry layer, starting at 1. `response` is None for a transport failure or a cancellation.
    """

    method: str
    endpoint: str
    number: int
    duration_seconds: float
    response: httpx.Response | None
    error: Exception | None
    cancelled: bool = False

    @property
    def fault(self) -> RequestFault:
        if self.cancelled:
            return RequestFault.CANCELLED
        if self.error is None:
            return RequestFault.NONE
        if self.response is None:
            return RequestFault.TIMEOUT if isinstance(self.error, httpx.TimeoutException) else RequestFault.TRANSPORT
        status = self.response.status_code
        # The client's own rule for a retryable rate limit: a 403 alone is a permission denial.
        if status in (403, 429):
            if self.response.headers.get("x-ratelimit-remaining") == "0":
                return RequestFault.PRIMARY_RATE_LIMIT
            if github_secondary_rate_limit_wait(self.response) is not None:
                return RequestFault.SECONDARY_RATE_LIMIT
            if status == 429:
                return RequestFault.UNKNOWN_RATE_LIMIT
            return RequestFault.PERMISSION
        if status == 401:
            return RequestFault.AUTHENTICATION
        if status < 400:
            return RequestFault.UNEXPECTED_RESPONSE
        return RequestFault.CLIENT_ERROR if status < 500 else RequestFault.SERVER_ERROR


@dataclass(frozen=True)
class RequestFailure:
    """A logical request that failed for good, after whatever retries it was allowed.

    `last_attempt` is None when the request failed before anything was sent, for example when a
    rate-limit wait was abandoned.
    """

    method: str
    endpoint: str
    error: Exception
    last_attempt: RequestAttempt | None


class RequestObserver(Protocol):
    """Receives the client's observations. Exceptions it raises are ignored by the client."""

    def attempt_finished(self, attempt: RequestAttempt) -> None: ...

    def request_failed(self, failure: RequestFailure) -> None: ...
