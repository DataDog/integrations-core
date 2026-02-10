# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import httpx
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.httpx import HTTPXResponseAdapter, HTTPXWrapper


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
