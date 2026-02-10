# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
from unittest import mock

import httpx
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.httpx import (
    HTTPXResponseAdapter,
    HTTPXWrapper,
    _make_httpx_auth,
    _parse_uds_url,
)
from datadog_checks.dev import TempDir
from datadog_checks.dev.fs import write_file


class TestMakeHttpxAuth:
    """Test _make_httpx_auth builds correct auth from config."""

    def test_basic_auth_with_credentials(self):
        logger = logging.getLogger('test')
        config = {'auth_type': 'basic', 'username': 'u', 'password': 'p'}
        assert _make_httpx_auth(config, logger) == ('u', 'p')

    def test_basic_auth_without_credentials_returns_none(self):
        logger = logging.getLogger('test')
        config = {'auth_type': 'basic'}
        assert _make_httpx_auth(config, logger) is None

    def test_unsupported_auth_type_logs_and_returns_none(self, caplog):
        logger = logging.getLogger('test')
        config = {'auth_type': 'digest'}
        with caplog.at_level(logging.WARNING):
            assert _make_httpx_auth(config, logger) is None
        assert 'digest' in caplog.text and 'without auth' in caplog.text


class TestParseUdsUrl:
    """Test _parse_uds_url for normal and unix URLs."""

    def test_normal_url_returns_none_and_unchanged_url(self):
        assert _parse_uds_url('http://example.com/path') == (None, 'http://example.com/path')
        assert _parse_uds_url('https://foo/') == (None, 'https://foo/')

    def test_unix_url_with_netloc(self):
        # unix://hostname/path has netloc=hostname (e.g. percent-encoded socket path)
        uds_path, request_url = _parse_uds_url('unix://%2Fvar%2Frun%2Fdocker.sock/info')
        assert uds_path == '/var/run/docker.sock'
        assert request_url == 'http://localhost/info'

    def test_unix_url_path_with_sock_suffix(self):
        uds_path, request_url = _parse_uds_url('unix:///var/run/app.sock/metrics')
        assert uds_path == '/var/run/app.sock'
        assert request_url == 'http://localhost/metrics'

    def test_unix_url_path_without_sock(self):
        uds_path, request_url = _parse_uds_url('unix:///some/path')
        assert uds_path == '/some/path'
        assert request_url == 'http://localhost/'


class TestBaseCheckUseHttpx:
    """Test that the base check's http property respects use_httpx."""

    def test_default_use_httpx_false(self):
        check = AgentCheck('test', {}, [{}])
        assert isinstance(check.http, RequestsWrapper)

    def test_use_httpx_false_explicit(self):
        check = AgentCheck('test', {'use_httpx': False}, [{}])
        assert isinstance(check.http, RequestsWrapper)

    def test_use_httpx_true_init_config(self):
        check = AgentCheck('test', {'use_httpx': True}, [{}])
        assert isinstance(check.http, HTTPXWrapper)

    def test_use_httpx_true_instance_overrides(self):
        check = AgentCheck('test', {'use_httpx': False}, [{'use_httpx': True}])
        assert isinstance(check.http, HTTPXWrapper)

    def test_use_httpx_instance_takes_precedence(self):
        check = AgentCheck('test', {'use_httpx': True}, [{'use_httpx': False}])
        assert isinstance(check.http, RequestsWrapper)


class TestHTTPXResponseAdapter:
    """Test HTTPXResponseAdapter matches the response surface expected by callers."""

    def test_content(self):
        response = httpx.Response(200, content=b'hello')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        assert adapter.content == b'hello'
        assert adapter.status_code == 200

    def test_headers(self):
        response = httpx.Response(200, headers={'X-Foo': 'bar'})
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        assert adapter.headers.get('x-foo') == 'bar'

    def test_encoding_get_set(self):
        response = httpx.Response(200, content=b'hi')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        adapter.encoding = 'utf-8'
        assert adapter.encoding == 'utf-8'

    def test_iter_lines(self):
        response = httpx.Response(200, content=b'line1\nline2\n')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        lines = list(adapter.iter_lines(decode_unicode=False))
        assert lines == [b'line1', b'line2']

    def test_iter_lines_decode_unicode(self):
        response = httpx.Response(200, content=b'hello\n')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        adapter.encoding = 'utf-8'
        lines = list(adapter.iter_lines(decode_unicode=True))
        assert lines == ['hello']

    def test_raise_for_status_ok(self):
        response = httpx.Response(200)
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        adapter.raise_for_status()  # no raise

    def test_raise_for_status_error(self):
        response = httpx.Response(404)
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        with pytest.raises(Exception) as exc_info:
            adapter.raise_for_status()
        assert getattr(exc_info.value, 'response', None) is adapter

    def test_close(self):
        response = httpx.Response(200)
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        adapter.close()  # no op for in-memory response

    def test_iter_content_chunks(self):
        response = httpx.Response(200, content=b'abcdefghij')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=3)
        chunks = list(adapter.iter_content(chunk_size=3, decode_unicode=False))
        assert chunks == [b'abc', b'def', b'ghi', b'j']

    def test_iter_content_decode_unicode(self):
        response = httpx.Response(200, content=b'ab')
        response.encoding = 'utf-8'
        adapter = HTTPXResponseAdapter(response, default_chunk_size=1)
        chunks = list(adapter.iter_content(chunk_size=1, decode_unicode=True))
        assert chunks == ['a', 'b']

    def test_iter_lines_custom_delimiter(self):
        response = httpx.Response(200, content=b'a|b|c')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        lines = list(adapter.iter_lines(delimiter=b'|', decode_unicode=False))
        assert lines == [b'a', b'b', b'c']

    def test_iter_lines_trailing_without_newline(self):
        response = httpx.Response(200, content=b'last')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        lines = list(adapter.iter_lines(decode_unicode=False))
        assert lines == [b'last']

    def test_raise_for_status_4xx_sets_response_on_exception(self):
        response = httpx.Response(404, content=b'Not Found')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        with pytest.raises(Exception) as exc_info:
            adapter.raise_for_status()
        assert '404' in str(exc_info.value)
        assert getattr(exc_info.value, 'response', None) is adapter

    def test_json_delegates_to_response(self):
        response = httpx.Response(200, content=b'{"a": 1}')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        assert adapter.json() == {'a': 1}

    def test_content_cached_on_multiple_access(self):
        response = httpx.Response(200, content=b'x')
        adapter = HTTPXResponseAdapter(response, default_chunk_size=16)
        assert adapter.content == b'x'
        assert adapter.content is adapter._content


class TestHTTPXWrapper:
    """Test HTTPXWrapper with mocked transport."""

    def test_get_returns_adapter(self):
        def handler(request):
            return httpx.Response(200, content=b'ok')

        transport = httpx.MockTransport(handler)
        mock_client = httpx.Client(transport=transport)
        instance = {}
        init_config = {}
        wrapper = HTTPXWrapper(instance, init_config)
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            response = wrapper.get('http://example.com/')
            assert isinstance(response, HTTPXResponseAdapter)
            assert response.content == b'ok'

    def test_options_dict_present(self):
        instance = {}
        init_config = {}
        wrapper = HTTPXWrapper(instance, init_config)
        assert 'headers' in wrapper.options
        assert 'timeout' in wrapper.options
        assert 'verify' in wrapper.options

    def test_session_close(self):
        instance = {}
        init_config = {}
        wrapper = HTTPXWrapper(instance, init_config)
        session = wrapper.session
        assert hasattr(session, 'close')
        session.close()  # no error when _client is None

    @pytest.mark.parametrize('method', ['post', 'head', 'put', 'patch', 'delete', 'options_method'])
    def test_http_methods_return_adapter(self, method):
        def handler(request):
            return httpx.Response(200, content=b'ok')

        transport = httpx.MockTransport(handler)
        mock_client = httpx.Client(transport=transport)
        wrapper = HTTPXWrapper({}, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            fn = getattr(wrapper, method)
            if method == 'options_method':
                response = fn('http://example.com/')
            else:
                response = fn('http://example.com/')
            assert isinstance(response, HTTPXResponseAdapter)
            assert response.status_code == 200

    def test_log_requests_logs_debug(self, caplog):
        def handler(request):
            return httpx.Response(200)

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        wrapper = HTTPXWrapper({'log_requests': True}, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            with caplog.at_level(logging.DEBUG):
                wrapper.get('http://example.com/')
        assert 'Sending GET request' in caplog.text and 'example.com' in caplog.text

    def test_no_proxy_bypasses_proxy_for_matching_url(self):
        def handler(request):
            return httpx.Response(200)

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        instance = {
            'skip_proxy': False,
            'proxy': {'http': 'http://proxy:3128'},
            'no_proxy': 'http://direct.example.com',
        }
        wrapper = HTTPXWrapper(instance, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            response = wrapper.get('http://direct.example.com/')
        assert response.status_code == 200

    def test_persist_false_creates_new_client_per_request(self):
        def handler(request):
            return httpx.Response(200)

        clients = [
            httpx.Client(transport=httpx.MockTransport(handler)),
            httpx.Client(transport=httpx.MockTransport(handler)),
        ]
        wrapper = HTTPXWrapper({}, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', side_effect=clients) as client_cls:
            wrapper.get('http://example.com/', persist=False)
            wrapper.get('http://example.com/', persist=False)
            assert client_cls.call_count == 2

    def test_extra_headers_passed_per_request(self):
        seen_headers = []

        def handler(request):
            seen_headers.append(dict(request.headers))
            return httpx.Response(200)

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        wrapper = HTTPXWrapper({}, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            wrapper.get('http://example.com/', extra_headers={'X-Custom': 'value'})
        assert any(h.get('x-custom') == 'value' for h in seen_headers)

    def test_init_with_basic_auth(self):
        instance = {'username': 'u', 'password': 'p'}
        wrapper = HTTPXWrapper(instance, {})
        assert wrapper.options['auth'] == ('u', 'p')

    def test_init_with_connect_and_read_timeout(self):
        instance = {'connect_timeout': 2, 'read_timeout': 5, 'timeout': 10}
        wrapper = HTTPXWrapper(instance, {})
        assert wrapper.options['timeout'] == (2.0, 5.0)

    def test_init_with_tls_verify_false(self):
        instance = {'tls_verify': False}
        wrapper = HTTPXWrapper(instance, {})
        assert wrapper.options['verify'] is False

    def test_uds_request_returns_adapter(self):
        def handler(request):
            return httpx.Response(200, content=b'uds-ok')

        transport = httpx.MockTransport(handler)
        mock_client = httpx.Client(transport=transport)
        wrapper = HTTPXWrapper({}, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            response = wrapper.get('unix:///var/run/docker.sock/info')
        assert isinstance(response, HTTPXResponseAdapter)
        assert response.content == b'uds-ok'

    def test_session_close_closes_client_when_set(self):
        def handler(request):
            return httpx.Response(200)

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        wrapper = HTTPXWrapper({'persist_connections': True}, {})
        with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
            wrapper.get('http://example.com/')
        assert wrapper._client is mock_client
        wrapper.session.close()
        assert wrapper._client is None


class TestHTTPXWrapperAuthTokenRetry:
    """Test auth token refresh and retry (UDS and non-UDS)."""

    def test_auth_token_retry_on_401_then_success(self):
        call_count = [0]

        def handler(request):
            call_count[0] += 1
            if call_count[0] == 1:
                return httpx.Response(401, content=b'unauthorized')
            return httpx.Response(200, content=b'ok')

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            write_file(token_file, 'secret-token\n')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            wrapper = HTTPXWrapper(instance, {})
            with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
                response = wrapper.get('http://example.com/')
            assert response.status_code == 200
            assert call_count[0] == 2

    def test_auth_token_retry_uds_on_401_then_success(self):
        call_count = [0]

        def handler(request):
            call_count[0] += 1
            if call_count[0] == 1:
                return httpx.Response(401, content=b'unauthorized')
            return httpx.Response(200, content=b'uds-ok')

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        with TempDir() as temp_dir:
            token_file = os.path.join(temp_dir, 'token.txt')
            write_file(token_file, 'uds-token\n')
            instance = {
                'auth_token': {
                    'reader': {'type': 'file', 'path': token_file},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                }
            }
            wrapper = HTTPXWrapper(instance, {})
            with mock.patch('datadog_checks.base.utils.httpx.httpx.Client', return_value=mock_client):
                response = wrapper.get('unix:///var/run/docker.sock/info')
            assert response.status_code == 200
            assert response.content == b'uds-ok'
            assert call_count[0] == 2
