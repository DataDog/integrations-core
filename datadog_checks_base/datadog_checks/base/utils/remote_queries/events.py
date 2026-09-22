# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query events."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator, Mapping
from typing import Any

from pydantic import ValidationError

from .contract import (
    RemoteQueryEmit,
    RemoteQueryEvent,
    RemoteQueryFailure,
    RemoteQueryRequest,
    RemoteQueryRunStats,
    validation_message,
)
from .timing import RemoteQueryProducerTimings

LOGGER = logging.getLogger(__name__)


def raise_if_timed_out(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise RemoteQueryFailure('timeout', 'Remote query exceeded timeoutMs.', retryable=True)


def remaining_wall_ms(deadline: float) -> int:
    """Clamp remaining database timeout to at least 1 ms: zero would disable server timeouts."""
    return max(1, int((deadline - time.monotonic()) * 1000))


def raise_if_cancelled(check: Any) -> None:
    # The Agent runtime exposes `is_cancelled` as a plain bool attribute on the check
    # object, while other runtimes (and test doubles) may expose a callable hook; honor
    # both shapes. An absent attribute carries no cancellation signal.
    is_cancelled = getattr(check, 'is_cancelled', None)
    if is_cancelled is None:
        return
    cancelled = is_cancelled() if callable(is_cancelled) else is_cancelled
    if cancelled:
        raise RemoteQueryFailure('cancelled', 'Remote query run was cancelled.', retryable=True)


def started_metadata(request: RemoteQueryRequest) -> dict[str, Any]:
    return {
        'status': 'STARTED',
        'operation': request.operation,
        'includeSchema': request.include_schema,
        'resultDelivery': request.result_delivery.model_dump(by_alias=True),
    }


def succeeded_metadata(
    receipt: Mapping[str, Any],
    stats: RemoteQueryRunStats,
    started_at: float,
    timings: RemoteQueryProducerTimings | None = None,
) -> dict[str, Any]:
    metadata = {
        'status': 'SUCCEEDED',
        'upload_receipt': dict(receipt),
        'stats': stats_metadata(stats, started_at),
    }
    if timings is not None:
        metadata['executionDiagnostics'] = timings.metadata(stats)
    return metadata


def stats_metadata(stats: RemoteQueryRunStats, started_at: float) -> dict[str, Any]:
    return {
        'rowsEmitted': stats.rows_emitted,
        'pagesEmitted': stats.pages_emitted,
        'bytesEmitted': stats.bytes_emitted,
        'elapsedMs': elapsed_ms(started_at),
    }


def failed_event(
    code: str,
    message: str,
    retryable: bool = False,
    stats: Mapping[str, Any] | None = None,
    elapsed_ms: int | None = None,
    execution_diagnostics: Mapping[str, Any] | None = None,
) -> RemoteQueryEvent:
    metadata: dict[str, Any] = {
        'status': 'FAILED',
        'error': {'code': code, 'message': message, 'retryable': retryable},
    }
    if stats is not None:
        metadata['stats'] = dict(stats)
    elif elapsed_ms is not None:
        metadata['stats'] = {'elapsedMs': elapsed_ms}
    if execution_diagnostics is not None:
        metadata['executionDiagnostics'] = dict(execution_diagnostics)
    return RemoteQueryEvent('error', metadata)


def matched_resolve_event(
    host: str | None,
    port: int | None,
    configured_dbname: str | None,
    resolved_dbname: str,
    database_instance: str | None,
) -> RemoteQueryEvent:
    """The per-check MATCHED resolve verdict: sanitized effective identity, no payload."""
    match: dict[str, Any] = {}
    if host is not None:
        match['host'] = host
    if port is not None:
        match['port'] = port
    if configured_dbname is not None:
        match['configuredDbname'] = configured_dbname
    match['resolvedDbname'] = resolved_dbname
    if database_instance is not None:
        match['databaseInstance'] = database_instance
    return RemoteQueryEvent('final', {'status': 'MATCHED', 'match': match})


def emit_event(emit: RemoteQueryEmit, event: RemoteQueryEvent) -> None:
    emit(event.event_type, json.dumps(event.metadata, default=str), event.payload)


def elapsed_ms(started_at: float) -> int:
    return max(0, int((time.monotonic() - started_at) * 1000))


def parse_agent_rpc_request(
    request_json: str | bytes | bytearray,
) -> tuple[Mapping[str, Any] | None, RemoteQueryProducerTimings, RemoteQueryEvent | None]:
    """Parse the bridge's request JSON with the run clock already running.

    Returns the parsed request object, the run's timing accumulator, and a failure event
    when the request is not a usable JSON object — malformed JSON or a non-object value:
    exactly one of the request and the failure event is set. Diagnostics collection
    starts before the parse so even a malformed request reports its measured wall.
    """
    started_at = time.monotonic()
    timings = RemoteQueryProducerTimings(started_at)
    try:
        request = json.loads(request_json)
    except (TypeError, ValueError):
        return (
            None,
            timings,
            failed_event(
                'invalid_request',
                'Invalid remote query request: request_json must be a valid JSON object.',
                execution_diagnostics=timings.metadata(),
            ),
        )
    if not isinstance(request, Mapping):
        return (
            None,
            timings,
            failed_event(
                'invalid_request',
                'Invalid remote query request: request_json must be a JSON object.',
                execution_diagnostics=timings.metadata(),
            ),
        )
    return request, timings, None


def emit_agent_rpc_events(emit: RemoteQueryEmit, events: Iterator[RemoteQueryEvent]) -> None:
    """Pump one event iterator into the Agent's emit callback.

    A callback failure (or any exception the generator raises) first closes the generator
    so its own cleanup — page buffers, database resources — runs, then propagates.
    """
    try:
        for event in events:
            emit_event(emit, event)
    except BaseException:
        events.close()
        raise


def validate_request(request: Any) -> RemoteQueryRequest:
    try:
        return RemoteQueryRequest.model_validate(request)
    except ValidationError as error:
        raise RemoteQueryFailure('invalid_request', validation_message(error)) from None


def query_failure_event(
    error: Exception, timings: RemoteQueryProducerTimings, stats: RemoteQueryRunStats | None
) -> RemoteQueryEvent:
    if not isinstance(error, RemoteQueryFailure):
        # Driver/transport exceptions can contain credentials, SQL or result values.
        LOGGER.error('Remote query execution failed')
        error = RemoteQueryFailure('query_failed', 'Remote query execution failed.')
    return failed_event(
        error.code,
        error.message,
        error.retryable,
        stats=stats_metadata(stats, timings.started_at) if stats is not None else None,
        elapsed_ms=elapsed_ms(timings.started_at),
        execution_diagnostics=timings.metadata(stats),
    )
