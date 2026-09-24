# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Observable behavior of the buffered Datadog log handler."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from typing import Any

import pytest
from datadog_api_client.exceptions import ApiException
from datadog_api_client.v2.model.http_log import HTTPLog
from datadog_api_client.v2.model.http_log_item import HTTPLogItem

import ddev.monitoring.datadog as datadog_module
from ddev.monitoring.datadog import REQUEST_ENTRIES_LIMIT, DatadogLogHandler
from tests.helpers.datadog import FakeLogSubmitter


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(record.msg, separators=(',', ':'), ensure_ascii=False)


def make_handler(submitter: FakeLogSubmitter, diagnostics: list[str], **kwargs: Any) -> DatadogLogHandler:
    handler = DatadogLogHandler(api_key='test-api-key', submitter=submitter, diagnostics=diagnostics.append, **kwargs)
    handler.setFormatter(JsonLogFormatter())
    return handler


def log_record(payload: object) -> logging.LogRecord:
    return logging.LogRecord('ddev.monitoring', logging.INFO, __file__, 1, payload, None, None)


def payload(message: str, **attributes: object) -> dict[str, object]:
    return {'message': message, 'status': 'info', 'service': 'test-service', **attributes}


def emit_many(handler: DatadogLogHandler, count: int) -> None:
    for index in range(count):
        handler.emit(log_record(payload(f'Log {index}', sequence=str(index))))


def test_the_queued_log_is_the_payload_as_it_was_formatted():
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)
    attributes = payload('Batch dispatched', batch_id='batch-01')

    handler.emit(log_record(attributes))
    attributes['batch_id'] = 'changed-after-emission'
    handler.close()

    submitter.assert_log_matches({'message': 'Batch dispatched', 'batch_id': 'batch-01'})
    assert not diagnostics


def test_queued_logs_are_batched_under_the_request_limit_and_drained_on_close():
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    emit_many(handler, 1200)
    handler.close()

    assert len(submitter.logs) == 1200
    assert all(len(request) <= REQUEST_ENTRIES_LIMIT for request in submitter.requests)
    handler.close()
    assert len(submitter.logs) == 1200
    assert not diagnostics


def test_delivery_failures_are_diagnosed_once_and_close_reports_the_suppressed_repeats():
    submitter = FakeLogSubmitter()
    submitter.fail_next(RuntimeError('intake unavailable'), count=100)
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    emit_many(handler, 1200)
    handler.close()

    submitter.assert_no_logs()
    assert len(diagnostics) == 2
    assert 'failed' in diagnostics[0]
    # Close reports how many failures the window suppressed, so repeats leave a trace.
    assert '2 earlier submission notice(s) were suppressed' in diagnostics[1]


def test_a_full_queue_drops_logs_instead_of_blocking_the_emitter():
    submitter = FakeLogSubmitter()
    submitter.block_submissions()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics, queue_size=2)

    emit_many(handler, 1)
    assert submitter.wait_for_submission()
    emit_many(handler, 50)

    assert any('queue is full' in notice for notice in diagnostics)
    submitter.resume_submissions()
    handler.close()


def test_a_different_category_is_delivered_immediately_inside_another_categorys_window():
    """Rate limiting is per category, so one noisy kind of failure cannot silence the rest."""
    submitter = FakeLogSubmitter()
    submitter.fail_next(RuntimeError('intake unavailable'), count=100)
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics, queue_size=2)

    emit_many(handler, 1)
    assert submitter.wait_for_submission()  # A submission failure opens the window for its category.
    submitter.block_submissions()
    emit_many(handler, 1)
    assert submitter.wait_for_submission()  # The worker now blocks inside its submission.
    emit_many(handler, 50)

    assert any('failed' in notice for notice in diagnostics)
    assert any('queue is full' in notice for notice in diagnostics)
    submitter.resume_submissions()
    handler.close()


def test_shutdown_returns_at_its_deadline_while_intake_is_blocked():
    submitter = FakeLogSubmitter()
    submitter.block_submissions()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)
    emit_many(handler, 1)
    assert submitter.wait_for_submission()

    started = time.monotonic()
    handler.close(timeout=0.01)
    elapsed = time.monotonic() - started

    assert elapsed < 0.5
    assert any('deadline' in notice for notice in diagnostics)
    submitter.resume_submissions()


def test_a_negative_shutdown_timeout_is_rejected_without_closing_the_handler():
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    with pytest.raises(ValueError, match='timeout must not be negative'):
        handler.close(timeout=-1)

    handler.emit(log_record(payload('Delivered after invalid close')))
    handler.close()
    submitter.assert_logs(payload('Delivered after invalid close'))
    assert not diagnostics


def test_the_owned_api_client_is_closed_after_the_worker_stops(monkeypatch: pytest.MonkeyPatch):
    clients = []
    submitter = FakeLogSubmitter()

    class FakeApiClient:
        def __init__(self, _configuration: object) -> None:
            self.closed = False
            clients.append(self)

        def close(self) -> None:
            self.closed = True

    def make_submitter(_client: FakeApiClient) -> FakeLogSubmitter:
        return submitter

    monkeypatch.setattr(datadog_module, 'ApiClient', FakeApiClient)
    monkeypatch.setattr(datadog_module, 'LogsApi', make_submitter)
    handler = DatadogLogHandler(api_key='test-api-key')
    handler.setFormatter(JsonLogFormatter())

    handler.emit(log_record(payload('Delivered')))
    handler.close()

    submitter.assert_logs(payload('Delivered'))
    assert clients[0].closed


def test_a_failing_owned_client_close_is_diagnosed_without_escaping_the_worker(monkeypatch: pytest.MonkeyPatch):
    unhandled: list[object] = []
    monkeypatch.setattr(threading, 'excepthook', lambda args: unhandled.append(args))
    submitter = FakeLogSubmitter()

    class FailingCloseClient:
        def __init__(self, _configuration: object) -> None:
            pass

        def close(self) -> None:
            raise RuntimeError('client teardown failed')

    monkeypatch.setattr(datadog_module, 'ApiClient', FailingCloseClient)
    monkeypatch.setattr(datadog_module, 'LogsApi', lambda _client: submitter)
    diagnostics: list[str] = []
    handler = DatadogLogHandler(api_key='test-api-key', diagnostics=diagnostics.append)
    handler.setFormatter(JsonLogFormatter())

    handler.emit(log_record(payload('Delivered')))
    handler.close()

    submitter.assert_logs(payload('Delivered'))
    assert any('closing the logs API client failed' in notice for notice in diagnostics)
    assert not unhandled


@pytest.mark.parametrize(
    'invalid_payload',
    [
        ['not', 'an', 'object'],
        {'status': 'info'},
        {'message': 'Numeric attribute', 'attempt': 1},
    ],
    ids=['not-an-object', 'missing-message', 'non-string-attribute'],
)
def test_invalid_formatter_output_is_dropped_with_a_diagnostic(invalid_payload: object):
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    handler.emit(log_record(invalid_payload))
    handler.close()

    submitter.assert_no_logs()
    assert any('could not be formatted' in notice for notice in diagnostics)


def test_formatter_failures_do_not_escape_the_logging_handler():
    class Unserializable:
        pass

    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    handler.emit(log_record(payload('Invalid value', metadata=Unserializable())))
    handler.close()

    submitter.assert_no_logs()
    assert any('could not be formatted' in notice for notice in diagnostics)


def test_a_request_the_api_rejects_is_split_until_it_is_accepted():
    submitter = FakeLogSubmitter()
    submitter.fail_next(ApiException(status=413, reason='Payload Too Large'))
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    emit_many(handler, 4)
    handler.close()

    assert len(submitter.logs) == 4
    assert all(len(request) <= 2 for request in submitter.requests)
    assert not diagnostics


def test_a_log_the_api_rejects_alone_is_dropped_without_losing_its_siblings():
    class RejectsBlobLogs(FakeLogSubmitter):
        def submit_log(self, body: HTTPLog) -> object:
            self.begin_submission()
            if any('blob:' in (getattr(item, 'ddtags', None) or '') for item in body.value):
                raise ApiException(status=413, reason='Payload Too Large')
            self.requests.append([item.to_dict() for item in body.value])
            return {}

    submitter = RejectsBlobLogs()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    handler.emit(log_record(payload('Fine 1')))
    handler.emit(log_record(payload('Fine 2')))
    handler.emit(log_record(payload('Huge', ddtags='blob:' + 'x' * 600_000)))
    handler.close()

    assert [log['message'] for log in submitter.logs] == ['Fine 1', 'Fine 2']
    assert any('too large on its own' in notice for notice in diagnostics)


def test_shutdown_drains_the_queue_when_the_sentinel_cannot_be_enqueued(monkeypatch: pytest.MonkeyPatch):
    """close() swallows a full-queue sentinel failure, so the worker must exit on a
    drained closed queue instead of waiting for a sentinel that never entered it."""

    class SentinelBlockedQueue(queue.Queue):
        def put_nowait(self, item: HTTPLogItem | None) -> None:
            if item is None:
                raise queue.Full
            super().put_nowait(item)

    monkeypatch.setattr(datadog_module.queue, 'Queue', SentinelBlockedQueue)
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    handler.emit(log_record(payload('Queued one')))
    handler.emit(log_record(payload('Queued two')))
    handler.close()

    assert [log['message'] for log in submitter.logs] == ['Queued one', 'Queued two']
    assert not diagnostics


def test_a_log_accepted_after_a_stale_empty_poll_is_drained_at_shutdown(monkeypatch: pytest.MonkeyPatch):
    """An empty-queue observation that predates an acceptance must not end the worker:
    the accepted log sits ahead of the sentinel, and exiting skips both."""
    empty_observed = threading.Event()
    resume_worker = threading.Event()
    sentinel_queued = threading.Event()

    class StaleEmptyQueue(queue.Queue):
        """Hold the worker between its empty observation and the Empty it acts on."""

        observing = True

        def get(self, block: bool = True, timeout: float | None = None) -> HTTPLogItem | None:
            if self.observing:
                try:
                    return super().get(block=False)
                except queue.Empty:
                    self.observing = False
                    empty_observed.set()
                    assert resume_worker.wait(5)
                    raise
            return super().get(block=block, timeout=timeout)

        def put_nowait(self, item: HTTPLogItem | None) -> None:
            super().put_nowait(item)
            if item is None:
                sentinel_queued.set()

    monkeypatch.setattr(datadog_module.queue, 'Queue', StaleEmptyQueue)
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)
    closing: threading.Thread | None = None
    try:
        assert empty_observed.wait(5)
        handler.emit(log_record(payload('Accepted after a stale empty poll')))
        closing = threading.Thread(target=handler.close)
        closing.start()
        assert sentinel_queued.wait(5)
    finally:
        resume_worker.set()
        if closing is not None:
            closing.join(5)
        handler.close()

    submitter.assert_logs(payload('Accepted after a stale empty poll'))
    assert not diagnostics


def test_a_log_racing_close_is_delivered_not_stranded_behind_the_worker(monkeypatch: pytest.MonkeyPatch):
    """A log accepted while shutdown runs must land ahead of the sentinel, where the worker
    still delivers it (see the review of
    https://github.com/DataDog/integrations-core/pull/25274#discussion_r4061350829)."""
    seen_first = threading.Event()
    released = threading.Event()
    closed = threading.Event()

    class GatedPutQueue(queue.Queue):
        """Hold the first accepted log inside its check-then-enqueue window."""

        def put_nowait(self, item: object) -> None:
            if not seen_first.is_set():
                seen_first.set()
                assert released.wait(5)
            super().put_nowait(item)

    monkeypatch.setattr(datadog_module.queue, 'Queue', GatedPutQueue)
    submitter = FakeLogSubmitter()
    handler = make_handler(submitter, [])

    racing = threading.Thread(target=handler.emit, args=(log_record(payload('Racing log')),))
    racing.start()
    assert seen_first.wait(5)

    def run_close() -> None:
        try:
            handler.close()
        finally:
            closed.set()

    closing = threading.Thread(target=run_close)
    closing.start()
    try:
        # With acceptance serialized, shutdown waits on the log's critical section; without it,
        # close finishes here and releasing the log strands it behind the sentinel.
        closed.wait(0.5)
    finally:
        released.set()

    racing.join(5)
    closing.join(5)
    assert not closing.is_alive()
    assert [log['message'] for log in submitter.logs] == ['Racing log']
