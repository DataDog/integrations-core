# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import time
from collections.abc import Callable, Collection, Iterable
from enum import Enum
from typing import TYPE_CHECKING

from .constants import COLLECTORS, COMMIT_SKIP_MAX_SECONDS, FAILURE_RETRY_SECONDS, IDENTITY, INTERVALS

if TYPE_CHECKING:
    from datadog_checks.base.log import CheckLoggingAdapter

    from .collectors.jobs import BusyJob


class Result(Enum):
    """What happened this run to the jobs check, the identity or a collector. A name with no result stays due."""

    RAN = 'ran'
    FAILED = 'failed'
    UNREACHABLE = 'unreachable'  # failed, because the firewall could not be reached
    SKIPPED = 'skipped'  # not run, or cut short, after another call could not reach the firewall: stays due


class FirewallSchedule:
    """Fixed-interval timers for the collectors of one firewall, on a monotonic clock. Collectors stay due until
    `mark_run()` or `mark_failed()`, so a skipped cycle (a commit in progress) leaves them due.

    Every method takes the `now` read once at the start of the run. The Agent starts runs on a fixed grid, so a timer
    counted from the end of a run would make the run one interval later a little early, and delay it by one more run.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._next_due: dict[str, float] = {}

    def now(self) -> float:
        return self._clock()

    def due(self, enabled: Collection[str], now: float, identity_missing: bool = False) -> list[str]:
        """The enabled collectors that are due, in `COLLECTORS` order; the identity always while it is missing."""
        return [
            name
            for name in COLLECTORS
            if (name in enabled and self._next_due.get(name, now) <= now) or (name == IDENTITY and identity_missing)
        ]

    def mark_run(self, names: Iterable[str], now: float) -> None:
        """Call it for the collectors that succeeded: they are due again after their interval."""
        for name in names:
            self._next_due[name] = now + INTERVALS[name]

    def mark_failed(self, names: Iterable[str], now: float) -> None:
        """Call it for the collectors that failed: they are due again after `FAILURE_RETRY_SECONDS` at most."""
        for name in names:
            self._next_due[name] = now + min(INTERVALS[name], FAILURE_RETRY_SECONDS)

    def record(self, results: dict[str, Result], now: float) -> None:
        """Set the timers from a run's results: RAN waits its interval, FAILED and UNREACHABLE retry within
        `FAILURE_RETRY_SECONDS`, and anything else (SKIPPED, no result) stays due. The jobs check has no timer."""
        self.mark_run((name for name, result in results.items() if result is Result.RAN), now)
        self.mark_failed(
            (
                name
                for name, result in results.items()
                if result in (Result.FAILED, Result.UNREACHABLE) and name in INTERVALS
            ),
            now,
        )

    def make_due(self, name: str) -> None:
        self._next_due.pop(name, None)


class BusyGate:
    """Skips collection while a commit or content update is in progress, for at most `COMMIT_SKIP_MAX_SECONDS` per busy
    period; after that the firewall is collected anyway, with one warning."""

    def __init__(self, log: CheckLoggingAdapter, ip: str):
        self._log = log
        self._ip = ip
        # Schedule-clock start of the current busy period, None while the firewall is not busy.
        self._since: float | None = None
        self._cap_warned = False

    def skip(self, jobs: list[BusyJob], now: float) -> bool:
        """True to skip this run's collectors, given the jobs in progress and the schedule's clock."""
        if not jobs:
            self.end()
            return False
        jobs_text = ', '.join(f'{job.type} job {job.id}' for job in jobs)
        if self._since is None:
            self._since = now
            self._cap_warned = False
        if now - self._since < COMMIT_SKIP_MAX_SECONDS:
            self._log.debug('%s: %s in progress, skipping collection this run', self._ip, jobs_text)
            return True
        if not self._cap_warned:
            self._cap_warned = True
            self._log.warning(
                '%s: %s still in progress after %ds of skipping; collecting anyway',
                self._ip,
                jobs_text,
                COMMIT_SKIP_MAX_SECONDS,
            )
        return False

    def end(self) -> None:
        """End the busy period: the next job in progress starts a new one."""
        self._since = None
