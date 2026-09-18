# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Delivery diagnostics: a rate-limited channel for exporter failures."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from contextlib import suppress

DIAGNOSTIC_WINDOW_SECONDS = 60.0

type DiagnosticSink = Callable[[str], None]


class RateLimitedDiagnostics:
    """Report exporter failures to a caller-supplied callback, never to the export path itself."""

    def __init__(self, sink: DiagnosticSink | None) -> None:
        self._sink = sink
        self._lock = threading.Lock()
        self._reported_at: float | None = None
        self._suppressed = 0

    def report(self, text: str) -> None:
        """Pass *text* through, limiting repeated notices to one per window."""
        now = time.monotonic()
        with self._lock:
            if self._reported_at is not None and now - self._reported_at < DIAGNOSTIC_WINDOW_SECONDS:
                self._suppressed += 1
                return
            self._reported_at = now
            suppressed, self._suppressed = self._suppressed, 0
        if suppressed:
            text = f'{text} (plus {suppressed} earlier notices suppressed)'
        if self._sink is None:
            return
        with suppress(Exception):  # Diagnostics cannot interrupt delivery.
            self._sink(text)
