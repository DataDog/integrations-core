# (C) Datadog, Inc. 2026-present
# All rights reserved.
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query tracing."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

from datadog_checks.base.utils.tracing import INTEGRATION_TRACING_SERVICE_NAME

from .contract import (
    REMOTE_QUERY_TRACE_ID_HEADER,
    REMOTE_QUERY_TRACE_PARENT_ID_HEADER,
    REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER,
    RemoteQueryResultDelivery,
    RemoteQueryRunStats,
    RemoteQueryTraceContext,
)

LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Native producer spans (ddtrace)
# ---------------------------------------------------------------------------

# The existing integrations tracing identity: every other check-owned span the Agent-bundled
# ddtrace emits already runs under service ``datadog-agent-integrations``
# (``datadog_checks.base.utils.tracing``), so the producer spans reuse it instead of
# introducing a second service identity, and the producer root follows it completely:
# the integration name rides as its resource and ``_dd.origin`` carries the same service
# name, matching the tracing wrappers. The ``action.run`` span the request's trace
# context continues runs under the mini-tracer's ``private-action-runner`` service, but
# that route ships through instrumentation telemetry, not the local trace agent the
# producer spans use; whether the two routes join in one view is the producer plan's
# inherited open gate, not an assumption made here.
REMOTE_QUERY_PRODUCER_SPAN_SERVICE = INTEGRATION_TRACING_SERVICE_NAME

# The producer span operation vocabulary, pinned by the producer timing retirement plan:
# one root span carrying run identity and the bounded counters, and phase spans at the
# producer's own phase boundaries.
REMOTE_QUERY_PRODUCER_ROOT_SPAN_OPERATION = 'remote_queries.producer'
REMOTE_QUERY_DATABASE_SETUP_SPAN_OPERATION = 'remote_queries.database_setup'
REMOTE_QUERY_DATABASE_FETCH_SPAN_OPERATION = 'remote_queries.database_fetch'
REMOTE_QUERY_ENCODE_AND_PAGE_BUILD_SPAN_OPERATION = 'remote_queries.encode_and_page_build'
REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION = 'remote_queries.page_upload'
REMOTE_QUERY_FINALIZE_SPAN_OPERATION = 'remote_queries.finalize'
REMOTE_QUERY_ABORT_SPAN_OPERATION = 'remote_queries.abort'

# The phase names the adapters pass to ``phase``/``enter_phase``, mapped to their span
# operations. The database-fetch, page-upload, finalize, and abort spans open through
# their own explicit boundaries below, so their entries document the vocabulary only.
PRODUCER_SPAN_OPERATIONS = {
    'database_setup': REMOTE_QUERY_DATABASE_SETUP_SPAN_OPERATION,
    'database_fetch': REMOTE_QUERY_DATABASE_FETCH_SPAN_OPERATION,
    'encode_and_page_build': REMOTE_QUERY_ENCODE_AND_PAGE_BUILD_SPAN_OPERATION,
    'page_upload': REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION,
    'finalize': REMOTE_QUERY_FINALIZE_SPAN_OPERATION,
    'abort': REMOTE_QUERY_ABORT_SPAN_OPERATION,
}

# The root span's bounded tag surface: run identity, the integration, the established
# tracing origin, and the terminal status as tags; the page/row/byte/attempt/retry
# counters and the time to the first acknowledged page as metrics. The tag allowlist
# discipline is the retired diagnostics contract's: no query text, result values, target
# addresses, credentials, tokens, storage keys, hostnames, or raw error strings on any
# span. The failure classification rides the closed event error-code vocabulary through
# the standard ``error.type`` key.
REMOTE_QUERY_SPAN_RUN_ID_TAG = 'run_id'
REMOTE_QUERY_SPAN_TASK_ID_TAG = 'task_id'
REMOTE_QUERY_SPAN_UPLOAD_ID_TAG = 'upload_id'
REMOTE_QUERY_SPAN_INTEGRATION_TAG = 'integration'
REMOTE_QUERY_SPAN_ORIGIN_TAG = '_dd.origin'
REMOTE_QUERY_SPAN_STATUS_TAG = 'status'
REMOTE_QUERY_SPAN_ERROR_TYPE_TAG = 'error.type'
REMOTE_QUERY_SPAN_RETRY_TAG = 'retry'
REMOTE_QUERY_SPAN_HTTP_STATUS_METRIC = 'http.status_code'
REMOTE_QUERY_SPAN_PAGE_COUNT_METRIC = 'page_count'
REMOTE_QUERY_SPAN_ROW_COUNT_METRIC = 'row_count'
REMOTE_QUERY_SPAN_BYTE_COUNT_METRIC = 'byte_count'
REMOTE_QUERY_SPAN_UPLOAD_ATTEMPT_COUNT_METRIC = 'upload_attempt_count'
REMOTE_QUERY_SPAN_UPLOAD_RETRY_COUNT_METRIC = 'upload_retry_count'
REMOTE_QUERY_SPAN_TIME_TO_FIRST_PAGE_METRIC = 'time_to_first_page_ms'


def _inject_span_context(propagator: Any, span: Any, headers: Mapping[str, str]) -> dict[str, str]:
    """One upload request's headers with the span's context replacing the manual trace trio.

    Fail-open: a propagator failure answers the manual headers unchanged, so the request
    still falls back to parenting its intake span on the Agent execution trace.
    """
    injected = {
        header: value
        for header, value in headers.items()
        if header
        not in (
            REMOTE_QUERY_TRACE_ID_HEADER,
            REMOTE_QUERY_TRACE_PARENT_ID_HEADER,
            REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER,
        )
    }
    try:
        propagator.inject(span, injected)
    except Exception:
        LOGGER.debug('Native remote query producer span header injection failed')
        return dict(headers)
    return injected


class RemoteQueryProducerTracing:
    """Native, fail-open ddtrace producer spans for one remote query run.

    Real spans parented on the request's existing trace context, additive to the event
    contract — which stays byte-identical, and tracing failure of
    any kind never alters pages, receipts, retries, results, or errors.

    The tracer is the supported global ``ddtrace.trace.tracer`` singleton (importing
    ddtrace initializes that singleton together with its telemetry, which is accepted
    supported package behavior): no second ``Tracer`` is constructed, no writer or
    processor is configured, nothing is patched, no context is ever activated, and the
    singleton is never shut down. Parenting is explicit — the root starts with
    ``child_of`` a ``Context`` built from the validated request carrier, or as a local
    root trace when the request carried none, and every child names its own parent span
    — and ``HTTPPropagator.inject`` carries the active page-upload, finalize, or abort
    span's context into those requests' headers, replacing the manual trace-context
    headers whenever a span is open.

    Every method is fail-open: an import failure answers the null tracing, and a raising
    tracer poisons the rest of the run's spans (finishing everything already open) after
    one bounded, fixed-text debug log. ``close`` finishes the root and flushes the
    singleton once, best-effort.
    """

    def __init__(self, tracer: Any, propagator: Any, parent_context: Any, integration: str | None):
        self._tracer = tracer
        self._propagator = propagator
        # The validated request carrier as a ddtrace Context, or None for a local root trace.
        self._parent_context = parent_context
        self._integration = integration
        self._root: Any = None
        self._root_finished = False
        # The monotonic root start for time_to_first_page_ms, which counts to the first
        # acknowledged page.
        self._root_started_at: float | None = None
        # The open phase spans, outermost first; the root itself is never on the stack.
        self._spans: list[Any] = []
        # The open database-fetch region span: reads open one lazily and the next
        # page-upload attempt closes it, so the fetch span count stays bounded by
        # maxPages where a span per read would not be.
        self._fetch_span: Any = None
        # The open finalize/abort span whose context those upload requests inject.
        self._request_span: Any = None
        self._upload_attempts = 0
        self._upload_retries = 0
        self._first_page_ms: int | None = None
        self._failed = False

    def _current_parent(self) -> Any:
        return self._spans[-1] if self._spans else self._root

    def _start_child_span(self, operation: str) -> Any:
        """Start one child span on the current parent; None (run poisoned) on failure."""
        try:
            return self._tracer.start_span(operation, child_of=self._current_parent(), activate=False)
        except Exception:
            LOGGER.debug('Native remote query producer span creation failed')
            self._disable()
            return None

    def _disable(self) -> None:
        """Fail open for the rest of the run: finish every open span, never raise again.

        The root stays open for ``close`` so the trace still completes — the span
        aggregator holds a trace until every one of its spans has finished — and
        everything after this point is inert.
        """
        self._failed = True
        for span in (self._fetch_span, self._request_span, *reversed(self._spans)):
            if span is not None:
                try:
                    span.finish()
                except Exception:
                    pass
        self._spans = []
        self._fetch_span = None
        self._request_span = None

    def open_root(self, delivery: RemoteQueryResultDelivery) -> None:
        """Start the run's root span on the request's trace context, a local root when absent.

        The root follows the established integrations tracing identity: the service and
        ``_dd.origin`` both carry the integrations tracing service name and the
        integration name rides as the resource, ddtrace falling back to the operation
        name when it is unknown. The identity tags are the delivery's run/task/upload
        ids plus the integration; the terminal status, the counters, and any failure
        classification arrive with ``succeed`` or ``fail``.
        """
        if self._failed or self._root is not None:
            return
        try:
            span = self._tracer.start_span(
                REMOTE_QUERY_PRODUCER_ROOT_SPAN_OPERATION,
                child_of=self._parent_context,
                service=REMOTE_QUERY_PRODUCER_SPAN_SERVICE,
                resource=self._integration,
                activate=False,
            )
            self._root = span
            self._root_started_at = time.monotonic()
            span.set_tag(REMOTE_QUERY_SPAN_RUN_ID_TAG, delivery.run_id)
            span.set_tag(REMOTE_QUERY_SPAN_TASK_ID_TAG, delivery.task_id)
            span.set_tag(REMOTE_QUERY_SPAN_UPLOAD_ID_TAG, delivery.upload_id)
            span.set_tag(REMOTE_QUERY_SPAN_ORIGIN_TAG, INTEGRATION_TRACING_SERVICE_NAME)
            if self._integration is not None:
                span.set_tag(REMOTE_QUERY_SPAN_INTEGRATION_TAG, self._integration)
        except Exception:
            LOGGER.debug('Native remote query producer span creation failed')
            self._disable()

    def _terminal(self, *, status: str, error_code: str | None, stats: RemoteQueryRunStats) -> None:
        span = self._root
        if span is None or self._root_finished:
            return
        try:
            span.set_tag(REMOTE_QUERY_SPAN_STATUS_TAG, status)
            if error_code is not None:
                span.error = 1
                span.set_tag(REMOTE_QUERY_SPAN_ERROR_TYPE_TAG, error_code)
            span.set_metric(REMOTE_QUERY_SPAN_PAGE_COUNT_METRIC, stats.pages_emitted)
            span.set_metric(REMOTE_QUERY_SPAN_ROW_COUNT_METRIC, stats.rows_emitted)
            span.set_metric(REMOTE_QUERY_SPAN_BYTE_COUNT_METRIC, stats.bytes_emitted)
            span.set_metric(REMOTE_QUERY_SPAN_UPLOAD_ATTEMPT_COUNT_METRIC, self._upload_attempts)
            span.set_metric(REMOTE_QUERY_SPAN_UPLOAD_RETRY_COUNT_METRIC, self._upload_retries)
            if self._first_page_ms is not None:
                span.set_metric(REMOTE_QUERY_SPAN_TIME_TO_FIRST_PAGE_METRIC, self._first_page_ms)
            span.finish()
            self._root_finished = True
        except Exception:
            LOGGER.debug('Native remote query producer span termination failed')
            self._disable()

    def succeed(self, stats: RemoteQueryRunStats) -> None:
        """Finish the root as SUCCEEDED with the run's counters (intake-authoritative)."""
        self._terminal(status='SUCCEEDED', error_code=None, stats=stats)

    def fail(self, error_code: str, stats: RemoteQueryRunStats) -> None:
        """Finish the root as FAILED with the failure code and the partial counters."""
        self._terminal(status='FAILED', error_code=error_code, stats=stats)

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        """One phase span scope at a producer phase boundary."""
        token = self.enter_phase(name)
        try:
            yield
        finally:
            self.exit_phase(token)

    def enter_phase(self, name: str) -> Any:
        """Start one phase span; the exit token for ``exit_phase``, or None when inert.

        ``name`` is the producer phase vocabulary; an unmapped name starts no
        span, so a vocabulary drift degrades to a missing span instead of poisoning the
        run's tracing.
        """
        if self._failed or self._root is None:
            return None
        operation = PRODUCER_SPAN_OPERATIONS.get(name)
        if operation is None:
            return None
        span = self._start_child_span(operation)
        if span is None:
            return None
        self._spans.append(span)
        return span

    def exit_phase(self, phase: Any) -> None:
        """Close one entered phase span; a no-op unless it is still the innermost open span.

        Idempotent, so a phase spanning nested ``with`` blocks can be exited inline and
        then again from its spanning ``finally``.
        """
        if self._failed or phase is None or not self._spans or self._spans[-1] is not phase:
            return
        self._spans.pop()
        # Children first: an open fetch region closes before its enclosing phase span.
        self._close_fetch_region()
        try:
            phase.finish()
        except Exception:
            LOGGER.debug('Native remote query producer span finishing failed')
            self._disable()

    def _close_fetch_region(self) -> None:
        span = self._fetch_span
        if span is None:
            return
        self._fetch_span = None
        try:
            span.finish()
        except Exception:
            LOGGER.debug('Native remote query producer span finishing failed')
            self._disable()

    def enter_fetch(self) -> None:
        """Keep one database-fetch region span open across the result-stream reads.

        One span covers one page's worth of reads: the region opens lazily on the first
        read after the previous page upload (or phase entry) and closes when the next
        page-upload attempt starts or its enclosing phase exits.
        """
        if self._failed or self._root is None or self._fetch_span is not None:
            return
        self._fetch_span = self._start_child_span(REMOTE_QUERY_DATABASE_FETCH_SPAN_OPERATION)

    def begin_page_upload_attempt(self, *, retry: bool) -> Any:
        """Start one page-upload attempt span and answer its handle, or None when inert.

        The attempt and retry counters feed the root span's metrics: one count per HTTP page
        upload attempt, a retry being any attempt beyond a page's first.
        """
        if self._failed or self._root is None:
            return None
        self._upload_attempts += 1
        if retry:
            self._upload_retries += 1
        # The upload ends the fetch region it interrupted.
        self._close_fetch_region()
        span = self._start_child_span(REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION)
        if span is None:
            return None
        try:
            span.set_tag(REMOTE_QUERY_SPAN_RETRY_TAG, 'true' if retry else 'false')
        except Exception:
            LOGGER.debug('Native remote query producer span tagging failed')
            self._disable()
            return None
        return _PageUploadAttempt(self, self._propagator, span)

    def inject_request_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        """One finalize/abort request's headers: the open request span's injected context.

        With no open request span — the writer never opened its finalize span, or the
        tracing degraded — the manual trace-context headers stand unchanged.
        """
        if self._failed or self._request_span is None:
            return dict(headers)
        return _inject_span_context(self._propagator, self._request_span, headers)

    def _open_request_span(self, operation: str) -> Any:
        if self._failed or self._root is None:
            return None
        span = self._start_child_span(operation)
        if span is None:
            return None
        self._request_span = span
        return span

    def _close_request_span(self, span: Any) -> None:
        if span is None or self._request_span is not span:
            return
        self._request_span = None
        try:
            span.finish()
        except Exception:
            LOGGER.debug('Native remote query producer span finishing failed')
            self._disable()

    @contextmanager
    def finalize_span(self) -> Iterator[None]:
        """The finalize phase span, also the injection parent of the finalize requests."""
        token = self._open_request_span(REMOTE_QUERY_FINALIZE_SPAN_OPERATION)
        try:
            yield
        finally:
            self._close_request_span(token)

    @contextmanager
    def abort_span(self) -> Iterator[None]:
        """The abort span around the failure tail's best-effort upload abort."""
        token = self._open_request_span(REMOTE_QUERY_ABORT_SPAN_OPERATION)
        try:
            yield
        finally:
            self._close_request_span(token)

    def note_page_acknowledged(self) -> None:
        """Record the first acknowledged page's wall from the root span's start, once.

        The root span's metric counts to the first receipt-verified, counted page —
        the same boundary an operator would time by hand.
        """
        if self._first_page_ms is not None or self._root_started_at is None:
            return
        self._first_page_ms = max(0, int((time.monotonic() - self._root_started_at) * 1000))

    def close(self) -> None:
        """Finish the root span (defensively, if no terminal call did) and flush once.

        The flush is the run's only one, best-effort and bounded: a disabled trace agent
        or an unreachable socket is swallowed after a fixed-text debug log. The singleton
        is never shut down — other check activity may share it.
        """
        span = self._root
        if span is not None and not self._root_finished:
            try:
                span.finish()
                self._root_finished = True
            except Exception:
                LOGGER.debug('Native remote query producer span finishing failed')
        try:
            self._tracer.flush()
        except Exception:
            LOGGER.debug('Native remote query producer span flush failed')


class _PageUploadAttempt:
    """One open page-upload attempt span, the injection parent of its own HTTP request.

    ``inject`` answers the attempt's request headers — the manual trace-context trio
    replaced by this span's injected context, or the manual headers unchanged when the
    propagator fails — and ``finish`` closes the attempt with its bounded outcome
    classification: no response (``transport``), a non-2xx rejection (``rejected``), or
    success.
    """

    def __init__(self, tracing: RemoteQueryProducerTracing, propagator: Any, span: Any):
        self._tracing = tracing
        self._propagator = propagator
        self._span = span

    def inject(self, headers: Mapping[str, str]) -> dict[str, str]:
        return _inject_span_context(self._propagator, self._span, headers)

    def finish(self, *, error: str | None, http_status: int | None) -> None:
        try:
            if error is not None:
                self._span.error = 1
                self._span.set_tag(REMOTE_QUERY_SPAN_ERROR_TYPE_TAG, error)
            if http_status is not None:
                self._span.set_metric(REMOTE_QUERY_SPAN_HTTP_STATUS_METRIC, http_status)
            self._span.finish()
        except Exception:
            LOGGER.debug('Native remote query producer span finishing failed')
            self._tracing._disable()


class NullRemoteQueryProducerTracing(RemoteQueryProducerTracing):
    """No-op producer tracing so instrumentation call sites never branch on ``tracing is None``."""

    def __init__(self) -> None:
        pass

    def open_root(self, delivery: RemoteQueryResultDelivery) -> None:
        pass

    def succeed(self, stats: RemoteQueryRunStats) -> None:
        pass

    def fail(self, error_code: str, stats: RemoteQueryRunStats) -> None:
        pass

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        token = self.enter_phase(name)
        try:
            yield
        finally:
            self.exit_phase(token)

    def enter_phase(self, name: str) -> Any:
        return None

    def exit_phase(self, phase: Any) -> None:
        pass

    def enter_fetch(self) -> None:
        pass

    def begin_page_upload_attempt(self, *, retry: bool) -> Any:
        return None

    def inject_request_headers(self, headers: Mapping[str, str]) -> dict[str, str]:
        return dict(headers)

    @contextmanager
    def finalize_span(self) -> Iterator[None]:
        yield

    @contextmanager
    def abort_span(self) -> Iterator[None]:
        yield

    def note_page_acknowledged(self) -> None:
        pass

    def close(self) -> None:
        pass


NULL_PRODUCER_TRACING = NullRemoteQueryProducerTracing()


def open_remote_query_producer_tracing(
    trace_context: RemoteQueryTraceContext | None, integration: str | None
) -> RemoteQueryProducerTracing:
    """Open one run's producer tracing against the supported global ddtrace singleton.

    The import is lazy and wrapped: ddtrace initializes its supported singleton tracer
    and telemetry on import, which is accepted as-is, and any failure — the package
    unimportable on a non-Agent host, a raising tracer — answers the null tracing, so
    the run executes exactly as before and the manual trace-context headers stay the
    upload requests' tracing fallback. The singleton is never configured, patched, or
    shut down here.
    """
    try:
        from ddtrace.propagation.http import HTTPPropagator
        from ddtrace.trace import Context, tracer
    except Exception:
        LOGGER.debug('Native remote query producer spans are unavailable: ddtrace did not import')
        return NULL_PRODUCER_TRACING
    try:
        parent_context = None
        if trace_context is not None:
            parent_context = Context(
                trace_id=int(trace_context.trace_id),
                span_id=int(trace_context.parent_id),
                sampling_priority=trace_context.sampling_priority,
            )
    except Exception:
        LOGGER.debug('Native remote query producer spans are unavailable for this run')
        return NULL_PRODUCER_TRACING
    return RemoteQueryProducerTracing(tracer, HTTPPropagator, parent_context, integration)
