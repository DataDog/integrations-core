# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Dispatcher metrics and logs for the GitHub requests it sends and the waits its limiters impose."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from contextlib import suppress
from typing import Any

import httpx

from ddev.cli.ci.tests.dispatcher_attributes import github_metrics
from ddev.monitoring import ComponentMonitor
from ddev.utils.github_async.client import failure_reason, parse_header, with_query_masked
from ddev.utils.github_async.observer import RequestAttempt, RequestFailure, RequestFault
from ddev.utils.rate_limiting import RateLimitEvent, WaitEvent

# GitHub names the budget a response drew from. One without the header is kept apart rather than
# assumed to have drawn from `core`.
UNKNOWN_RESOURCE = 'unknown'

RATE_LIMIT_FAULTS = frozenset(
    {RequestFault.PRIMARY_RATE_LIMIT, RequestFault.SECONDARY_RATE_LIMIT, RequestFault.UNKNOWN_RATE_LIMIT}
)


def failure_detail(error: Exception) -> str:
    """The failure's type and reason, with no query string that could carry a signature."""
    reason = failure_reason(error) if isinstance(error, httpx.HTTPError) else with_query_masked(str(error))
    return f'{type(error).__name__}: {reason}'


class GitHubMonitor:
    """The GitHub client's request observer and the rate limiters' event handler for one component."""

    def __init__(self, monitor: ComponentMonitor, *, now: Callable[[], float] = time.time) -> None:
        self._logger = monitor.logger
        self._metrics = github_metrics(monitor.metrics)
        self._now = now

    def attempt_finished(self, attempt: RequestAttempt) -> None:
        fault = attempt.fault
        status = {} if attempt.response is None else {'status_code': attempt.response.status_code}
        self._metrics.count('requests.count', 1, **status)
        is_fault = fault not in (RequestFault.NONE, RequestFault.CANCELLED)
        self._metrics.count('requests.fault', int(is_fault), reason=fault, **status)
        self._metrics.count('requests.throttled', int(fault in RATE_LIMIT_FAULTS), **status)
        self._metrics.count('requests.retried', int(attempt.number > 1))
        self._metrics.distribution('requests.duration', attempt.duration_seconds, **status)
        if attempt.response is not None:
            self._emit_budget(attempt.response.headers)

        fields: dict[str, Any] = {
            'method': attempt.method,
            'endpoint': attempt.endpoint,
            'attempt': attempt.number,
            'duration_seconds': attempt.duration_seconds,
            **status,
        }
        if attempt.cancelled:
            self._logger.debug('GitHub request cancelled', reason=fault, **fields)
        elif attempt.error is None:
            self._logger.debug('GitHub request completed', **fields)
        else:
            self._logger.error(
                'GitHub request attempt failed',
                reason=fault,
                terminal=False,
                error=failure_detail(attempt.error),
                **fields,
            )

    def request_failed(self, failure: RequestFailure) -> None:
        last = failure.last_attempt
        fields: dict[str, Any] = {}
        if last is not None and last.error is not None:
            fields['reason'] = last.fault
            if last.response is not None:
                fields['status_code'] = last.response.status_code
        self._logger.error(
            'GitHub request failed',
            method=failure.method,
            endpoint=failure.endpoint,
            attempts=0 if last is None else last.number,
            terminal=True,
            error=failure_detail(failure.error),
            **fields,
        )

    def rate_limit_event(self, event: RateLimitEvent) -> None:
        # Called from inside the limiter, which must not fail because monitoring did.
        with suppress(Exception):
            if not isinstance(event, WaitEvent):
                return
            self._metrics.distribution(
                'throttle.wait.duration',
                event.elapsed_seconds,
                reason=event.reason,
                rate_limiter=event.name or None,
            )
            # DEBUG even when abandoned: the limiter's own events already warn about that.
            self._logger.debug(
                'GitHub rate limit wait ended',
                reason=event.reason,
                outcome=event.outcome,
                elapsed_seconds=event.elapsed_seconds,
                requested_seconds=event.requested_seconds,
                limiter=event.name or None,
            )

    def _emit_budget(self, headers: httpx.Headers) -> None:
        """Gauge the budget a response reports. Absent or unparseable values are not reported as zero."""
        resource = headers.get('x-ratelimit-resource') or UNKNOWN_RESOURCE
        for name in ('remaining', 'limit', 'used'):
            if (value := parse_header(headers, f'x-ratelimit-{name}', int)) is not None:
                self._metrics.gauge(f'requests.rate_limit.{name}', value, rate_limit_resource=resource)
        if (reset_at := parse_header(headers, 'x-ratelimit-reset', float)) is not None and math.isfinite(reset_at):
            self._metrics.gauge(
                'requests.rate_limit.reset_in', max(0.0, reset_at - self._now()), rate_limit_resource=resource
            )
