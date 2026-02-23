# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_testing import MockHTTPResponse


class TestMockHTTPResponseBasics:
    """Test basic MockHTTPResponse functionality."""

    def test_default_status_code(self):
        """Default status code is 200."""
        response = MockHTTPResponse(content='test')

        assert response.status_code == 200


class TestMockHTTPResponseJSON:
    """Test JSON response functionality."""

    def test_json_with_custom_headers(self):
        """json_data sets Content-Type but preserves other headers."""
        headers = {'X-Custom': 'value'}
        response = MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

        assert response.headers['content-type'] == 'application/json'
        assert response.headers['x-custom'] == 'value'

    def test_json_does_not_mutate_caller_headers(self):
        """json_data path must not modify the caller's headers dict."""
        headers = {'X-Custom': 'value'}
        MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

        assert list(headers.keys()) == ['X-Custom']

    def test_header_keys_are_lowercased(self):
        """Header keys are stored lowercased; read with lowercase key or .get(key.lower())."""
        response = MockHTTPResponse(content='ok', headers={'Content-Type': 'text/plain'})

        assert response.headers['content-type'] == 'text/plain'
        assert response.headers.get('content-type') == 'text/plain'
        assert 'content-type' in response.headers
        assert 'Content-Type' not in response.headers


class TestMockHTTPResponseStatus:
    """Test raise_for_status functionality."""

    def test_client_error_raises(self):
        """4xx status codes raise HTTPStatusError."""
        response = MockHTTPResponse(content='Not Found', status_code=404)

        with pytest.raises(HTTPStatusError) as exc_info:
            response.raise_for_status()

        assert '404 Client Error' in str(exc_info.value)
        assert exc_info.value.response is response

    def test_server_error_raises(self):
        """5xx status codes raise HTTPStatusError."""
        response = MockHTTPResponse(content='Server Error', status_code=500)

        with pytest.raises(HTTPStatusError) as exc_info:
            response.raise_for_status()

        assert '500 Server Error' in str(exc_info.value)
        assert exc_info.value.response is response


class TestMockHTTPResponseStreaming:
    """Test streaming functionality (iter_content, iter_lines)."""

    def test_iter_lines_preserves_empty_lines(self):
        """Empty lines are preserved but trailing delimiter does not produce an extra element."""
        content = 'line1\n\nline3\n'
        response = MockHTTPResponse(content=content)

        lines = list(response.iter_lines())
        assert lines == [b'line1', b'', b'line3']


class TestMockHTTPResponseNormalization:
    """Test content normalization."""

    def test_normalize_leading_newline(self):
        """Leading newline is removed by default."""
        content = '\nActual content'
        response = MockHTTPResponse(content=content)

        assert response.text == 'Actual content'
