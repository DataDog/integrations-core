# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import hashlib
import io
import json
import logging
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import timing as rq_timing
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing
from datadog_checks.base.utils.remote_queries import upload as rq_upload

from .helpers import (
    PARENT_ID,
    TRACE_ID,
    RefusingPropagator,
    acceptance_receipt,
    descriptor,
    descriptor_receipt,
    finalize_receipt,
    make_tracing,
    pending_receipt,
    receipt,
    source_page,
)


def test_descriptor_receipt_confirms_the_registration_exactly():
    upload_descriptor = descriptor(columns=(('value', 'text', 'string'),), include_schema=True)
    body = rq_contract.descriptor_request_bytes(upload_descriptor)
    rq_upload.verify_descriptor_response(descriptor_receipt(body), 'upload-1', upload_descriptor, body)


@pytest.mark.parametrize(
    'field,bad',
    [
        ('upload_id', None),  # missing
        ('upload_id', 123),  # mistyped
        ('upload_id', 'other-upload'),  # mismatched
        ('format_version', None),
        ('format_version', 2),
        ('format_version', 'csv-json-cell-v2'),
        ('include_schema', None),
        ('include_schema', 0),
        ('include_schema', False),  # flipped against the registered descriptor
        ('columns', None),
        ('columns', '1'),
        ('columns', 2),
        ('sha256', None),
        ('sha256', 'A' * 64),  # the pinned receipt is lowercase hex
        ('sha256', hashlib.sha256(b'other canonical descriptor bytes').hexdigest()),
    ],
)
def test_descriptor_receipt_rejects_missing_mistyped_or_mismatched_fields(field, bad):
    upload_descriptor = descriptor(columns=(('value', 'text', 'string'),), include_schema=True)
    body = rq_contract.descriptor_request_bytes(upload_descriptor)
    receipt = descriptor_receipt(body)
    if bad is None:
        del receipt[field]
    else:
        receipt[field] = bad
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.verify_descriptor_response(receipt, 'upload-1', upload_descriptor, body)
    assert failure.value.code == 'invalid_receipt'


def test_descriptor_receipt_allows_no_keys_beyond_the_pinned_five():
    """The receipt's key set is exactly the five pinned keys: an unknown extra key — even
    alongside five matching values — is unknown intake behavior and fails closed."""
    upload_descriptor = descriptor(columns=(('value', 'text', 'string'),), include_schema=True)
    body = rq_contract.descriptor_request_bytes(upload_descriptor)
    receipt = descriptor_receipt(body)
    rq_upload.verify_descriptor_response(receipt, 'upload-1', upload_descriptor, body)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        # The legacy provisional echo key is exactly the kind of drift the pinned set rejects.
        rq_upload.verify_descriptor_response(
            {**receipt, 'descriptor_sha256': hashlib.sha256(body).hexdigest()},
            'upload-1',
            upload_descriptor,
            body,
        )
    assert failure.value.code == 'invalid_receipt'


def test_descriptor_receipt_rejects_a_non_object_response():
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.verify_descriptor_response(None, 'upload-1', descriptor(), b'{}')
    assert failure.value.code == 'invalid_receipt'


def test_finalize_totals_are_required_and_authoritative():
    assert rq_upload.finalize_totals({'page_count': 1, 'total_rows': 2, 'total_bytes': 3}) == (1, 2, 3)
    for missing in ({}, {'page_count': 1}, {'page_count': 1, 'total_rows': 2}):
        with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
            rq_upload.finalize_totals(missing)
        assert failure.value.code == 'invalid_receipt'
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.finalize_totals({'page_count': '1', 'total_rows': 0, 'total_bytes': 0})
    assert failure.value.code == 'invalid_receipt'
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.finalize_totals({'page_count': -1, 'total_rows': 0, 'total_bytes': 0})
    assert failure.value.code == 'invalid_receipt'


def test_http_descriptor_registration_replays_the_identical_body(monkeypatch, creds):
    import requests

    calls = []
    body = rq_contract.descriptor_request_bytes(descriptor())

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data))
        if len(calls) == 1:
            raise requests.exceptions.ConnectionError('response lost')
        return SimpleNamespace(status_code=200, content=json.dumps({'upload_id': creds.upload_id}).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    assert rq_upload.RequestsUploadClient().register_descriptor(creds, body) == {'upload_id': 'upload-1'}
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('POST', 'https://intake.example/uploads/upload-1/descriptor', body)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'dd-application-key': 'test-app-key',
        'Content-Type': 'application/json',
    }


@pytest.mark.parametrize('trigger', ['lost_response', 'unavailable'])
def test_http_source_page_retry_replays_exact_body_and_headers(monkeypatch, creds, trigger):
    import requests

    calls = []
    payload = b'null,"""x"""\n'
    page = source_page(payload, batch_index=2)

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data.read()))
        if len(calls) == 1:
            if trigger == 'lost_response':
                raise requests.exceptions.ConnectionError('response lost')
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        return SimpleNamespace(status_code=202, content=json.dumps(acceptance_receipt(2, 7, 1)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    client = rq_upload.RequestsUploadClient()
    with io.BytesIO(payload) as body:
        receipt = client.put_source_page(creds, page, body)
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('PUT', 'https://intake.example/uploads/upload-1/pages/2', payload)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'dd-application-key': 'test-app-key',
        'Content-Type': 'application/vnd.datadog.remote-query.rows+csv;version=1',
        'Content-Length': str(len(payload)),
        'X-DD-Source-Page-Bytes': str(len(payload)),
        'X-DD-Source-Page-Rows': '1',
        'X-DD-Record-Offset': '7',
    }
    # HTTP 202 is the successful page handoff: the client returns the acceptance receipt
    # untouched — no final page metadata exists to synthesize.
    assert receipt == acceptance_receipt(2, 7, 1)


def test_http_page_handoff_requires_http_202(monkeypatch, creds):
    """The pinned page handoff is HTTP 202 exactly: an HTTP 200 carrying an otherwise-valid
    acceptance receipt is not the acceptance contract and fails closed, so a non-202
    success can never advance the producer on an unverified handoff."""
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(1)
        return SimpleNamespace(status_code=200, content=json.dumps(acceptance_receipt(0, 7, 1)).encode())

    monkeypatch.setattr(requests, 'request', request)
    page = source_page(b'x')
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(b'x') as body:
        rq_upload.RequestsUploadClient().put_source_page(creds, page, body)
    assert failure.value.code == 'invalid_receipt'
    assert not failure.value.retryable
    # The wrong-status success fails on its own response; it is not retried.
    assert len(calls) == 1


def test_http_final_page_too_large_surfaces_as_its_own_code(monkeypatch, creds):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(
            status_code=413, content=b'{"error":{"code":"final_page_too_large","message":"too large"}}'
        )

    monkeypatch.setattr(requests, 'request', request)
    page = source_page(b'null\n')
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(b'null\n') as body:
        rq_upload.RequestsUploadClient().put_source_page(creds, page, body)
    assert failure.value.code == 'final_page_too_large'
    assert not failure.value.retryable
    assert len(calls) == 1  # terminal: the writer splits; the client never retries it


def test_http_terminal_rejections_on_default_mapping_requests_fail_closed(monkeypatch, creds):
    """Descriptor and finalize map no intake error codes: a terminal rejection on either
    must surface as upload_failed, never as an AttributeError from the missing mapping."""
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url))
        return SimpleNamespace(status_code=409, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    client = rq_upload.RequestsUploadClient()
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        client.register_descriptor(creds, b'{}')
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        client.finalize_run(creds, 0)
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert calls == [
        ('POST', 'https://intake.example/uploads/upload-1/descriptor'),
        ('POST', 'https://intake.example/uploads/upload-1/finalize'),
    ]


@pytest.mark.parametrize('status', [400, 403, 409])
def test_http_terminal_rejections_are_not_retried(monkeypatch, creds, status):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(status_code=status, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    page = source_page(b'x')
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(b'x') as body:
        rq_upload.RequestsUploadClient().put_source_page(creds, page, body)
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert len(calls) == 1


def test_http_page_attempt_bound_kills_slow_attempts(monkeypatch, creds):
    import requests

    payload = b'null\n'
    page = source_page(payload, record_offset=0)
    attempts = []
    sent = []
    clock = {'now': 0.0}

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        if len(attempts) == 1:
            clock['now'] += 56
        sent.append(data.read())
        return SimpleNamespace(status_code=202, content=json.dumps(acceptance_receipt(0, 0, 1)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    # The wall is 100 s away, but the per-attempt bound is 55 s: the first attempt's body read
    # happens past it and is killed mid-body; the second, rewound attempt succeeds.
    monkeypatch.setattr(rq_timing.time, 'monotonic', lambda: clock['now'])
    wall_creds = rq_upload.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=100.0
    )
    with io.BytesIO(payload) as body:
        assert rq_upload.RequestsUploadClient().put_source_page(wall_creds, page, body) == acceptance_receipt(0, 0, 1)
    assert len(attempts) == 2
    # The killed attempt fails its deadline check before any byte leaves; only the rewound
    # second attempt streams the page.
    assert sent == [payload]


def test_http_page_attempt_bound_never_exceeds_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'null\n'
    page = source_page(payload, record_offset=0)
    attempts = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        data.read()
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    # The wall is 50 s away, inside the 55 s attempt bound, so the attempt's own deadline is
    # the wall: a partially consumed budget bounds the page attempt, the killed attempt is not
    # retried past the wall, and the run surfaces the retryable wall timeout.
    clock = iter([0.0, 0.0, 51.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq_timing.time, 'monotonic', lambda: next(clock))
    wall_creds = rq_upload.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=50.0
    )
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq_upload.RequestsUploadClient().put_source_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_http_retry_sequence_never_extends_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'null\n'
    page = source_page(payload, record_offset=0)
    attempts = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    # A transient rejection followed by an expired wall: the sequence refuses to start another
    # attempt and surfaces the retryable wall timeout instead of uploading past the wall.
    clock = iter([0.0, 0.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq_timing.time, 'monotonic', lambda: next(clock))
    wall_creds = rq_upload.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=50.0
    )
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq_upload.RequestsUploadClient().put_source_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_http_finalize_sends_the_accepted_page_count(monkeypatch, creds):
    import requests

    bodies = []

    def request(method, url, headers, data, timeout):
        bodies.append((method, data))
        return SimpleNamespace(status_code=200, content=json.dumps(finalize_receipt(3, 5, 99)).encode())

    monkeypatch.setattr(requests, 'request', request)
    assert rq_upload.RequestsUploadClient().finalize_run(creds, 3) == finalize_receipt(3, 5, 99)
    # The request body is exactly the accepted page count, nothing else.
    assert bodies == [('POST', b'{"expected_page_count":3}')]


def test_http_finalize_polls_pending_until_the_authoritative_receipt(monkeypatch, creds):
    import requests

    calls = []
    sleeps = []

    def request(method, url, headers, data, timeout):
        calls.append((method, data))
        if len(calls) == 1:
            return SimpleNamespace(status_code=202, content=json.dumps(pending_receipt(1, 3)).encode())
        if len(calls) == 2:
            # The completed count may advance between polls while pages are recorded.
            return SimpleNamespace(status_code=202, content=json.dumps(pending_receipt(3, 3)).encode())
        return SimpleNamespace(status_code=200, content=json.dumps(finalize_receipt(3, 5, 99)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', sleeps.append)
    scoped = rq_upload.UploadCredentials(
        creds.base_url,
        creds.upload_id,
        creds.api_key,
        creds.app_key,
        None,
        wall_deadline=rq_timing.time.monotonic() + 60,
    )
    assert rq_upload.RequestsUploadClient().finalize_run(scoped, 3) == finalize_receipt(3, 5, 99)
    # Every poll replays the identical finalize body under the same wall.
    assert calls == [('POST', b'{"expected_page_count":3}')] * 3
    assert sleeps == [
        rq_upload.REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS,
        2 * rq_upload.REMOTE_QUERY_UPLOAD_INITIAL_BACKOFF_SECONDS,
    ]


@pytest.mark.parametrize(
    'pending',
    [
        {'status': 'processing', 'completed_page_count': 1, 'expected_page_count': 2},  # wrong expected echo
        {'status': 'processing', 'completed_page_count': 4, 'expected_page_count': 3},  # beyond the expected count
        {'status': 'processing', 'completed_page_count': -1, 'expected_page_count': 3},
        {'status': 'processing', 'completed_page_count': True, 'expected_page_count': 3},
        {'status': 'processing', 'completed_page_count': 1, 'expected_page_count': '3'},
        {'status': 'accepted', 'completed_page_count': 1, 'expected_page_count': 3},  # not the pending status
        {'status': 'processing', 'completed_page_count': 1},  # missing the expected echo
        {'status': 'processing', 'completed_page_count': 1, 'expected_page_count': 3, 'upload_id': 'upload-1'},
        'not-an-object',
    ],
)
def test_http_finalize_pending_receipt_is_strictly_verified(monkeypatch, creds, pending):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(1)
        body = pending if isinstance(pending, str) else json.dumps(pending)
        return SimpleNamespace(status_code=202, content=body.encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    scoped = rq_upload.UploadCredentials(
        creds.base_url,
        creds.upload_id,
        creds.api_key,
        creds.app_key,
        None,
        wall_deadline=rq_timing.time.monotonic() + 60,
    )
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().finalize_run(scoped, 3)
    assert failure.value.code == 'invalid_receipt'
    # A malformed pending receipt fails closed on its own poll; nothing is retried.
    assert len(calls) == 1


def test_http_finalize_pending_backoff_is_bounded_under_the_run_wall(monkeypatch, creds):
    import requests

    attempts = []
    sleeps = []
    clock = {'now': 0.0}

    def request(method, url, headers, data, timeout):
        attempts.append(clock['now'])
        return SimpleNamespace(status_code=202, content=json.dumps(pending_receipt(0, 1)).encode())

    def sleep(seconds):
        sleeps.append(seconds)
        clock['now'] += seconds

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', sleep)
    monkeypatch.setattr(rq_timing.time, 'monotonic', lambda: clock['now'])
    scoped = rq_upload.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=25.0
    )
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().finalize_run(scoped, 1)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 10
    assert sleeps == [0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 5.0, 5.0, 5.0, 5.0]


def test_http_finalize_pending_then_terminal_rejection_fails_closed(monkeypatch, creds):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(1)
        if len(calls) == 1:
            return SimpleNamespace(status_code=202, content=json.dumps(pending_receipt(0, 1)).encode())
        return SimpleNamespace(status_code=409, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    scoped = rq_upload.UploadCredentials(
        creds.base_url,
        creds.upload_id,
        creds.api_key,
        creds.app_key,
        None,
        wall_deadline=rq_timing.time.monotonic() + 60,
    )
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().finalize_run(scoped, 1)
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert len(calls) == 2  # the terminal rejection is not retried; the run aborts


def test_trace_headers_reach_page_finalize_abort_and_retries_without_other_changes(monkeypatch, creds):
    import requests

    page = rq_contract.SourcePageUploadMetadata(0, 0, 1, 1)
    page_receipt = json.dumps(receipt(page)).encode()
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, dict(headers)))
        if method == 'PUT' and len(calls) == 1:
            # A transient rejection: the page PUT retries once with the same headers.
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        if method == 'PUT':
            return SimpleNamespace(status_code=202, content=page_receipt)
        return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    client = rq_upload.RequestsUploadClient()

    def drive(trace_context):
        calls.clear()
        scoped = rq_upload.UploadCredentials(
            creds.base_url, creds.upload_id, creds.api_key, creds.app_key, 'test-intake', trace_context=trace_context
        )
        with io.BytesIO(b'x') as body:
            client.put_source_page(scoped, page, body)
        client.finalize_run(scoped, 1)
        client.abort(scoped)
        return list(calls)

    plain_calls = drive(None)
    traced_calls = drive(
        rq_contract.RemoteQueryTraceContext.model_validate(
            {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}
        )
    )

    # The carrier reaches the page PUT (each attempt), finalize, and abort; the retried
    # page PUT replays the same tracing headers byte for byte.
    assert [(method, url) for method, url, _ in traced_calls] == [
        ('PUT', 'https://intake.example/uploads/upload-1/pages/0'),
        ('PUT', 'https://intake.example/uploads/upload-1/pages/0'),
        ('POST', 'https://intake.example/uploads/upload-1/finalize'),
        ('POST', 'https://intake.example/uploads/upload-1/abort'),
    ]
    assert traced_calls[0][2] == traced_calls[1][2]
    expected_trace_headers = {
        'x-datadog-trace-id': TRACE_ID,
        'x-datadog-parent-id': PARENT_ID,
        'x-datadog-sampling-priority': '2',
    }
    for (_, _, traced_headers), (_, _, plain_headers) in zip(traced_calls, plain_calls):
        # Exactly the three tracing headers differ from a context-free run: the auth,
        # integrity, content-length, and Test Drive headers are unchanged, and an absent
        # context preserves the request behavior byte for byte.
        assert traced_headers == {**plain_headers, **expected_trace_headers}


def test_page_upload_attempts_span_each_http_attempt_with_retry_and_outcome(monkeypatch, delivery, creds):
    import requests

    page = rq_contract.SourcePageUploadMetadata(0, 0, 1, 1)
    page_receipt = json.dumps(receipt(page)).encode()
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(dict(headers))
        if len(calls) == 1:
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        return SimpleNamespace(status_code=202, content=page_receipt)

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    tracing, tracer = make_tracing()
    tracing.open_root(delivery)
    timings = rq_timing.RemoteQueryProducerTimings(0.0)
    client = rq_upload.RequestsUploadClient(timings=timings, tracing=tracing)

    with io.BytesIO(b'x') as body:
        page_receipt = client.put_source_page(creds, page, body)

    tracing.succeed(rq_contract.RemoteQueryRunStats())
    tracing.close()

    assert page_receipt['status'] == 'accepted'
    first, second = tracer.by_name(rq_tracing.REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION)
    # The failed first attempt is a rejection with its public status counter; the retried
    # attempt succeeds and is marked as the page's second attempt.
    assert first.tags[rq_tracing.REMOTE_QUERY_SPAN_RETRY_TAG] == 'false'
    assert first.error == 1
    assert first.tags[rq_tracing.REMOTE_QUERY_SPAN_ERROR_TYPE_TAG] == 'rejected'
    assert first.metrics[rq_tracing.REMOTE_QUERY_SPAN_HTTP_STATUS_METRIC] == 503
    assert second.tags[rq_tracing.REMOTE_QUERY_SPAN_RETRY_TAG] == 'true'
    assert second.error == 0
    assert second.metrics[rq_tracing.REMOTE_QUERY_SPAN_HTTP_STATUS_METRIC] == 202
    assert [span.child_of for span in (first, second)] == [tracer.spans[0], tracer.spans[0]]
    # The root's attempt counters agree with the accumulator's upload accounting for the
    # same retries.
    root = tracer.spans[0]
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_ATTEMPT_COUNT_METRIC] == 2
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_RETRY_COUNT_METRIC] == 1
    accumulator = timings.metadata()['producer']
    assert accumulator['uploadAttemptCount'] == 2
    assert accumulator['uploadRetryCount'] == 1


def test_active_spans_replace_the_manual_trace_headers_only_on_spanned_requests(monkeypatch, delivery, creds):
    import requests

    traced = rq_upload.UploadCredentials(
        creds.base_url,
        creds.upload_id,
        creds.api_key,
        creds.app_key,
        None,
        trace_context=rq_contract.RemoteQueryTraceContext.model_validate(
            {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}
        ),
    )
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(dict(headers))
        if url.endswith('/pages/0'):
            page = rq_contract.SourcePageUploadMetadata(0, 0, 1, 1)
            return SimpleNamespace(status_code=202, content=json.dumps(receipt(page)).encode())
        if url.endswith('/finalize'):
            return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', request)
    tracing, tracer = make_tracing()
    tracing.open_root(delivery)
    client = rq_upload.RequestsUploadClient(tracing=tracing)

    # The descriptor registration carries no span, so its manual trace headers stand.
    client.register_descriptor(traced, b'{"format_version":"csv-json-cell-v1"}')
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_ID_HEADER] == TRACE_ID
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] == PARENT_ID
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER] == '2'

    # The page upload replaces the manual trio with the attempt span's own injected
    # context, while the authorization and declared-metadata headers ride unchanged.
    with io.BytesIO(b'x') as body:
        client.put_source_page(traced, rq_contract.SourcePageUploadMetadata(0, 0, 1, 1), body)
    [attempt] = tracer.by_name(rq_tracing.REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION)
    page_headers = calls[1]
    assert page_headers[rq_contract.REMOTE_QUERY_TRACE_ID_HEADER] == '222'
    assert page_headers[rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] == str(attempt.span_id)
    assert page_headers[rq_contract.REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER] == '1'
    assert page_headers['dd-api-key'] == 'test-api-key'
    assert page_headers['dd-application-key'] == 'test-app-key'
    assert page_headers['Content-Type'] == rq_upload.REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE

    # Finalize and abort inject their whole-call spans the same way.
    with tracing.finalize_span():
        client.finalize_run(traced, 1)
    with tracing.abort_span():
        client.abort(traced)
    [finalize_span] = tracer.by_name(rq_tracing.REMOTE_QUERY_FINALIZE_SPAN_OPERATION)
    [abort_span] = tracer.by_name(rq_tracing.REMOTE_QUERY_ABORT_SPAN_OPERATION)
    assert calls[2][rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] == str(finalize_span.span_id)
    assert calls[3][rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] == str(abort_span.span_id)


def test_injection_failure_falls_back_to_the_manual_trace_headers(monkeypatch, delivery, creds):
    import requests

    traced = rq_upload.UploadCredentials(
        creds.base_url,
        creds.upload_id,
        creds.api_key,
        creds.app_key,
        None,
        trace_context=rq_contract.RemoteQueryTraceContext.model_validate(
            {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}
        ),
    )
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(dict(headers))
        return SimpleNamespace(
            status_code=202, content=json.dumps(receipt(rq_contract.SourcePageUploadMetadata(0, 0, 1, 1))).encode()
        )

    monkeypatch.setattr(requests, 'request', request)
    tracing, tracer = make_tracing(propagator=RefusingPropagator())
    tracing.open_root(delivery)
    client = rq_upload.RequestsUploadClient(tracing=tracing)

    with io.BytesIO(b'x') as body:
        page_receipt = client.put_source_page(traced, rq_contract.SourcePageUploadMetadata(0, 0, 1, 1), body)

    # The propagator failed, so the request still carries the manual trace headers
    # verbatim — the no-tracer fallback — and the upload itself succeeded.
    assert page_receipt['status'] == 'accepted'
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_ID_HEADER] == TRACE_ID
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] == PARENT_ID
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER] == '2'
    # The span still finished with its outcome; only the injection fell back.
    [attempt] = tracer.by_name(rq_tracing.REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION)
    assert attempt.finished


@pytest.mark.parametrize('body', [b'', b'not-json', b'[]', b'null'])
def test_responses_require_json_objects(body):
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.parse_json_object_response(body, 'page upload')
    assert failure.value.code == 'invalid_receipt'


def test_finalize_identity_must_match():
    with pytest.raises(rq_contract.RemoteQueryFailure):
        rq_upload.verify_run_finalize_response({'upload_id': 'other'}, 'upload-1')


@pytest.mark.parametrize(
    'value,expected',
    [
        (' TEST-INTAKE ', 'test-intake'),
        (None, None),
        ('', None),
        ('-intake', None),
        ('a' * 64, None),
        ('x\r\nAuthorization: y', None),
    ],
)
def test_test_drive_name_cannot_inject_headers(value, expected):
    assert rq_upload.validate_test_drive_name(value) == expected


@pytest.mark.parametrize('trigger', ['transport', 'transient_status'])
def test_retry_exhausted_upload_failure_reports_only_safe_diagnostics(monkeypatch, creds, caplog, trigger):
    """The exhausted retry sequence stays retryable upload_failed, and its diagnostic is the
    fixed failure category or intake's HTTP status — never the caught transport exception,
    whose text carries the URL and request body."""
    import requests

    caplog.set_level(logging.DEBUG)

    def request(*args, **kwargs):
        if trigger == 'transport':
            raise requests.exceptions.ConnectionError('SECRET_DO_NOT_LOG while sending page bytes')
        return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().register_descriptor(creds, b'{}')
    assert failure.value.code == 'upload_failed'
    assert failure.value.retryable
    expected_detail = 'transport failure' if trigger == 'transport' else 'HTTP status 503'
    message = failure.value.message
    assert (
        'failed after {} attempts: {}'.format(rq_upload.REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, expected_detail) in message
    )
    assert 'SECRET_DO_NOT_LOG' not in message
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_abort_failures_log_fixed_text_only(monkeypatch, creds, caplog):
    """Both best-effort abort paths log fixed diagnostic text: the caught exception can
    quote the URL, the request body, or credentials embedded in its message."""
    import requests

    caplog.set_level(logging.DEBUG)

    def request(*args, **kwargs):
        raise requests.exceptions.ConnectionError('SECRET_DO_NOT_LOG while aborting')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq_timing.time, 'sleep', lambda _: None)
    rq_upload.RequestsUploadClient().abort(creds)  # best-effort: never raises

    class ExplodingClient:
        def abort(self, creds):
            raise RuntimeError('SECRET_DO_NOT_LOG while aborting')

    rq_upload.safe_abort(ExplodingClient(), creds)  # best-effort: never raises
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_invalid_test_drive_name_warning_omits_the_configured_value(caplog):
    assert rq_upload.validate_test_drive_name('INVALID_NAME_SECRET_DO_NOT_LOG') is None
    # The verdict and the grammar requirement stay in the warning; only the configured
    # value is dropped.
    assert 'Ignoring invalid remote query intake Test Drive name' in caplog.text
    assert 'lowercase ASCII alphanumerics' in caplog.text
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
