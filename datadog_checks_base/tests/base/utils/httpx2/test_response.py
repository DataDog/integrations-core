# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from datetime import timedelta

import httpx2
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.httpx2 import DEFAULT_CHUNK_SIZE, HTTPX2ResponseAdapter, HTTPX2Wrapper


@pytest.mark.parametrize('status_code', [404, 500])
def test_response_raise_for_status_raises_on_error_codes(status_transport_factory, status_code):
    transport = status_transport_factory(status_code, b'')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_response_iter_content_bytes(status_transport_factory):
    transport = status_transport_factory(200, b'abcdef')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content(chunk_size=2))
    assert b''.join(chunks) == b'abcdef'


def test_response_iter_content_decode_unicode(status_transport_factory):
    transport = status_transport_factory(200, b'abcdef')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content(chunk_size=3, decode_unicode=True))
    assert ''.join(chunks) == 'abcdef'


@pytest.mark.parametrize(
    'decode_unicode,expected',
    [
        pytest.param(False, [b'a', b'b', b'c'], id='bytes'),
        pytest.param(True, ['a', 'b', 'c'], id='decoded-unicode'),
    ],
)
def test_response_iter_lines(status_transport_factory, decode_unicode, expected):
    transport = status_transport_factory(200, b'a\nb\nc')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert list(response.iter_lines(decode_unicode=decode_unicode)) == expected


def test_response_iter_content_empty_body_yields_nothing(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert list(response.iter_content()) == []


def test_response_iter_content_default_chunk_size_uses_default(status_transport_factory):
    body = b'X' * (DEFAULT_CHUNK_SIZE * 3 + 5)
    transport = status_transport_factory(200, body)
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content())
    assert b''.join(chunks) == body
    assert all(len(chunk) <= DEFAULT_CHUNK_SIZE for chunk in chunks)
    assert any(len(chunk) == DEFAULT_CHUNK_SIZE for chunk in chunks)


@pytest.mark.parametrize(
    'charset,raw,expected',
    [
        pytest.param('utf-8', 'café'.encode('utf-8'), 'café', id='utf-8'),
        pytest.param('iso-8859-1', 'café'.encode('iso-8859-1'), 'café', id='iso-8859-1'),
    ],
)
def test_response_iter_content_decode_uses_response_encoding(charset, raw, expected):
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=raw, headers={'Content-Type': f'text/plain; charset={charset}'})

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    chunks = list(response.iter_content(chunk_size=64, decode_unicode=True))
    assert ''.join(chunks) == expected


@pytest.mark.parametrize(
    'charset,line',
    [
        pytest.param('utf-8', 'café', id='utf-8'),
        pytest.param('iso-8859-1', 'café', id='iso-8859-1'),
    ],
)
def test_response_iter_lines_decode_uses_response_encoding(charset, line):
    raw = (line + '\n' + line).encode(charset)

    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=raw, headers={'Content-Type': f'text/plain; charset={charset}'})

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    encoded_lines = list(response.iter_lines(decode_unicode=False))
    assert encoded_lines == [line.encode(charset), line.encode(charset)]


def test_response_iter_lines_bytes_through_invalid_sequences():
    raw = b'invalid\xff\xfe\nsecond\n'

    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=raw, headers={'Content-Type': 'text/plain; charset=utf-8'})

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    assert list(response.iter_lines(decode_unicode=False)) == [b'invalid\xff\xfe', b'second']


def test_response_iter_lines_bytes_through_crlf(status_transport_factory):
    transport = status_transport_factory(200, b'a\r\nb\r\nc')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert list(response.iter_lines(decode_unicode=False)) == [b'a', b'b', b'c']


def test_response_iter_lines_rejects_delimiter(status_transport_factory):
    transport = status_transport_factory(200, b'a\nb\n')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(NotImplementedError):
        list(response.iter_lines(delimiter=b'|'))


def test_response_elapsed_returns_zero_on_runtime_error(caplog):
    # httpx2's .elapsed raises RuntimeError for in-memory responses. The real httpx2.Request is
    # attached so the adapter's debug log can format request info without a secondary error.
    request = httpx2.Request('GET', 'http://example.test/')
    response = httpx2.Response(200, content=b'x', request=request)
    adapter = HTTPX2ResponseAdapter(response)
    with caplog.at_level(logging.DEBUG, logger='datadog_checks.base.utils.httpx2'):
        assert adapter.elapsed == timedelta(0)
    assert any('elapsed unavailable' in record.message for record in caplog.records)


@pytest.mark.parametrize('status_code,expected_ok', [(200, True), (204, True), (301, True), (400, False), (500, False)])
def test_response_ok_property(status_transport_factory, status_code, expected_ok):
    transport = status_transport_factory(status_code, b'')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.ok is expected_ok


def test_response_reason_from_httpx_response(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.reason == 'OK'


def test_response_text_decodes_body(status_transport_factory):
    transport = status_transport_factory(200, b'hello')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.text == 'hello'


def test_response_json_returns_decoded_object():
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, json={'a': 1})

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.json() == {'a': 1}


def test_response_content_returns_raw_bytes(status_transport_factory):
    transport = status_transport_factory(200, b'\x00\x01\x02')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.content == b'\x00\x01\x02'


def test_response_headers_exposed():
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers={'X-Custom': 'value'}, content=b'')

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.headers['X-Custom'] == 'value'


def test_response_url_reflects_request_url(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPX2Wrapper({}, {}, transport=transport)
    response = http.get('http://example.test/path')
    assert str(response.url) == 'http://example.test/path'


def test_response_encoding_property_reflects_declared_charset():
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b'data', headers={'Content-Type': 'text/plain; charset=iso-8859-1'})

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.encoding == 'iso-8859-1'


def test_response_encoding_property_settable_through_adapter():
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, content=b'data', headers={'Content-Type': 'text/plain; charset=utf-8'})

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    response.encoding = 'iso-8859-1'
    assert response.encoding == 'iso-8859-1'


def test_response_cookies_exposed():
    def handler(_request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(200, headers={'Set-Cookie': 'session=abc123'}, content=b'')

    http = HTTPX2Wrapper({}, {}, transport=httpx2.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.cookies['session'] == 'abc123'
