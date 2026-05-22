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


def test_response_iter_content_chunk_size_none(status_transport_factory):
    transport = status_transport_factory(200, b'hello')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content())
    assert chunks == [b'hello']


def test_response_iter_content_decode_unicode(status_transport_factory):
    transport = status_transport_factory(200, b'hello world')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    chunks = list(response.iter_content(chunk_size=3, decode_unicode=True))
    assert all(isinstance(c, str) for c in chunks)
    assert ''.join(chunks) == 'hello world'


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


def test_response_encoding_default_is_utf8(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    # httpx defaults to utf-8 when no charset is signalled. Pin the exact value
    # so a future httpx change that returns ``None`` here surfaces immediately.
    assert response.encoding == 'utf-8'


def test_response_encoding_setter_propagates_to_inner_response(status_transport_factory):
    """OM v2 scraper does ``response.encoding = 'utf-8'`` after the request."""
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    response.encoding = 'latin-1'
    assert response.encoding == 'latin-1'
    assert response._response.encoding == 'latin-1'


def test_response_url(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/path?x=1')
    assert str(response.url) == 'http://example.test/path?x=1'


def test_response_cookies_empty_by_default(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert len(response.cookies) == 0


def test_response_elapsed(status_transport_factory):
    from datetime import timedelta

    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert isinstance(response.elapsed, timedelta)


def test_response_elapsed_returns_zero_on_runtime_error(status_transport_factory):
    """Cover the RuntimeError fallback in HTTPXResponseAdapter.elapsed.

    httpx 0.28 raises ``RuntimeError`` from ``.elapsed`` until the bound stream's
    ``close()`` has finalized the timer. When MockTransport bypasses that path
    by serving buffered content, the adapter should return ``timedelta(0)`` so
    callers never see the RuntimeError.
    """
    from datetime import timedelta

    transport = status_transport_factory(200, b'hello')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    # Forge the MockTransport quirk explicitly: if ``_elapsed`` was set, drop it
    # so the property has to take the except branch.
    if hasattr(response._response, '_elapsed'):
        delattr(response._response, '_elapsed')
    assert response.elapsed == timedelta(0)


def test_response_close_marks_inner_response_closed(status_transport_factory):
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    response.close()
    assert response._response.is_closed is True


@pytest.mark.parametrize('status_code,expected_ok', [(200, True), (204, True), (301, True), (400, False), (500, False)])
def test_response_ok_property(status_transport_factory, status_code, expected_ok):
    transport = status_transport_factory(status_code, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.ok is expected_ok


def test_response_reason_from_httpx_response(status_transport_factory):
    """``reason`` reads from the underlying ``httpx.Response.reason_phrase``."""
    transport = status_transport_factory(200, b'')
    http = HTTPXWrapper({}, {}, transport=transport)
    response = http.get('http://example.test/')
    assert response.reason == 'OK'


def test_response_reason_falls_back_when_reason_phrase_missing():
    """Mock fixtures expose ``.reason``, not ``.reason_phrase`` — the adapter handles that."""
    from datadog_checks.base.utils.http_httpx import HTTPXResponseAdapter

    class _FakeResponseExposingReason:
        reason = 'Not Found'

    adapter = HTTPXResponseAdapter(_FakeResponseExposingReason())  # type: ignore[arg-type]
    assert adapter.reason == 'Not Found'
