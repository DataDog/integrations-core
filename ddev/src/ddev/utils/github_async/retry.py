# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Retry strategy for requests that failed for a reason other than rate limiting.

Rate limiting is handled elsewhere (`ddev.utils.rate_limiting`), where re-acquiring the limiter is
itself the backoff. This module covers the rest: a policy says what to retry and how hard to try,
and stamina executes it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

import httpx
import stamina

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

type RetryPredicate = Callable[[Exception], bool]

# Transport failures raised before any byte of the request reached the server, so a replay cannot
# repeat a side effect. Read and write failures are absent on purpose.
PRE_SEND_TRANSPORT_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)

RETRYABLE_SERVER_STATUSES = frozenset((500, 502, 503, 504))

REPLAYABLE_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

DEFAULT_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_WAIT_INITIAL_SECONDS = 0.5
DEFAULT_WAIT_MAX_SECONDS = 10.0
DEFAULT_WAIT_JITTER_SECONDS = 1.0

# A mutation retries only what provably never left, which a second attempt either fixes at once or
# is unlikely to fix at all.
MUTATION_ATTEMPTS = 2


class Unset(Enum):
    """Sentinel for `RetryPolicy.replace`, where `timeout=None` means no timeout, not unchanged."""

    TOKEN = auto()


UNSET = Unset.TOKEN


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def never(exc: Exception) -> bool:
    """Refuse everything."""
    return False


def on_transport_error(exc: Exception) -> bool:
    """Any transport failure, whether or not the request reached the server."""
    return isinstance(exc, httpx.TransportError)


def on_pre_send_transport_error(exc: Exception) -> bool:
    """Only the transport failures that prove the request never left."""
    return isinstance(exc, PRE_SEND_TRANSPORT_ERRORS)


def on_status(*status_codes: int) -> RetryPredicate:
    """Responses whose status is one of `status_codes`."""
    wanted = frozenset(status_codes)

    def matches(exc: Exception) -> bool:
        return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in wanted

    return matches


def any_of(*predicates: RetryPredicate) -> RetryPredicate:
    """Accept what any of `predicates` accepts."""

    def matches(exc: Exception) -> bool:
        return any(predicate(exc) for predicate in predicates)

    return matches


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """What to retry, and how hard to try.

    Frozen because the defaults below are shared for the life of the process: tuning one in place would
    change the behaviour of every client that took it. `replace`, `also_on` and `unless` return new
    policies instead.

    `timeout` bounds the whole ladder including backoff; None leaves `attempts` as the only stop.
    """

    should_retry: RetryPredicate = never
    attempts: int = DEFAULT_ATTEMPTS
    timeout: float | None = DEFAULT_TIMEOUT_SECONDS
    wait_initial: float = DEFAULT_WAIT_INITIAL_SECONDS
    wait_max: float = DEFAULT_WAIT_MAX_SECONDS
    wait_jitter: float = DEFAULT_WAIT_JITTER_SECONDS

    def __post_init__(self) -> None:
        if self.attempts < 1:
            raise ValueError(f"attempts must be at least 1, got {self.attempts}")
        if self.timeout is not None and self.timeout <= 0:
            # stamina reads timeout=0 as "no retries", a confusing way to spell attempts=1.
            raise ValueError(f"timeout must be positive or None, got {self.timeout}")

    def replace(
        self,
        *,
        should_retry: RetryPredicate | None = None,
        attempts: int | None = None,
        timeout: float | None | Unset = UNSET,
        wait_initial: float | None = None,
        wait_max: float | None = None,
        wait_jitter: float | None = None,
    ) -> RetryPolicy:
        """A copy with the given fields changed."""
        return RetryPolicy(
            should_retry=self.should_retry if should_retry is None else should_retry,
            attempts=self.attempts if attempts is None else attempts,
            timeout=self.timeout if isinstance(timeout, Unset) else timeout,
            wait_initial=self.wait_initial if wait_initial is None else wait_initial,
            wait_max=self.wait_max if wait_max is None else wait_max,
            wait_jitter=self.wait_jitter if wait_jitter is None else wait_jitter,
        )

    def also_on(self, predicate: RetryPredicate) -> RetryPolicy:
        """A copy that retries what `predicate` accepts as well."""
        return self.replace(should_retry=any_of(self.should_retry, predicate))

    def unless(self, predicate: RetryPredicate) -> RetryPolicy:
        """A copy that refuses what `predicate` accepts."""
        accepted = self.should_retry

        def narrowed(exc: Exception) -> bool:
            return accepted(exc) and not predicate(exc)

        return self.replace(should_retry=narrowed)


# Policy constants. They follow the class because they are instances of it.
NO_RETRY = RetryPolicy(attempts=1)
SAFE_RETRY = RetryPolicy(should_retry=any_of(on_transport_error, on_status(*RETRYABLE_SERVER_STATUSES)))
MUTATION_RETRY = RetryPolicy(should_retry=on_pre_send_transport_error, attempts=MUTATION_ATTEMPTS)


@dataclass(frozen=True, slots=True)
class RetryPolicies:
    """The defaults a client picks from, one per replay-safety class.

    The verb is only a proxy: idempotence is the real question, so an endpoint that mutates but is
    idempotent asks for `safe` explicitly.
    """

    safe: RetryPolicy = SAFE_RETRY
    mutating: RetryPolicy = MUTATION_RETRY

    def for_method(self, method: str) -> RetryPolicy:
        """The default for `method`, by whether the verb is replayable."""
        return self.safe if method.upper() in REPLAYABLE_HTTP_METHODS else self.mutating


DEFAULT_RETRY_POLICIES = RetryPolicies()


def retry_attempts(policy: RetryPolicy, should_retry: RetryPredicate) -> AsyncIterator[stamina.Attempt]:
    """Yield one attempt per try of `policy`, retrying what `should_retry` accepts.

    The caller runs its work inside `with attempt:`, which is what swallows a retryable exception,
    waits the backoff and lets the loop turn again.
    """
    return stamina.retry_context(
        on=should_retry,
        attempts=policy.attempts,
        timeout=policy.timeout,
        wait_initial=policy.wait_initial,
        wait_max=policy.wait_max,
        wait_jitter=policy.wait_jitter,
    )
