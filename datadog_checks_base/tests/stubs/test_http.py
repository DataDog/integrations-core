# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event, Lock
from typing import Any

import pytest

from datadog_checks.base.stubs import http as http_stub
from datadog_checks.base.stubs.http import FakeHTTPClient, FakeHTTPResponse, RecordedRequest
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError, HTTPClientTimeoutError


def test_fake_response_returns_only_configured_results():
    json_result = {'items': []}
    response = FakeHTTPResponse(
        status_code=202,
        content=b'complete body',
        text='configured text',
        headers={'X-Test': 'value'},
        json_result=json_result,
        content_chunks=(b'complete ', b'body'),
        lines=('first', 'second'),
        encoding='utf-8',
        elapsed=timedelta(seconds=2),
        cookies={'session': 'abc'},
        links={'next': {'url': 'https://example.test/items?page=2'}},
        url='https://example.test/items',
        reason='Accepted',
        peer_cert=b'certificate',
    )

    assert response.text == 'configured text'
    assert response.json(parse_float=str) is json_result
    assert list(response.iter_content(chunk_size=1, decode_unicode=True)) == [b'complete ', b'body']
    assert list(response.iter_lines(chunk_size=1, decode_unicode=True)) == ['first', 'second']
    assert list(response) == [b'complete ', b'body']
    assert response.get_peer_cert(binary_form=True) == b'certificate'
    assert response.headers['x-test'] == 'value'


@pytest.mark.parametrize(
    ('content', 'encoding', 'expected_text'),
    [
        (b'first line\nsecond line', None, 'first line\nsecond line'),
        (b'caf\xe9', 'latin-1', 'café'),
        (b'\xff\xfebinary', None, '\ufffd\ufffdbinary'),
    ],
)
def test_fake_response_derives_text_and_stream_results_from_content(
    content: bytes, encoding: str | None, expected_text: str
):
    response = FakeHTTPResponse(content=content, encoding=encoding)

    assert response.text == expected_text
    assert list(response.iter_content()) == [content]


@pytest.mark.parametrize(
    ('content', 'encoding', 'decode_unicode', 'expected_lines'),
    [
        pytest.param(b'caf\xe9\nsecond', 'latin-1', True, ['caf\xe9', 'second'], id='decoded with the encoding'),
        pytest.param(b'caf\xe9\nsecond', 'latin-1', False, [b'caf\xe9', b'second'], id='bytes unless decoding'),
        pytest.param(b'first\nsecond', None, True, [b'first', b'second'], id='bytes without an encoding'),
    ],
)
def test_fake_response_derives_lines_from_content(
    content: bytes, encoding: str | None, decode_unicode: bool, expected_lines: list[bytes | str]
):
    response = FakeHTTPResponse(content=content, encoding=encoding)

    assert list(response.iter_lines(decode_unicode=decode_unicode)) == expected_lines


def test_fake_response_decodes_lines_with_an_encoding_set_after_creation():
    response = FakeHTTPResponse(content=b'first\nsecond')
    response.encoding = 'utf-8'

    assert list(response.iter_lines(decode_unicode=True)) == ['first', 'second']


def test_fake_response_preserves_explicit_text_and_stream_results():
    response = FakeHTTPResponse(content=b'body', text='', content_chunks=(), lines=())

    assert response.text == ''
    assert list(response.iter_content()) == []
    assert list(response.iter_lines()) == []


def test_fake_response_does_not_derive_metadata_or_json_from_content_or_headers():
    response = FakeHTTPResponse(
        content=b'{"items": []}\nsecond line',
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'Link': '<https://example.test/items?page=2>; rel=next',
        },
    )

    assert response.encoding is None
    assert response.links == {}
    with pytest.raises(AssertionError, match='No JSON result'):
        response.json()


def test_fake_response_raises_configured_json_error():
    error = ValueError('invalid JSON')
    response = FakeHTTPResponse(json_error=error)

    with pytest.raises(ValueError) as exc_info:
        response.json()

    assert exc_info.value is error


def test_fake_response_raises_configured_status_error():
    error = HTTPClientStatusError('503 Service Unavailable')
    response = FakeHTTPResponse(status_code=503, status_error=error)

    with pytest.raises(HTTPClientStatusError) as exc_info:
        response.raise_for_status()

    assert exc_info.value is error
    assert error.response is response


@pytest.mark.parametrize(
    ('status_code', 'expected_message'),
    [
        (404, '404 Client Error'),
        (500, '500 Server Error'),
    ],
)
def test_fake_response_derives_status_error_from_status_code(status_code: int, expected_message: str):
    response = FakeHTTPResponse(status_code=status_code)

    with pytest.raises(HTTPClientStatusError, match=expected_message) as exc_info:
        response.raise_for_status()

    assert exc_info.value.response is response


@pytest.mark.parametrize(
    ('iter_method', 'response_options', 'first_result'),
    [
        pytest.param('iter_content', {'content_chunks': (b'first',)}, b'first', id='content'),
        pytest.param('iter_lines', {'lines': ('first',)}, 'first', id='lines'),
    ],
)
def test_fake_response_raises_configured_stream_error_after_results(iter_method, response_options, first_result):
    error = HTTPClientTimeoutError('timed out')
    response = FakeHTTPResponse(stream_error=error, **response_options)
    stream = getattr(response, iter_method)()

    assert next(stream) == first_result
    with pytest.raises(HTTPClientTimeoutError) as exc_info:
        next(stream)

    assert exc_info.value is error


def test_fake_client_matches_responses_and_records_requests():
    client = FakeHTTPClient()
    page_one = FakeHTTPResponse(status_code=202)
    page_two = FakeHTTPResponse(status_code=204)
    url = 'https://example.test/items'
    client.register_response('GET', url, page_two, match_options={'params': {'page': 2}})
    client.register_response('GET', url, page_one, match_options={'params': {'page': 1}})

    assert client.get(url, params={'page': 1}) is page_one
    assert client.get(url, params={'page': 2}) is page_two
    assert client.requests == [
        RecordedRequest(method='GET', url=url, options={'params': {'page': 1}}),
        RecordedRequest(method='GET', url=url, options={'params': {'page': 2}}),
    ]
    client.assert_all_responses_consumed()


def test_fake_client_returns_registered_responses_in_queue_order():
    client = FakeHTTPClient()
    first = FakeHTTPResponse(status_code=202)
    second = FakeHTTPResponse(status_code=204)
    url = 'https://example.test/items'
    client.register_response('GET', url, first)
    client.register_response('GET', url, second)

    assert client.get(url) is first
    assert client.get(url) is second
    client.assert_all_responses_consumed()


def test_fake_client_raises_registered_exception():
    client = FakeHTTPClient()
    error = HTTPClientTimeoutError('timed out')
    client.register_response('GET', 'https://example.test/items', error)

    with pytest.raises(HTTPClientTimeoutError) as exc_info:
        client.get('https://example.test/items')

    assert exc_info.value is error
    client.assert_all_responses_consumed()


def test_fake_client_reads_configured_cookies_and_falls_back_for_missing_names():
    client = FakeHTTPClient(cookies={'session': 'abc'})

    assert client.get_cookie('session') == 'abc'
    assert client.get_cookie('missing', 'fallback') == 'fallback'


@pytest.mark.parametrize(
    'bypass',
    [
        pytest.param(True, id='flag'),
        pytest.param(lambda url: url.startswith('https://internal.'), id='callable'),
    ],
)
def test_created_clients_follow_the_parent_proxy_bypass(bypass):
    parent = FakeHTTPClient()
    child = parent.create_client()

    parent.set_should_bypass_proxy(bypass)

    assert child.should_bypass_proxy('https://internal.example/') is True


def test_fake_client_reports_unmatched_request_and_pending_responses():
    client = FakeHTTPClient()
    client.register_response('POST', 'https://example.test/items', FakeHTTPResponse())

    with pytest.raises(AssertionError, match=r'No registered response matched GET https://example\.test/items'):
        client.get('https://example.test/items')

    with pytest.raises(AssertionError, match='1 registered response was not consumed'):
        client.assert_all_responses_consumed()


def test_fake_client_request_assertions():
    client = FakeHTTPClient()
    url = 'https://example.test/items'
    client.register_response('PUT', url, FakeHTTPResponse())
    client.put(url, json={'name': 'widget'})
    expected = RecordedRequest(method='PUT', url=url, options={'json': {'name': 'widget'}})

    client.assert_requests([expected])
    client.assert_has_request(expected)

    with pytest.raises(AssertionError, match='Expected recorded requests'):
        client.assert_requests([])

    with pytest.raises(AssertionError, match='No recorded request matched'):
        client.assert_has_request(RecordedRequest(method='GET', url=url))


def test_fake_client_records_each_request_when_the_caller_reuses_one_options_container():
    client = FakeHTTPClient()
    url = 'https://example.test/items'
    for _ in range(3):
        client.register_response('GET', url, FakeHTTPResponse())

    params = {'take': 30}
    for page in range(3):
        params['skip'] = page * 30
        client.get(url, params=params)

    client.assert_requests(
        [
            RecordedRequest('GET', url, {'params': {'take': 30, 'skip': 0}}),
            RecordedRequest('GET', url, {'params': {'take': 30, 'skip': 30}}),
            RecordedRequest('GET', url, {'params': {'take': 30, 'skip': 60}}),
        ]
    )


def test_fake_client_matches_registrations_made_before_a_match_option_changed():
    client = FakeHTTPClient()
    url = 'https://example.test/items'
    first = FakeHTTPResponse(status_code=201)
    second = FakeHTTPResponse(status_code=202)
    match_options = {'params': {'page': 1}}
    client.register_response('GET', url, first, match_options=match_options)
    match_options['params']['page'] = 2
    client.register_response('GET', url, second, match_options=match_options)

    assert client.get(url, params={'page': 1}) is first
    assert client.get(url, params={'page': 2}) is second
    client.assert_all_responses_consumed()


def test_fake_client_accepts_protocol_mapping_request_options():
    client = FakeHTTPClient()
    url = 'https://example.test/items'
    response = FakeHTTPResponse()
    headers = FakeHTTPResponse(headers={'X-Test': 'value'}).headers
    client.register_response('GET', url, response)

    assert client.get(url, headers=headers) is response
    client.assert_requests([RecordedRequest('GET', url, {'headers': {'X-Test': 'value'}})])


def test_fake_client_records_a_body_that_cannot_be_copied():
    client = FakeHTTPClient()
    url = 'https://example.test/upload'
    client.register_response('POST', url, FakeHTTPResponse())
    body = (chunk for chunk in (b'first', b'second'))

    client.post(url, data=body)

    assert client.requests[0].options['data'] is body


@pytest.fixture
def competing_operation(monkeypatch: pytest.MonkeyPatch) -> Event:
    progressed = Event()

    class ObservedLock:
        """Let the scheduler distinguish a blocked contender from a finished one."""

        def __init__(self) -> None:
            self.lock = Lock()

        def __enter__(self) -> None:
            if not self.lock.acquire(blocking=False):
                progressed.set()
                assert self.lock.acquire(timeout=5), 'Timed out acquiring the shared fake lock'

        def __exit__(self, *exc_info: object) -> None:
            self.lock.release()

    # This also runs against the unlocked implementation to demonstrate the regression.
    monkeypatch.setattr(http_stub, 'Lock', ObservedLock, raising=False)
    return progressed


@pytest.mark.parametrize('clients', ['same', 'child', 'descendant', 'siblings'])
@pytest.mark.parametrize('same_url', [False, True], ids=['distinct-urls', 'match-options'])
@pytest.mark.parametrize('raises', [False, True], ids=['response', 'exception'])
def test_concurrent_fake_requests_keep_response_ownership(
    monkeypatch: pytest.MonkeyPatch, competing_operation: Event, clients: str, same_url: bool, raises: bool
):
    # Removing an earlier registration must not shift another worker's matched index (AI-7378).
    root = FakeHTTPClient()
    first_client = root.create_client() if clients == 'siblings' else root
    second_client = root
    if clients != 'same':
        second_client = root.create_client()
    if clients == 'descendant':
        second_client = second_client.create_client()
    urls = ['/items'] * 3 if same_url else ['/a', '/b', '/c']
    options = [{'params': {'id': i}} if same_url else {} for i in range(3)]
    outcomes = [FakeHTTPResponse(), HTTPClientTimeoutError('b') if raises else FakeHTTPResponse(), FakeHTTPResponse()]
    for url, outcome, match_options in zip(urls, outcomes, options):
        root.register_response('GET', url, outcome, match_options=match_options)

    matched = Event()
    release = Event()
    original_matches = FakeHTTPClient._matches

    def pause_matched_response(registered: Any, request: RecordedRequest) -> bool:
        matches = original_matches(registered, request)
        if matches and registered.outcome is outcomes[1]:
            matched.set()
            assert release.wait(5), 'Timed out releasing the matched request'
        return matches

    monkeypatch.setattr(FakeHTTPClient, '_matches', staticmethod(pause_matched_response))

    def consume_earlier_response() -> Any:
        try:
            return first_client.get(urls[0], **options[0])
        finally:
            competing_operation.set()

    with ThreadPoolExecutor(max_workers=2) as workers:
        second = workers.submit(second_client.get, urls[1], **options[1])
        try:
            assert matched.wait(5), 'Request never reached response matching'
            first = workers.submit(consume_earlier_response)
            assert competing_operation.wait(5), 'Competing request neither completed nor waited for the lock'
        finally:
            release.set()
        assert first.result(timeout=5) is outcomes[0]
        if raises:
            with pytest.raises(HTTPClientTimeoutError) as exc_info:
                second.result(timeout=5)
            assert exc_info.value is outcomes[1]
        else:
            assert second.result(timeout=5) is outcomes[1]

    # Requests for different resources need not have a predetermined global order.
    assert len(root.requests) == 2
    for url, request_options in zip(urls[:2], options[:2]):
        root.assert_has_request(RecordedRequest('GET', url, request_options))
    assert root.get(urls[2], **options[2]) is outcomes[2]
    root.assert_all_responses_consumed()
    with pytest.raises(AssertionError, match='No registered response matched'):
        root.get(urls[1], **options[1])


def test_concurrent_fake_requests_consume_a_registration_only_once(
    monkeypatch: pytest.MonkeyPatch, competing_operation: Event
):
    # Two callers of the same URL must see one response and one unmatched-request error.
    root = FakeHTTPClient()
    child = root.create_client()
    response = FakeHTTPResponse()
    root.register_response('GET', '/one', response)
    matched = Event()
    release = Event()
    original_matches = FakeHTTPClient._matches

    def pause_first_match(registered: Any, request: RecordedRequest) -> bool:
        matches = original_matches(registered, request)
        if matches and not matched.is_set():
            matched.set()
            assert release.wait(5), 'Timed out releasing the first request'
        return matches

    monkeypatch.setattr(FakeHTTPClient, '_matches', staticmethod(pause_first_match))

    def compete() -> Any:
        try:
            return child.get('/one')
        finally:
            competing_operation.set()

    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(root.get, '/one')
        try:
            assert matched.wait(5), 'Request never reached response matching'
            second = workers.submit(compete)
            assert competing_operation.wait(5), 'Competing request neither completed nor waited for the lock'
        finally:
            release.set()
        assert first.result(timeout=5) is response
        with pytest.raises(AssertionError, match='No registered response matched GET /one'):
            second.result(timeout=5)
    root.assert_requests([RecordedRequest('GET', '/one'), RecordedRequest('GET', '/one')])
    root.assert_all_responses_consumed()


def test_fake_consumption_assertion_waits_for_matching_to_finish(
    monkeypatch: pytest.MonkeyPatch, competing_operation: Event
):
    # A consumption assertion must not read a partially completed queue operation.
    root = FakeHTTPClient()
    child = root.create_client()
    root.register_response('GET', '/one', FakeHTTPResponse())
    matched = Event()
    release = Event()
    original_matches = FakeHTTPClient._matches

    def pause_match(registered: Any, request: RecordedRequest) -> bool:
        matches = original_matches(registered, request)
        matched.set()
        assert release.wait(5), 'Timed out releasing the request'
        return matches

    monkeypatch.setattr(FakeHTTPClient, '_matches', staticmethod(pause_match))

    def assert_consumed() -> None:
        try:
            child.assert_all_responses_consumed()
        finally:
            competing_operation.set()

    with ThreadPoolExecutor(max_workers=2) as workers:
        request = workers.submit(root.get, '/one')
        try:
            assert matched.wait(5), 'Request never reached response matching'
            assertion = workers.submit(assert_consumed)
            assert competing_operation.wait(5), 'Assertion neither completed nor waited for the lock'
        finally:
            release.set()
        request.result(timeout=5)
        assertion.result(timeout=5)


@pytest.mark.parametrize('processing', ['json', 'iter_lines'])
def test_fake_response_processing_does_not_block_other_clients(monkeypatch: pytest.MonkeyPatch, processing: str):
    # A listener reading an open stream must not prevent a sibling client from polling.
    root = FakeHTTPClient()
    listener = root.create_client()
    entered = Event()
    release = Event()
    response = FakeHTTPResponse()
    root.register_response('GET', '/stream', response)
    poll_response = FakeHTTPResponse()
    root.register_response('GET', '/poll', poll_response)

    def read_response() -> Iterator[bytes]:
        entered.set()
        assert release.wait(5), 'Timed out releasing response processing'
        yield b'body'

    monkeypatch.setattr(
        response, processing, read_response if processing == 'iter_lines' else lambda: list(read_response())
    )

    def consume() -> list[bytes]:
        with listener.get('/stream', stream=True) as stream:
            return list(getattr(stream, processing)())

    with ThreadPoolExecutor(max_workers=2) as workers:
        reading = workers.submit(consume)
        try:
            assert entered.wait(5), 'Response processing did not start'
            polling = workers.submit(root.get, '/poll')
            assert polling.result(timeout=5) is poll_response
        finally:
            release.set()
        assert reading.result(timeout=5) == [b'body']
    assert response.closed
    root.assert_all_responses_consumed()


class TestFakeHttpLegacyOptions:
    def test_header_views_share_storage(self):
        http = FakeHTTPClient()
        http.options['headers']['X-Token'] = 'abc'
        assert http.get_header('x-token') == 'abc'

        http.set_header('X-Other', 'def')
        assert http.options['headers']['X-Other'] == 'def'
