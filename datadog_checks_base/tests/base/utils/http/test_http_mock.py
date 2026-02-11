# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for HTTPResponseMock and RequestWrapperMock test helpers."""

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev.http import HTTPResponseMock, RequestWrapperMock
from datadog_checks.base.utils.http_protocol import (
    HTTPClientProtocol,
    HTTPResponseProtocol,
    HTTPSessionLike,
)


class TestHTTPResponseMock:
    """HTTPResponseMock satisfies HTTPResponseProtocol and has no requests/httpx dependency."""

    def test_satisfies_http_response_protocol(self):
        resp = HTTPResponseMock(200, content=b'ok')
        assert isinstance(resp, HTTPResponseProtocol)

    def test_content_and_status_code(self):
        resp = HTTPResponseMock(201, content=b'created')
        assert resp.content == b'created'
        assert resp.status_code == 201

    def test_headers(self):
        resp = HTTPResponseMock(200, headers={'X-Foo': 'bar'})
        assert resp.headers.get('X-Foo') == 'bar'

    def test_encoding_get_set(self):
        resp = HTTPResponseMock(200)
        resp.encoding = 'utf-8'
        assert resp.encoding == 'utf-8'

    def test_iter_content(self):
        resp = HTTPResponseMock(200, content=b'abc')
        chunks = list(resp.iter_content(chunk_size=1, decode_unicode=False))
        assert chunks == [b'a', b'b', b'c']

    def test_iter_lines(self):
        resp = HTTPResponseMock(200, content=b'line1\nline2\n')
        lines = list(resp.iter_lines(decode_unicode=False))
        assert lines == [b'line1', b'line2']

    def test_raise_for_status_ok(self):
        resp = HTTPResponseMock(200)
        resp.raise_for_status()

    def test_raise_for_status_4xx_raises(self):
        resp = HTTPResponseMock(404, content=b'Not Found')
        with pytest.raises(Exception) as exc_info:
            resp.raise_for_status()
        assert getattr(exc_info.value, 'response', None) is resp

    def test_close_no_op(self):
        resp = HTTPResponseMock(200)
        resp.close()

    def test_json_from_content(self):
        resp = HTTPResponseMock(200, content=b'{"a": 1}')
        assert resp.json() == {'a': 1}

    def test_json_from_json_data(self):
        resp = HTTPResponseMock(200, json_data={'b': 2})
        assert resp.json() == {'b': 2}


class TestRequestWrapperMock:
    """RequestWrapperMock implements HTTPClientProtocol and can patch check._http."""

    def test_satisfies_http_client_protocol(self):
        mock = RequestWrapperMock()
        assert isinstance(mock, HTTPClientProtocol)

    def test_session_satisfies_httpsession_like(self):
        mock = RequestWrapperMock()
        assert isinstance(mock.session, HTTPSessionLike)

    def test_get_returns_default_response_without_handler(self):
        mock = RequestWrapperMock()
        resp = mock.get('http://example.com/')
        assert isinstance(resp, HTTPResponseProtocol)
        assert resp.status_code == 200
        assert resp.content == b''

    def test_get_uses_handler_when_provided(self):
        custom = HTTPResponseMock(201, content=b'created')
        mock = RequestWrapperMock(get=lambda url, **kwargs: custom)
        resp = mock.get('http://example.com/')
        assert resp is custom
        assert resp.content == b'created'

    def test_post_uses_handler(self):
        custom = HTTPResponseMock(200, content=b'posted')
        mock = RequestWrapperMock(post=lambda url, **kwargs: custom)
        assert mock.post('http://example.com/').content == b'posted'

    def test_context_manager_patches_check_http(self):
        check = AgentCheck('test', {}, [{}])
        custom = HTTPResponseMock(200, content=b'mocked')
        with RequestWrapperMock(check, get=lambda url, **kwargs: custom):
            assert check._http is not None
            resp = check.http.get('http://example.com/')
            assert resp.content == b'mocked'
        # After exit, next access to .http should create real wrapper again
        assert not hasattr(check, '_http') or isinstance(check.http, RequestsWrapper)

    def test_context_manager_restores_previous_http(self):
        check = AgentCheck('test', {}, [{}])
        original = check.http
        mock = RequestWrapperMock(check)
        with mock:
            assert check._http is mock
        assert check._http is original
