# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import timedelta

import pytest

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

    assert response.json(parse_float=str) is json_result
    assert list(response.iter_content(chunk_size=1, decode_unicode=True)) == [b'complete ', b'body']
    assert list(response.iter_lines(chunk_size=1, decode_unicode=True, delimiter='|')) == ['first', 'second']
    assert list(response) == [b'complete ', b'body']
    assert response.get_peer_cert(binary_form=True) == b'certificate'
    assert response.headers['x-test'] == 'value'


def test_fake_response_does_not_derive_results_from_content_or_headers():
    response = FakeHTTPResponse(
        content=b'{"items": []}\nsecond line',
        headers={
            'Content-Type': 'application/json; charset=utf-8',
            'Link': '<https://example.test/items?page=2>; rel=next',
        },
    )

    assert response.text == ''
    assert response.encoding is None
    assert response.links == {}
    assert list(response.iter_content()) == []
    assert list(response.iter_lines()) == []
    with pytest.raises(ValueError, match='No JSON result'):
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
