# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Rate-limited diagnostics shared by background exporters."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from enum import StrEnum

DIAGNOSTIC_WINDOW_SECONDS = 60.0


class DiagnosticCategory(StrEnum):
    """The bounded failure classes emitted by monitoring exporters."""

    QUEUE_FULL = 'queue_full'
    SUBMISSION = 'submission'
    CONVERSION = 'conversion'
    OVERSIZED = 'oversized'
    DEADLINE = 'deadline'
    CLIENT_CLOSE = 'client_close'


type DiagnosticSink = Callable[[DiagnosticCategory, str, Mapping[str, object]], None]


def plain_diagnostic_sink(callback: Callable[[str], None] | None) -> DiagnosticSink | None:
    """Adapt a human-readable callback to the structured diagnostics contract."""
    if callback is None:
        return None

    def report(_category: DiagnosticCategory, message: str, _fields: Mapping[str, object]) -> None:
        callback(message)

    return report


class RateLimitedDiagnostics:
    """Deliver the first failure in each category and summarize suppressed repeats."""

    def __init__(
        self,
        sink: DiagnosticSink | None = None,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._sink = sink
        self._clock = clock if clock is not None else time.monotonic
        self._lock = threading.Lock()
        self._reported_at: dict[DiagnosticCategory, float] = {}
        self._suppressed: dict[DiagnosticCategory, int] = {}

    @property
    def sink(self) -> DiagnosticSink | None:
        with self._lock:
            return self._sink

    @sink.setter
    def sink(self, sink: DiagnosticSink | None) -> None:
        with self._lock:
            self._sink = sink

    def __call__(self, category: DiagnosticCategory, message: str, fields: Mapping[str, object]) -> None:
        """Let the rate limiter stand in as a diagnostic sink, so every reporter shares one window."""
        self.report(category, message, **fields)

    def report(self, category: DiagnosticCategory, message: str, **fields: object) -> None:
        now = self._clock()
        with self._lock:
            reported_at = self._reported_at.get(category)
            if reported_at is not None and now - reported_at < DIAGNOSTIC_WINDOW_SECONDS:
                self._suppressed[category] = self._suppressed.get(category, 0) + 1
                return
            self._reported_at[category] = now
            suppressed, self._suppressed[category] = self._suppressed.get(category, 0), 0
        if suppressed:
            fields = {**fields, 'suppressed_notices': suppressed}
            message = f'{message} (plus {suppressed} earlier notice(s) suppressed)'
        self._deliver(category, message, fields)

    def summarize(self) -> None:
        with self._lock:
            pending = [(category, count) for category, count in self._suppressed.items() if count]
            self._suppressed.clear()
        for category, count in pending:
            self._deliver(
                category,
                f'{count} earlier {category} notice(s) were suppressed',
                {'suppressed_notices': count},
            )

    def _deliver(self, category: DiagnosticCategory, message: str, fields: Mapping[str, object]) -> None:
        with self._lock:
            sink = self._sink
        if sink is None:
            return
        try:
            sink(category, message, fields)
        except Exception:
            pass
