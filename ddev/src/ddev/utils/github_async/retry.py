# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Retry strategy for the async GitHub client.

Separate from rate-limit handling, which lives in ``ddev.utils.rate_limiting`` and reacts to GitHub
telling us to slow down: there the backoff *is* the limiter, so re-acquiring it is the whole retry.
This layer covers the failures that carry no such instruction, a dropped connection or a 502, where
the only useful response is to wait a little and ask again.

A ``RetryPolicy`` only describes what to do. stamina executes it, so no backoff arithmetic, sleeping
or attempt counting lives here.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx
import stamina

from ddev.utils.github_errors import GitHubAuthenticationError
from ddev.utils.rate_limiting import RateLimitWaitAbandoned

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

type RetryPredicate = Callable[[Exception], bool]

# Transport failures raised before any byte of the request reached GitHub, so replaying them cannot
# repeat a side effect. Read and write failures are deliberately absent: once the request is on the
# wire we cannot know whether the server acted on it.
PRE_SEND_TRANSPORT_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)

# Server-side failures an identical later request may well survive.
RETRYABLE_SERVER_STATUSES = frozenset((500, 502, 503, 504))

# Verbs whose requests can be replayed without changing anything server-side.
REPLAYABLE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def is_redirect_status(status_code: int) -> bool:
    """Whether *status_code* is a redirect, Location header or not."""
    return 300 <= status_code < 400


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def never(exc: Exception) -> bool:
    """Refuse everything. The condition of a policy that does not retry."""
    return False


def on_transport_error(exc: Exception) -> bool:
    """Any transport-level failure, whether or not the request reached GitHub."""
    return isinstance(exc, httpx.TransportError)


def on_pre_send_transport_error(exc: Exception) -> bool:
    """Only the transport failures that prove the request never left."""
    return isinstance(exc, PRE_SEND_TRANSPORT_ERRORS)


def on_status(*status_codes: int) -> RetryPredicate:
    """Responses whose status is one of *status_codes*."""
    wanted = frozenset(status_codes)

    def matches(exc: Exception) -> bool:
        return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in wanted

    return matches


def any_of(*predicates: RetryPredicate) -> RetryPredicate:
    """Accept what any of *predicates* accepts."""

    def matches(exc: Exception) -> bool:
        return any(predicate(exc) for predicate in predicates)

    return matches


on_server_error = on_status(*RETRYABLE_SERVER_STATUSES)


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetryPolicy:
    """How hard to try, and what to try again on, for one request.

    ``timeout`` bounds the whole ladder including backoff, not one request; ``None`` removes that
    bound and leaves ``attempts`` as the only stop condition.
    """

    should_retry: RetryPredicate = never
    attempts: int = 3
    timeout: float | None = 60.0
    wait_initial: float = 0.5
    wait_max: float = 10.0
    wait_jitter: float = 1.0

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError(f"attempts must be at least 1, got {self.attempts}")
        if self.timeout is not None and self.timeout <= 0:
            # stamina reads timeout=0 as "no retries", which is a confusing way to spell attempts=1.
            raise ValueError(f"timeout must be positive or None, got {self.timeout}")

    def replace(self, **overrides: Any) -> RetryPolicy:
        """A copy with *overrides* applied."""
        return dataclasses.replace(self, **overrides)

    def also_on(self, predicate: RetryPredicate) -> RetryPolicy:
        """A copy that retries what *predicate* accepts as well."""
        return dataclasses.replace(self, should_retry=any_of(self.should_retry, predicate))

    def unless(self, predicate: RetryPredicate) -> RetryPolicy:
        """A copy that refuses what *predicate* accepts, whatever this policy accepted before."""
        accepted = self.should_retry

        def narrowed(exc: Exception) -> bool:
            return accepted(exc) and not predicate(exc)

        return dataclasses.replace(self, should_retry=narrowed)


NO_RETRY = RetryPolicy(attempts=1)
SAFE_RETRY = RetryPolicy(should_retry=any_of(on_transport_error, on_server_error))
MUTATION_RETRY = RetryPolicy(should_retry=on_pre_send_transport_error, attempts=2)


@dataclass(frozen=True)
class RetryPolicies:
    """The client's defaults, one per replay-safety class.

    A verb is the proxy the client uses to pick between them, but idempotence is the real question,
    so an endpoint that is idempotent despite mutating (setting a comment body, closing a check run)
    asks for ``safe`` explicitly.
    """

    safe: RetryPolicy = SAFE_RETRY
    mutating: RetryPolicy = MUTATION_RETRY

    def for_method(self, method: str) -> RetryPolicy:
        """The default for *method*, by whether the verb is replayable."""
        return self.safe if method.upper() in REPLAYABLE_HTTP_METHODS else self.mutating


DEFAULT_RETRY_POLICIES = RetryPolicies()


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def refuses_retry(is_rate_limit_response: Callable[[httpx.Response], bool]) -> RetryPredicate:
    """Build the exclusions the client applies whatever policy a caller supplies.

    Retrying any of these is useless or harmful, so no policy may opt in:

    - authentication failures, which no amount of waiting fixes;
    - rate-limit responses, owned by the limiter, whose pause is the correct backoff;
    - ``RateLimitWaitAbandoned``, the caller's killswitch for that pause;
    - redirects, which are an answer rather than a failure.
    """

    def refuses(exc: Exception) -> bool:
        if isinstance(exc, (GitHubAuthenticationError, RateLimitWaitAbandoned)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return is_rate_limit_response(exc.response) or is_redirect_status(exc.response.status_code)
        return False

    return refuses


class RetryTracker:
    """Decides retries for one operation and keeps the failure that caused the most recent one.

    stamina asks whether to retry where the exception is known, and the caller logs where the attempt
    number is known. This carries the exception between the two.
    """

    def __init__(self, policy: RetryPolicy, refuses: RetryPredicate) -> None:
        self._policy = policy
        self._refuses = refuses
        self.last_error: Exception | None = None

    def __call__(self, exc: Exception) -> bool:
        if self._refuses(exc) or not self._policy.should_retry(exc):
            return False
        self.last_error = exc
        return True


def retry_attempts(policy: RetryPolicy, should_retry: RetryPredicate) -> AsyncIterator[stamina.Attempt]:
    """Yield one stamina attempt per try of *policy*, retrying what *should_retry* accepts.

    The caller runs its work inside ``with attempt:``; that context manager is what swallows a
    retryable exception, waits the backoff and lets the loop turn again.
    """
    return stamina.retry_context(
        on=should_retry,
        attempts=policy.attempts,
        timeout=policy.timeout,
        wait_initial=policy.wait_initial,
        wait_max=policy.wait_max,
        wait_jitter=policy.wait_jitter,
    )
