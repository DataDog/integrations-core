# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Observable behavior of rate-limited exporter diagnostics."""

from __future__ import annotations

from collections.abc import Mapping

from ddev.monitoring.diagnostics import DIAGNOSTIC_WINDOW_SECONDS, DiagnosticCategory, RateLimitedDiagnostics
from tests.helpers.clock import FakeClock


class RecordingDiagnostics:
    def __init__(self) -> None:
        self.events: list[tuple[DiagnosticCategory, str, Mapping[str, object]]] = []

    def __call__(
        self,
        category: DiagnosticCategory,
        message: str,
        fields: Mapping[str, object],
    ) -> None:
        self.events.append((category, message, fields))


def test_each_failure_category_has_an_independent_rate_limit():
    delivered = RecordingDiagnostics()
    diagnostics = RateLimitedDiagnostics(delivered, clock=FakeClock())

    diagnostics.report(DiagnosticCategory.SUBMISSION, 'submission failed')
    diagnostics.report(DiagnosticCategory.QUEUE_FULL, 'queue full')
    diagnostics.report(DiagnosticCategory.CONVERSION, 'record dropped', metric_name='jobs')

    assert delivered.events == [
        (DiagnosticCategory.SUBMISSION, 'submission failed', {}),
        (DiagnosticCategory.QUEUE_FULL, 'queue full', {}),
        (DiagnosticCategory.CONVERSION, 'record dropped', {'metric_name': 'jobs'}),
    ]


def test_repeated_failures_are_summarized_on_the_next_delivery():
    clock = FakeClock()
    delivered = RecordingDiagnostics()
    diagnostics = RateLimitedDiagnostics(delivered, clock=clock)

    for _ in range(3):
        diagnostics.report(DiagnosticCategory.SUBMISSION, 'submission failed')
    clock.advance(DIAGNOSTIC_WINDOW_SECONDS)
    diagnostics.report(DiagnosticCategory.SUBMISSION, 'submission failed')

    assert delivered.events == [
        (DiagnosticCategory.SUBMISSION, 'submission failed', {}),
        (
            DiagnosticCategory.SUBMISSION,
            'submission failed (plus 2 earlier notice(s) suppressed)',
            {'suppressed_notices': 2},
        ),
    ]


def test_close_summary_delivers_suppressed_counts():
    delivered = RecordingDiagnostics()
    diagnostics = RateLimitedDiagnostics(delivered, clock=FakeClock())

    diagnostics.report(DiagnosticCategory.SUBMISSION, 'submission failed')
    diagnostics.report(DiagnosticCategory.SUBMISSION, 'submission failed')
    diagnostics.summarize()

    assert delivered.events[-1] == (
        DiagnosticCategory.SUBMISSION,
        '1 earlier submission notice(s) were suppressed',
        {'suppressed_notices': 1},
    )


def test_the_diagnostic_sink_can_be_replaced():
    first = RecordingDiagnostics()
    second = RecordingDiagnostics()
    diagnostics = RateLimitedDiagnostics(first, clock=FakeClock())

    diagnostics.sink = second
    diagnostics.report(DiagnosticCategory.QUEUE_FULL, 'queue full')

    assert not first.events
    assert second.events == [(DiagnosticCategory.QUEUE_FULL, 'queue full', {})]
