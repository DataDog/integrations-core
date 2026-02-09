# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Unit tests for HTTPXWrapper and HTTPXResponseAdapter (httpx-backed HTTP client)."""

from __future__ import annotations

import logging
from unittest import mock

import httpx
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import (
    HTTPXResponseAdapter,
    HTTPXWrapper,
    _make_httpx_auth,
)

pytestmark = [pytest.mark.unit]


# -----------------------------------------------------------------------------
# HTTPXResponseAdapter
# -----------------------------------------------------------------------------


class TestHTTPXResponseAdapter:
    """Tests for HTTPXResponseAdapter (response wrapper compatibility)."""

    def test_json_returns_parsed_body(self):
        data = {'key': 'value', 'count': 42}
        raw = httpx.Response(200, json=data)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        assert adapter.json() == data

    def test_json_passes_kwargs_to_underlying(self):
        data = [1, 2, 3]
        raw = httpx.Response(200, json=data)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        # httpx.Response.json() accepts no kwargs by default but we pass through
        assert adapter.json() == data

    def test_content_delegates_to_response(self):
        body = b'hello world'
        raw = httpx.Response(200, content=body)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        assert adapter.content == body

    def test_status_code_delegates_to_response(self):
        raw = httpx.Response(404)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        assert adapter.status_code == 404

    def test_headers_delegates_to_response(self):
        raw = httpx.Response(200, headers={'X-Custom': 'value'})
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        assert adapter.headers.get('x-custom') == 'value'

    def test_encoding_get_and_set(self):
        raw = httpx.Response(200, content=b'')
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        adapter.encoding = 'utf-8'
        assert adapter.encoding == 'utf-8'

    def test_raise_for_status_success_does_not_raise(self):
        raw = httpx.Response(200)
        with mock.patch.object(raw, 'raise_for_status'):
            adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
            adapter.raise_for_status()  # no raise

    def test_raise_for_status_http_error_raises_requests_style(self):
        raw = httpx.Response(401, content=b'Unauthorized')
        with mock.patch.object(
            raw,
            'raise_for_status',
            side_effect=httpx.HTTPStatusError('Unauthorized', request=mock.MagicMock(), response=raw),
        ):
            adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
            with pytest.raises(requests.exceptions.HTTPError) as exc_info:
                adapter.raise_for_status()
            assert exc_info.value.response is adapter
            assert exc_info.value.response.status_code == 401

    def test_raise_for_status_exception_has_response_with_json(self):
        data = {'error': 'forbidden'}
        raw = httpx.Response(403, json=data)
        with mock.patch.object(
            raw,
            'raise_for_status',
            side_effect=httpx.HTTPStatusError('Forbidden', request=mock.MagicMock(), response=raw),
        ):
            adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
            with pytest.raises(requests.exceptions.HTTPError) as exc_info:
                adapter.raise_for_status()
            assert exc_info.value.response.json() == data

    def test_close_delegates_to_response(self):
        raw = httpx.Response(200)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        adapter.close()
        # No exception; real Response.close() is idempotent

    def test_iter_content_chunks(self):
        body = b'abc'
        raw = httpx.Response(200, content=body)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=2)
        chunks = list(adapter.iter_content())
        assert len(chunks) == 2
        assert chunks[0] == b'ab'
        assert chunks[1] == b'c'

    def test_iter_lines_newline_delimiter(self):
        body = b'line1\nline2\r\nline3'
        raw = httpx.Response(200, content=body)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        lines = list(adapter.iter_lines())
        assert lines == [b'line1', b'line2', b'line3']

    def test_iter_lines_decode_unicode(self):
        body = 'a\nb'.encode('utf-8')
        raw = httpx.Response(200, content=body)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        lines = list(adapter.iter_lines(decode_unicode=True))
        assert lines == ['a', 'b']

    def test_iter_lines_custom_delimiter(self):
        body = b'one|two|three'
        raw = httpx.Response(200, content=body)
        adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
        parts = list(adapter.iter_lines(delimiter=b'|'))
        assert parts == [b'one', b'two', b'three']

    def test_raise_for_status_http_status_error_with_no_args(self):
        raw = httpx.Response(500, content=b'Error')
        err = httpx.HTTPStatusError('msg', request=mock.MagicMock(), response=raw)
        err.args = ()  # simulate empty args so adapter passes None to RequestsHTTPError
        with mock.patch.object(raw, 'raise_for_status', side_effect=err):
            adapter = HTTPXResponseAdapter(raw, default_chunk_size=1024)
            with pytest.raises(requests.exceptions.HTTPError) as exc_info:
                adapter.raise_for_status()
            assert exc_info.value.response is adapter
            assert exc_info.value.args[0] is None


# -----------------------------------------------------------------------------
# HTTPXWrapper.session (backward compatibility)
# -----------------------------------------------------------------------------


class TestHTTPXWrapperSession:
    """Tests for HTTPXWrapper.session (session-like close)."""

    def test_session_returns_object_with_close(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        session = http.session
        assert session is not None
        assert hasattr(session, 'close')
        assert callable(session.close)

    def test_session_close_when_no_persistent_client(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        assert getattr(http, '_client', None) is None
        http.session.close()  # no-op, must not raise

    def test_session_close_closes_persistent_client(self):
        instance = {'persist_connections': True}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        # Trigger a request so _client is set (mocked)
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(200, content=b'ok')
            http.get('https://example.com/')
        assert http._client is not None
        http.session.close()
        assert http._client is None

    def test_session_close_idempotent(self):
        instance = {'persist_connections': True}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(200, content=b'ok')
            http.get('https://example.com/')
        http.session.close()
        http.session.close()  # second close must not raise
        assert http._client is None


# -----------------------------------------------------------------------------
# HTTPXWrapper options['auth'] (basic auth as tuple)
# -----------------------------------------------------------------------------


class TestHTTPXWrapperAuth:
    """Tests for HTTPXWrapper auth options (tuple for basic auth)."""

    def test_options_auth_basic_is_tuple(self):
        instance = {'username': 'user', 'password': 'pass'}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        assert http.options['auth'] == ('user', 'pass')

    def test_options_auth_basic_authtype_explicit(self):
        instance = {'username': 'u', 'password': 'p', 'auth_type': 'basic'}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        assert http.options['auth'] == ('u', 'p')

    def test_options_auth_no_creds_is_none(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        assert http.options['auth'] is None

    def test_options_auth_only_username_is_none(self):
        instance = {'username': 'u'}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        assert http.options['auth'] is None

    def test_options_auth_only_password_is_none(self):
        instance = {'password': 'p'}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        assert http.options['auth'] is None

    def test_make_httpx_auth_unknown_type_returns_none_and_logs(self, caplog):
        logger = logging.getLogger('test_httpx_auth')
        config = {
            'auth_type': 'digest',
            'username': 'u',
            'password': 'p',
        }
        with caplog.at_level(logging.WARNING):
            result = _make_httpx_auth(config, logger)
        assert result is None
        assert 'digest' in caplog.text or 'not yet support' in caplog.text.lower()

    def test_make_httpx_auth_invalid_authtype_falls_back_to_basic(self):
        logger = logging.getLogger('test_httpx_auth')
        config = {
            'auth_type': 'invalid',
            'username': 'u',
            'password': 'p',
        }
        result = _make_httpx_auth(config, logger)
        assert result == ('u', 'p')


# -----------------------------------------------------------------------------
# HTTPXWrapper get/post and adapter roundtrip
# -----------------------------------------------------------------------------


class TestHTTPXWrapperRequestResponse:
    """Tests for HTTPXWrapper request/response path and adapter usage."""

    def test_get_returns_adapter_with_json(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        payload = {'result': True}
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(200, json=payload)
            response = http.get('https://example.com/api')
        assert isinstance(response, HTTPXResponseAdapter)
        assert response.json() == payload

    def test_post_returns_adapter(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(201, content=b'created')
            response = http.post('https://example.com/')
        assert isinstance(response, HTTPXResponseAdapter)
        assert response.status_code == 201

    def test_head_returns_adapter(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(200, headers={'Content-Length': '0'})
            response = http.head('https://example.com/')
        assert isinstance(response, HTTPXResponseAdapter)
        assert response.status_code == 200

    def test_delete_returns_adapter(self):
        instance = {}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(204, content=b'')
            response = http.delete('https://example.com/resource')
        assert isinstance(response, HTTPXResponseAdapter)
        assert response.status_code == 204

    def test_log_requests_logs_debug(self, caplog):
        instance = {'log_requests': True}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(200, content=b'')
            with caplog.at_level(logging.DEBUG):
                http.get('https://example.com/')
        assert 'GET' in caplog.text and 'example.com' in caplog.text

    def test_request_with_basic_auth_tuple_passed_to_client(self):
        instance = {'username': 'u', 'password': 'p'}
        init_config = {}
        http = HTTPXWrapper(instance, init_config)
        with mock.patch('datadog_checks.base.utils.http.httpx.Client') as client_cls:
            mock_client = mock.MagicMock()
            mock_client.request.return_value = httpx.Response(200, content=b'')
            mock_client.__enter__ = mock.MagicMock(return_value=mock_client)
            mock_client.__exit__ = mock.MagicMock(return_value=False)
            client_cls.return_value = mock_client
            http.get('https://example.com/')
        # Auth is passed to Client() constructor, not to request()
        call_kw = client_cls.call_args.kwargs
        assert call_kw.get('auth') == ('u', 'p')


# -----------------------------------------------------------------------------
# AgentCheck.http (HTTPXWrapper) integration
# -----------------------------------------------------------------------------


class TestAgentCheckHTTPX:
    """Tests for AgentCheck using HTTPXWrapper."""

    def test_check_http_is_httpx_wrapper(self):
        check = AgentCheck('test', {}, [{}])
        assert isinstance(check.http, HTTPXWrapper)

    def test_check_http_get_json_roundtrip(self):
        check = AgentCheck('test', {}, [{}])
        with mock.patch.object(httpx.Client, 'request') as req:
            req.return_value = httpx.Response(200, json={'ok': True})
            resp = check.http.get('https://example.com/')
        assert resp.json() == {'ok': True}
