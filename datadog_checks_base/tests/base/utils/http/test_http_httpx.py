# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock

import httpx
import pytest

from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPStatusError,
    HTTPTimeoutError,
)
from datadog_checks.base.utils.http_httpx import HTTPXResponseAdapter, HTTPXWrapper


class TestHTTPXResponseAdapter:
    def test_iter_content_yields_bytes_by_default(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_bytes.return_value = iter([b"chunk1", b"chunk2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_content()) == [b"chunk1", b"chunk2"]

    def test_iter_content_yields_str_when_decode_unicode(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_text.return_value = iter(["chunk1", "chunk2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_content(decode_unicode=True)) == ["chunk1", "chunk2"]

    def test_iter_lines_yields_bytes_by_default(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_lines.return_value = iter(["line1", "line2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_lines()) == [b"line1", b"line2"]

    def test_iter_lines_yields_str_when_decode_unicode(self):
        response = MagicMock(spec=httpx.Response)
        response.iter_lines.return_value = iter(["line1", "line2"])
        adapter = HTTPXResponseAdapter(response)

        assert list(adapter.iter_lines(decode_unicode=True)) == ["line1", "line2"]

    def test_raise_for_status_translates_http_status_error(self):
        response = MagicMock(spec=httpx.Response)
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        )
        adapter = HTTPXResponseAdapter(response)

        with pytest.raises(HTTPStatusError):
            adapter.raise_for_status()

    def test_context_manager_closes_response_on_exit(self):
        response = MagicMock(spec=httpx.Response)
        adapter = HTTPXResponseAdapter(response)

        with adapter:
            pass

        response.close.assert_called_once()

    def test_response_attributes_accessible(self):
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        adapter = HTTPXResponseAdapter(response)

        assert adapter.status_code == 200


class TestHTTPXWrapper:
    def test_successful_request_returns_response_adapter(self):
        client = MagicMock(spec=httpx.Client)
        client.request.return_value = MagicMock(spec=httpx.Response)
        wrapper = HTTPXWrapper(client)

        result = wrapper.get("http://example.com")

        assert isinstance(result, HTTPXResponseAdapter)

    def test_timeout_raises_http_timeout_error(self):
        client = MagicMock(spec=httpx.Client)
        request = httpx.Request("GET", "http://example.com")
        client.request.side_effect = httpx.TimeoutException("timed out", request=request)
        wrapper = HTTPXWrapper(client)

        with pytest.raises(HTTPTimeoutError):
            wrapper.get("http://example.com")

    def test_connect_error_raises_http_connection_error(self):
        client = MagicMock(spec=httpx.Client)
        request = httpx.Request("GET", "http://example.com")
        client.request.side_effect = httpx.ConnectError("connection refused", request=request)
        wrapper = HTTPXWrapper(client)

        with pytest.raises(HTTPConnectionError):
            wrapper.get("http://example.com")

    def test_all_http_methods_delegate_to_client(self):
        client = MagicMock(spec=httpx.Client)
        client.request.return_value = MagicMock(spec=httpx.Response)
        wrapper = HTTPXWrapper(client)

        url = "http://example.com"
        wrapper.get(url)
        wrapper.post(url)
        wrapper.head(url)
        wrapper.put(url)
        wrapper.patch(url)
        wrapper.delete(url)
        wrapper.options_method(url)

        methods = [call.args[0] for call in client.request.call_args_list]
        assert methods == ["GET", "POST", "HEAD", "PUT", "PATCH", "DELETE", "OPTIONS"]
