# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import timedelta

import httpx
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_httpx import HTTPXResponseAdapter, HTTPXWrapper


@pytest.mark.parametrize('status_code', [404, 500])
def test_response_raise_for_status_raises_on_error_codes(status_transport_factory, status_code):
    transport = status_transport_factory(status_code, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_response_iter_content_bytes(status_transport_factory):
    transport = status_transport_factory(200, b'abcdef')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content(chunk_size=2))
    assert b''.join(chunks) == b'abcdef'


def test_response_iter_content_decode_unicode(status_transport_factory):
    transport = status_transport_factory(200, b'abcdef')
    http = HTTPXWrapper({}, {}, transport=transport)
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
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert list(response.iter_lines(decode_unicode=decode_unicode)) == expected


def test_response_iter_content_empty_body_yields_nothing(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert list(response.iter_content()) == []


def test_response_iter_lines_rejects_delimiter(status_transport_factory):
    transport = status_transport_factory(200, b'a\nb\n')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(NotImplementedError):
        list(response.iter_lines(delimiter=b'|'))


def test_response_elapsed_returns_zero_on_runtime_error():
    class _FakeResponse:
        @property
        def elapsed(self):
            raise RuntimeError('not measured')

    adapter = HTTPXResponseAdapter(_FakeResponse())  # type: ignore[arg-type]
    assert adapter.elapsed == timedelta(0)


@pytest.mark.parametrize('status_code,expected_ok', [(200, True), (204, True), (301, True), (400, False), (500, False)])
def test_response_ok_property(status_transport_factory, status_code, expected_ok):
    transport = status_transport_factory(status_code, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.ok is expected_ok


def test_response_reason_from_httpx_response(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.reason == 'OK'


def test_response_reason_falls_back_when_reason_phrase_missing():
    class _FakeResponseExposingReason:
        reason = 'Not Found'

    adapter = HTTPXResponseAdapter(_FakeResponseExposingReason())  # type: ignore[arg-type]
    assert adapter.reason == 'Not Found'


def test_response_text_decodes_body(status_transport_factory):
    transport = status_transport_factory(200, b'hello')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.text == 'hello'


def test_response_json_returns_decoded_object():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'a': 1})

    http = HTTPXWrapper({}, {}, transport=httpx.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.json() == {'a': 1}


def test_response_content_returns_raw_bytes(status_transport_factory):
    transport = status_transport_factory(200, b'\x00\x01\x02')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.content == b'\x00\x01\x02'


def test_response_headers_exposed():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={'X-Custom': 'value'}, content=b'')

    http = HTTPXWrapper({}, {}, transport=httpx.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.headers['X-Custom'] == 'value'


def test_response_url_reflects_request_url(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/path')
    assert str(response.url) == 'http://example.test/path'


def test_response_encoding_defaults_to_utf8(status_transport_factory):
    transport = status_transport_factory(200, b'hello')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.encoding in (None, 'utf-8', 'ascii')


def test_response_cookies_exposed():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={'Set-Cookie': 'session=abc123'}, content=b'')

    http = HTTPXWrapper({}, {}, transport=httpx.MockTransport(handler))
    response = http.get('http://example.test/')
    assert response.cookies['session'] == 'abc123'
