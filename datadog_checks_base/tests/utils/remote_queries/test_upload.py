# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import io
import json
import logging
import socket
import socketserver
import threading
import time
from types import SimpleNamespace
from typing import Any

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing
from datadog_checks.base.utils.remote_queries import upload as rq_upload

from .helpers import (
    PARENT_ID,
    TRACE_ID,
    RefusingPropagator,
    as_session_request,
    descriptor,
    make_tracing,
    source_page,
)


def test_upload_credentials_are_api_key_only(monkeypatch, delivery):
    """Agents upload with the API key alone: the application key is never read, even when
    configured, and no request carries a dd-application-key header."""
    reads = []

    def get_config(key):
        reads.append(key)
        return {'api_key': 'test-api-key', 'app_key': 'SHOULD_NOT_BE_READ', 'site': 'intake.example'}.get(key)

    monkeypatch.setattr(rq_upload.datadog_agent, 'get_config', get_config)
    resolved = rq_upload.resolve_upload_credentials(delivery, 0.0)
    assert resolved.api_key == 'test-api-key'
    assert 'app_key' not in reads
    assert not hasattr(resolved, 'app_key')
    headers = rq_upload.RequestsUploadClient()._headers(resolved, 'application/json')
    assert headers == {'dd-api-key': 'test-api-key', 'Content-Type': 'application/json'}


@pytest.mark.parametrize(
    'base_url',
    [
        'https://intake.example',
        'https://intake.example/',
        'https://dd.intake.example/api/unstable/its-agent-intake',
        'https://INTAKE.example:443/api/unstable/its-agent-intake/',
    ],
)
def test_intake_base_url_on_the_agent_site_is_accepted(base_url):
    rq_upload.validate_intake_base_url(base_url, 'intake.example')


@pytest.mark.parametrize(
    'base_url',
    [
        'http://intake.example/api',  # not https
        'https://evil.example/api',
        'https://intake.example.evil.example/api',  # site as a prefix label
        'https://evilintake.example/api',  # site as a bare string suffix
        'https://evil.example/intake.example',
        'https://intake.example@evil.example/api',  # userinfo
        'https://user:pass@intake.example/api',
        'https://intake.example\\@evil.example/api',
        'https://intake.example:8443/api',
        'https://intake.example:/api',
        'https://intake.example./api',
        'https://intake.example/api?next=https://evil.example',
        'https://intake.example/api#frag',
        'https://intake.example/../api',
        'https://intake.example/api/./x',
        'https://intake.example/%2e%2e/api',
        'https://intake.example//api',
        'https://intake.example/a b',
        'https://intake.example/api\n',
        'https://[::1]/api',
        'https://127.0.0.1/api',
        'https://intake.example/' + 'a' * 2048,
        'intake.example/api',
        '',
    ],
)
def test_hostile_intake_base_url_is_rejected_without_being_echoed(base_url):
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.validate_intake_base_url(base_url, 'intake.example')
    assert failure.value.code == 'invalid_request'
    assert 'evil' not in failure.value.message


@pytest.mark.parametrize('site', [None, '', '   ', 'localhost', 'evil.example/path', 'a b.example'])
def test_intake_base_url_fails_closed_without_a_usable_agent_site(site):
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.validate_intake_base_url('https://intake.example/api', site)
    assert failure.value.code == 'invalid_request'


def test_the_api_key_is_not_read_for_an_off_site_base_url(monkeypatch, delivery):
    """The base URL is checked before the API key is even fetched from the Agent config."""
    reads = []

    def get_config(key):
        reads.append(key)
        return {'api_key': 'test-api-key', 'site': 'datadoghq.com'}.get(key)

    monkeypatch.setattr(rq_upload.datadog_agent, 'get_config', get_config)
    with pytest.raises(rq_contract.RemoteQueryFailure):
        rq_upload.resolve_upload_credentials(delivery, 0.0)
    assert 'api_key' not in reads


def test_http_descriptor_registration_replays_the_identical_body(monkeypatch, creds):
    import requests

    calls = []
    body = rq_contract.descriptor_request_bytes(descriptor())

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data))
        if len(calls) == 1:
            raise requests.exceptions.ConnectionError('response lost')
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    assert rq_upload.RequestsUploadClient().register_descriptor(creds, body) is None
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('POST', 'https://intake.example/uploads/upload-1/descriptor', body)
    assert headers == {
        'dd-api-key': 'test-api-key',
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
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    client = rq_upload.RequestsUploadClient()
    with io.BytesIO(payload) as body:
        client.put_source_page(creds, page, body)
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('PUT', 'https://intake.example/uploads/upload-1/pages/2', payload)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'Content-Type': 'text/csv',
        'Content-Length': str(len(payload)),
        'X-DD-Source-Page-Rows': '1',
        'X-DD-Record-Offset': '7',
    }


def test_http_result_file_too_large_surfaces_as_its_own_code(monkeypatch, creds):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(
            status_code=413, content=b'{"error":{"code":"result_file_too_large","message":"too large"}}'
        )

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    page = source_page(b'null\n')
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(b'null\n') as body:
        rq_upload.RequestsUploadClient().put_source_page(creds, page, body)
    assert failure.value.code == 'result_file_too_large'
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

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
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


@pytest.mark.parametrize(
    'status,code,retryable',
    [
        (400, 'invalid_argument', False),
        (401, 'unauthenticated', False),
        (404, 'not_found', False),
        (409, 'already_exists', False),
        (409, 'failed_precondition', False),
        (410, 'gone', False),
        (413, 'payload_too_large', False),
        (422, 'scan_failed', False),
        (422, 'storage_access_denied', False),
        (500, 'internal', True),
        (503, 'unavailable', True),
    ],
)
def test_intake_error_retry_classification(
    monkeypatch: pytest.MonkeyPatch, creds: rq_upload.UploadCredentials, status: int, code: str, retryable: bool
):
    # Retrying permanent intake errors wastes the run budget; transient intake errors
    # must instead replay the request, with only the public code in diagnostics.
    import requests

    calls = []

    def request(*args: Any, **kwargs: Any) -> SimpleNamespace:
        calls.append(1)
        return SimpleNamespace(
            status_code=status, content=json.dumps({'error': {'code': code, 'message': 'rejected'}}).encode()
        )

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().register_descriptor(creds, b'{}')
    assert failure.value.code == 'upload_failed'
    assert failure.value.retryable is retryable
    assert len(calls) == (5 if retryable else 1)
    if not retryable:
        assert code in failure.value.message


def test_unavailable_retries_until_the_run_wall_with_bounded_jitter(
    monkeypatch: pytest.MonkeyPatch, creds: rq_upload.UploadCredentials
):
    # A busy intake can stay at capacity beyond five attempts; treating its 503 as
    # permanent exhaustion would fail otherwise valid long-running queries.
    import requests

    attempts = []
    delays = []
    clock = {'now': 0.0}

    def request(*args: Any, **kwargs: Any) -> SimpleNamespace:
        attempts.append(1)
        if len(attempts) <= 8:
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable","message":"retry"}}')
        return SimpleNamespace(status_code=204, content=b'')

    def wait(delay: float) -> None:
        delays.append(delay)
        clock['now'] += delay

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'monotonic', lambda: clock['now'])
    monkeypatch.setattr(rq_upload.time, 'sleep', wait)
    monkeypatch.setattr(rq_upload.random, 'uniform', lambda low, high: (low + high) / 2)
    scoped = rq_upload.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, None, wall_deadline=100.0)
    rq_upload.RequestsUploadClient().register_descriptor(scoped, b'{}')
    assert len(attempts) == 9
    assert delays == [0.75 * min(0.1 * 2**i, 5.0) for i in range(8)]


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
            clock['now'] += 361
        sent.append(data.read())
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    # The wall is 1000 s away, but the per-attempt bound is 360 s: the first attempt's body read
    # happens past it and is killed mid-body; the second, rewound attempt succeeds.
    monkeypatch.setattr(rq_upload.time, 'monotonic', lambda: clock['now'])
    wall_creds = rq_upload.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, None, wall_deadline=1000.0)
    with io.BytesIO(payload) as body:
        assert rq_upload.RequestsUploadClient().put_source_page(wall_creds, page, body) is None
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

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    # The wall is 50 s away, inside the 360 s attempt bound, so the attempt's own deadline is
    # the wall: a partially consumed budget bounds the page attempt, the killed attempt is not
    # retried past the wall, and the run surfaces the retryable wall timeout.
    clock = iter([0.0, 0.0, 51.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq_upload.time, 'monotonic', lambda: next(clock))
    wall_creds = rq_upload.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, None, wall_deadline=50.0)
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

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    # A transient rejection followed by an expired wall: the sequence refuses to start another
    # attempt and surfaces the retryable wall timeout instead of uploading past the wall.
    clock = iter([0.0, 0.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq_upload.time, 'monotonic', lambda: next(clock))
    wall_creds = rq_upload.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, None, wall_deadline=50.0)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq_upload.RequestsUploadClient().put_source_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_http_finalize_sends_the_recorded_page_count(monkeypatch, creds):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, data))
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    rq_upload.RequestsUploadClient().finalize_run(creds, 3)
    assert calls == [('POST', 'https://intake.example/uploads/upload-1/finalize', b'{"expected_page_count":3}')]


def test_trace_headers_reach_page_finalize_abort_and_retries_without_other_changes(monkeypatch, creds):
    import requests

    page = rq_contract.SourcePageUploadMetadata(0, 0, 1, 1)
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, dict(headers)))
        if method == 'PUT' and len(calls) == 1:
            # A transient rejection: the page PUT retries once with the same headers.
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        if method == 'PUT':
            return SimpleNamespace(status_code=204, content=b'')
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    client = rq_upload.RequestsUploadClient()

    def drive(trace_context):
        calls.clear()
        scoped = rq_upload.UploadCredentials(
            creds.base_url, creds.upload_id, creds.api_key, 'test-intake', trace_context=trace_context
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
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(dict(headers))
        if len(calls) == 1:
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    tracing, tracer = make_tracing()
    tracing.open_root(delivery)
    client = rq_upload.RequestsUploadClient(tracing=tracing)

    with io.BytesIO(b'x') as body:
        client.put_source_page(creds, page, body)

    tracing.succeed(rq_contract.RemoteQueryRunStats())
    tracing.close()

    first, second = tracer.by_name(rq_tracing.REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION)
    # The failed first attempt is a rejection with its public status counter; the retried
    # attempt succeeds and is marked as the page's second attempt.
    assert first.tags[rq_tracing.REMOTE_QUERY_SPAN_RETRY_TAG] == 'false'
    assert first.error == 1
    assert first.tags[rq_tracing.REMOTE_QUERY_SPAN_ERROR_TYPE_TAG] == 'rejected'
    assert first.metrics[rq_tracing.REMOTE_QUERY_SPAN_HTTP_STATUS_METRIC] == 503
    assert second.tags[rq_tracing.REMOTE_QUERY_SPAN_RETRY_TAG] == 'true'
    assert second.error == 0
    assert second.metrics[rq_tracing.REMOTE_QUERY_SPAN_HTTP_STATUS_METRIC] == 204
    assert [span.child_of for span in (first, second)] == [tracer.spans[0], tracer.spans[0]]
    # The root's attempt counters count each HTTP page upload attempt exactly once, a
    # retry being any attempt beyond a page's first.
    root = tracer.spans[0]
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_ATTEMPT_COUNT_METRIC] == 2
    assert root.metrics[rq_tracing.REMOTE_QUERY_SPAN_UPLOAD_RETRY_COUNT_METRIC] == 1


def test_active_spans_replace_the_manual_trace_headers_only_on_spanned_requests(monkeypatch, delivery, creds):
    import requests

    traced = rq_upload.UploadCredentials(
        creds.base_url,
        creds.upload_id,
        creds.api_key,
        None,
        trace_context=rq_contract.RemoteQueryTraceContext.model_validate(
            {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}
        ),
    )
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(dict(headers))
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
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
    assert 'dd-application-key' not in page_headers
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
        None,
        trace_context=rq_contract.RemoteQueryTraceContext.model_validate(
            {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}
        ),
    )
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(dict(headers))
        return SimpleNamespace(status_code=204, content=b'')

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    tracing, tracer = make_tracing(propagator=RefusingPropagator())
    tracing.open_root(delivery)
    client = rq_upload.RequestsUploadClient(tracing=tracing)

    with io.BytesIO(b'x') as body:
        client.put_source_page(traced, rq_contract.SourcePageUploadMetadata(0, 0, 1, 1), body)

    # The propagator failed, so the request still carries the manual trace headers
    # verbatim — the no-tracer fallback — and the upload itself succeeded.
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_ID_HEADER] == TRACE_ID
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_PARENT_ID_HEADER] == PARENT_ID
    assert calls[0][rq_contract.REMOTE_QUERY_TRACE_SAMPLING_PRIORITY_HEADER] == '2'
    # The span still finished with its outcome; only the injection fell back.
    [attempt] = tracer.by_name(rq_tracing.REMOTE_QUERY_PAGE_UPLOAD_SPAN_OPERATION)
    assert attempt.finished


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

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
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

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
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


class StallingIntake:
    """A local HTTP server that reads a page's first bytes, stalls, then drains and answers.

    Unlike the patched-request tests, this drives real sockets, so it exercises which timeout
    urllib3 leaves on the socket while the request body is written.
    """

    FIRST_READ_BYTES = 64 * 1024

    def __init__(self, stall_seconds):
        self.stall_seconds = stall_seconds
        self.connections = 0
        self.released = threading.Event()
        intake = self

        class Handler(socketserver.BaseRequestHandler):
            def handle(self):
                intake.connections += 1
                try:
                    intake.serve(self.request)
                except OSError:
                    pass  # the client gave up and closed the connection

        class Server(socketserver.ThreadingTCPServer):
            daemon_threads = True
            allow_reuse_address = True

            def server_bind(self):
                # A small receive buffer makes the client's send block as soon as intake
                # stops reading, instead of the kernel absorbing the whole page.
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
                super().server_bind()

        self.server = Server(('127.0.0.1', 0), Handler)
        self.base_url = 'http://127.0.0.1:{}'.format(self.server.server_address[1])

    def serve(self, conn):
        buffered = b''
        while b'\r\n\r\n' not in buffered:
            chunk = conn.recv(65536)
            if not chunk:
                return
            buffered += chunk
        head, _, body = buffered.partition(b'\r\n\r\n')
        length = next(
            int(line.split(b':', 1)[1]) for line in head.split(b'\r\n') if line.lower().startswith(b'content-length:')
        )
        received = len(body)
        while received < min(length, self.FIRST_READ_BYTES):
            received += len(conn.recv(65536))
        self.released.wait(self.stall_seconds)
        while received < length:
            chunk = conn.recv(65536)
            if not chunk:
                return
            received += len(chunk)
        conn.sendall(b'HTTP/1.1 204 No Content\r\nContent-Length: 0\r\nConnection: close\r\n\r\n')

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc_info):
        self.released.set()
        self.server.shutdown()
        self.server.server_close()


PAGE_PAYLOAD = b'x' * (8 * 1024 * 1024)


def put_page_to(intake, client, wall_deadline=None):
    creds = rq_upload.UploadCredentials(intake.base_url, 'upload-1', 'test-api-key', None, wall_deadline)
    with io.BytesIO(PAGE_PAYLOAD) as body:
        return client.put_source_page(creds, source_page(PAGE_PAYLOAD, record_offset=0), body)


def test_a_reader_that_stalls_longer_than_the_connect_timeout_does_not_fail_the_upload(monkeypatch):
    """Regression for slow-draining intake: urllib3 kept the 10 s connect timeout on the socket
    while the body was sent, so a reader that paused longer than that killed the attempt as a
    transport failure and the retries piled onto the same slow intake."""
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    with StallingIntake(stall_seconds=1.0) as intake:
        # The stall is 3x the connect timeout and well inside the write timeout.
        client = rq_upload.RequestsUploadClient(timeout=(0.3, 5), write_timeout=5)
        assert put_page_to(intake, client) is None
    assert intake.connections == 1


def test_a_reader_that_stalls_longer_than_the_write_timeout_fails_the_attempt(monkeypatch):
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    with StallingIntake(stall_seconds=30) as intake:
        client = rq_upload.RequestsUploadClient(timeout=(5, 5), write_timeout=0.3)
        with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
            put_page_to(intake, client)
    assert failure.value.code == 'upload_failed'
    assert failure.value.retryable
    assert 'transport failure' in str(failure.value)
    assert intake.connections == rq_upload.REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1


def test_a_stalled_send_never_outlives_the_page_attempt_deadline():
    with StallingIntake(stall_seconds=30) as intake:
        # The write timeout alone would allow 30 s; the run wall, and so the attempt, ends in 0.5 s.
        client = rq_upload.RequestsUploadClient(timeout=(5, 5), write_timeout=30)
        started = time.monotonic()
        with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
            put_page_to(intake, client, wall_deadline=started + 0.5)
        elapsed = time.monotonic() - started
    assert failure.value.code == 'timeout'
    assert elapsed < 5
