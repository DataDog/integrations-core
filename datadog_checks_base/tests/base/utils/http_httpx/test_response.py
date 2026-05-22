# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_httpx import HTTPXWrapper


def test_response_content_bytes(status_transport_factory):
    transport = status_transport_factory(200, b'hello world')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.content == b'hello world'


def test_response_text(status_transport_factory):
    transport = status_transport_factory(200, 'hello')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.text == 'hello'


def test_response_status_code(status_transport_factory):
    transport = status_transport_factory(204, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.status_code == 204


def test_response_json(json_transport_factory):
    transport = json_transport_factory({'a': 1, 'b': [1, 2, 3]})
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.json() == {'a': 1, 'b': [1, 2, 3]}


def test_response_headers_case_insensitive():
    def handler(_request):
        return httpx.Response(200, headers={'X-Custom': 'foo', 'Content-Type': 'text/plain'})

    transport = httpx.MockTransport(handler)
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.headers['x-custom'] == 'foo'
    assert response.headers['X-CUSTOM'] == 'foo'
    assert response.headers['content-type'] == 'text/plain'


def test_response_raise_for_status_4xx(status_transport_factory):
    transport = status_transport_factory(404, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_response_raise_for_status_5xx(status_transport_factory):
    transport = status_transport_factory(500, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    with pytest.raises(HTTPStatusError):
        response.raise_for_status()


def test_response_iter_content(status_transport_factory):
    transport = status_transport_factory(200, b'abcdef')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content(chunk_size=2))
    assert b''.join(chunks) == b'abcdef'


def test_response_iter_lines_bytes_default(status_transport_factory):
    transport = status_transport_factory(200, b'a\nb\nc')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    lines = list(response.iter_lines())
    assert lines == [b'a', b'b', b'c']


def test_response_iter_lines_decode_unicode(status_transport_factory):
    transport = status_transport_factory(200, b'a\nb\nc')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    lines = list(response.iter_lines(decode_unicode=True))
    assert lines == ['a', 'b', 'c']


def test_response_encoding(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.encoding is not None


def test_response_url(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/path?x=1')
    assert 'example.test' in str(response.url)


def test_response_cookies_empty_by_default(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.cookies is not None


def test_response_elapsed(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.elapsed is not None


def test_response_close(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    response.close()


def test_response_ok_property(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.ok is True

    transport = status_transport_factory(500, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.ok is False
