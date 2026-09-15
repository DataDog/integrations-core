# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Observable behavior of the buffered Datadog log handler."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import pytest

import ddev.monitoring.datadog as datadog_module
from ddev.monitoring.datadog import ENTRY_SIZE_LIMIT, REQUEST_ENTRIES_LIMIT, DatadogLogHandler
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


def test_delivery_failures_are_diagnosed_once_and_never_escape_close():
    submitter = FakeLogSubmitter()
    submitter.fail_next(RuntimeError('intake unavailable'), count=100)
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    emit_many(handler, 1200)
    handler.close()

    submitter.assert_no_logs()
    assert len(diagnostics) == 1
    assert 'failed' in diagnostics[0]


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


def test_requests_stay_below_the_intake_payload_limit():
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    for index in range(20):
        handler.emit(log_record(payload(f'Large log {index}', blob='x' * (240 * 1024))))
    handler.close()

    assert len(submitter.logs) == 20
    assert all(
        len(json.dumps(request, separators=(',', ':'), ensure_ascii=False).encode()) < 5 * 1024 * 1024
        for request in submitter.requests
    )
    assert not diagnostics


def test_an_oversized_log_is_dropped_with_a_notice():
    submitter = FakeLogSubmitter()
    diagnostics: list[str] = []
    handler = make_handler(submitter, diagnostics)

    handler.emit(log_record(payload('Huge', blob='x' * (ENTRY_SIZE_LIMIT + 1))))
    handler.close()

    submitter.assert_no_logs()
    assert any('entry limit' in notice for notice in diagnostics)
