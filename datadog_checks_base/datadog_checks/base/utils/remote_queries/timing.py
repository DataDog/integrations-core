# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query timing."""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from .contract import RemoteQueryRunStats

REMOTE_QUERY_DIAGNOSTICS_CONTRACT_VERSION = 1


@dataclass
class RemoteQueryTimingPhase:
    """One entered producer phase segment; also the exit token for `exit_phase`."""

    name: str
    segment_start: float


PRODUCER_PHASE_METADATA_KEYS = (
    ('database_setup', 'databaseSetupMs'),
    ('database_fetch', 'databaseFetchMs'),
    ('encode_and_page_build', 'encodeAndPageBuildMs'),
    ('page_upload', 'pageUploadMs'),
    ('finalize', 'finalizeMs'),
)


def nearest_rank_percentile(sorted_ms: Sequence[float], quantile: float) -> float:
    """The pinned nearest-rank percentile: the ceil(quantile*N)-th of N ascending values.

    One definition shared by the emitted aggregates and their tests; `sorted_ms` must
    hold at least one value.
    """
    return sorted_ms[max(1, math.ceil(quantile * len(sorted_ms))) - 1]


class RemoteQueryProducerTimings:
    """Bounded per-run timing accumulator for the producer execution diagnostics contract."""

    def __init__(self, started_at: float, clock: Callable[[], float] | None = None):
        self.started_at = started_at
        self._clock = clock
        self._phase_ms: dict[str, float] = {}
        self._stack: list[RemoteQueryTimingPhase] = []
        self._page_walls_ms: list[float] = []
        self._pending_page_wall_ms: float | None = None
        self._upload_attempts = 0
        self._upload_retries = 0
        self._upload_attempts_measured = False
        self._first_page_ack_ms: float | None = None

    def _now(self) -> float:
        if self._clock is not None:
            return self._clock()
        return time.monotonic()

    def enter_phase(self, name: str) -> RemoteQueryTimingPhase:
        """Enter one phase, suspending the enclosing phase's accumulation."""
        now = self._now()
        if self._stack:
            enclosing = self._stack[-1]
            segment_ms = max(0.0, now - enclosing.segment_start) * 1000
            self._phase_ms[enclosing.name] = self._phase_ms.get(enclosing.name, 0.0) + segment_ms
        phase = RemoteQueryTimingPhase(name, now)
        self._stack.append(phase)
        return phase

    def exit_phase(self, phase: RemoteQueryTimingPhase) -> float:
        """Account one entered phase segment in ms; idempotent for an already-exited phase.

        The exit is a no-op unless the segment is still the top of the stack, so a phase
        that spans nested `with` blocks can be exited inline and then offered again from
        its spanning `finally`.
        """
        if not self._stack or self._stack[-1] is not phase:
            return 0.0
        now = self._now()
        self._stack.pop()
        segment_ms = max(0.0, now - phase.segment_start) * 1000
        self._phase_ms[phase.name] = self._phase_ms.get(phase.name, 0.0) + segment_ms
        if self._stack:
            self._stack[-1].segment_start = now
        return segment_ms

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        phase = self.enter_phase(name)
        try:
            yield
        finally:
            self.exit_phase(phase)

    @contextmanager
    def page_upload(self) -> Iterator[None]:
        """Bracket one whole `put_source_page` call — every attempt plus backoff — as page upload.

        The measured wall is stashed until `note_page_acknowledged` promotes it into the
        per-page distribution, so only verified, counted pages enter it; the cumulative
        `pageUploadMs` keeps every attempted wall either way.
        """
        phase = self.enter_phase('page_upload')
        try:
            yield
        finally:
            self._pending_page_wall_ms = self.exit_phase(phase)

    def note_page_acknowledged(self) -> None:
        """Promote the last uploaded page: receipt verified, counted, and acknowledged."""
        if self._pending_page_wall_ms is not None:
            self._page_walls_ms.append(self._pending_page_wall_ms)
            self._pending_page_wall_ms = None
        if self._first_page_ack_ms is None:
            self._first_page_ack_ms = max(0.0, self._now() - self.started_at) * 1000

    def note_upload_attempt(self, *, retry: bool) -> None:
        """Count one HTTP upload attempt; `retry` marks an attempt beyond a page's first."""
        self._upload_attempts += 1
        if retry:
            self._upload_retries += 1
        self._upload_attempts_measured = True

    def metadata(self, stats: RemoteQueryRunStats | None = None) -> dict[str, Any]:
        """The contract's camelCase producer diagnostics; only measured fields are present.

        `stats` mirrors the run counters at emission time; pass `None` when the run
        never started producing, so no receipt counters exist to mirror.
        """
        total_ms = max(0, int((self._now() - self.started_at) * 1000))
        producer: dict[str, Any] = {'totalMs': total_ms}
        named_ms = 0
        for phase_name, metadata_key in PRODUCER_PHASE_METADATA_KEYS:
            if phase_name in self._phase_ms:
                phase_ms = int(self._phase_ms[phase_name])
                producer[metadata_key] = phase_ms
                named_ms += phase_ms
        producer['otherMs'] = max(0, total_ms - named_ms)
        if self._first_page_ack_ms is not None:
            producer['timeToFirstPageMs'] = int(self._first_page_ack_ms)
        if stats is not None:
            producer['pageCount'] = stats.pages_emitted
            producer['rowCount'] = stats.rows_emitted
            producer['byteCount'] = stats.bytes_emitted
        if self._upload_attempts_measured:
            producer['uploadAttemptCount'] = self._upload_attempts
            producer['uploadRetryCount'] = self._upload_retries
        if self._page_walls_ms:
            walls = sorted(self._page_walls_ms)
            producer['pageUploadMinMs'] = int(walls[0])
            producer['pageUploadP50Ms'] = int(nearest_rank_percentile(walls, 0.50))
            producer['pageUploadP95Ms'] = int(nearest_rank_percentile(walls, 0.95))
            producer['pageUploadMaxMs'] = int(walls[-1])
        return {'contractVersion': REMOTE_QUERY_DIAGNOSTICS_CONTRACT_VERSION, 'producer': producer}
