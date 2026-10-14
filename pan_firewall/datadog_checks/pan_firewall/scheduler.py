# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from collections.abc import Callable, Collection, Iterable

from .constants import COLLECTORS, INTERVALS


class FirewallSchedule:
    """Fixed-interval timers for the collectors of one firewall, on a monotonic clock. Collectors stay due until
    `mark_run()`, so a skipped cycle (a commit in progress) leaves them due."""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._clock = clock
        self._next_due: dict[str, float] = {}

    def now(self) -> float:
        """The schedule's clock, for timers that must follow it."""
        return self._clock()

    def due(self, enabled: Collection[str], identity_missing: bool = False) -> list[str]:
        """The enabled collectors that are due, in `COLLECTORS` order; the identity always while it is missing."""
        now = self._clock()
        return [
            name
            for name in COLLECTORS
            if (name in enabled and self._next_due.get(name, now) <= now)
            or (name == 'identity_metadata' and identity_missing)
        ]

    def mark_run(self, names: Iterable[str]) -> None:
        """Call it for the collectors that ran, whether they succeeded or not."""
        now = self._clock()
        for name in names:
            self._next_due[name] = now + INTERVALS[name]

    def make_due(self, name: str) -> None:
        self._next_due.pop(name, None)
