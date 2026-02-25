# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_testing import MockHTTPResponse


class TestMockHTTPFixture:
    """Test the mock_http fixture."""

    def test_patches_agentcheck_http(self, mock_http):
        """check.http returns the mock when mock_http fixture is active."""
        check = AgentCheck('test', {}, [{}])
        assert check.http is mock_http


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


class TestMockHTTPResponseFilePath:
    """Test the file_path constructor path."""

    def test_file_path_reads_content(self, tmp_path):
        """file_path reads file content as bytes."""
        f = tmp_path / 'fixture.txt'
        f.write_bytes(b'file content')

        response = MockHTTPResponse(file_path=str(f))
        assert response.content == b'file content'


class TestMockHTTPResponseStatus:
    """Test raise_for_status functionality."""

    def test_2xx_does_not_raise(self):
        """2xx status codes do not raise."""
        response = MockHTTPResponse(content='ok', status_code=200)
        response.raise_for_status()  # must not raise

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

    def test_iter_content_chunks_by_size(self):
        """iter_content splits content into chunks of the requested size."""
        response = MockHTTPResponse(content='hello world')

        chunks = list(response.iter_content(chunk_size=5))
        assert chunks == [b'hello', b' worl', b'd']

    def test_iter_lines_preserves_empty_lines(self):
        """Empty lines are preserved but trailing delimiter does not produce an extra element."""
        content = 'line1\n\nline3\n'
        response = MockHTTPResponse(content=content)

        lines = list(response.iter_lines())
        assert lines == [b'line1', b'', b'line3']

    def test_iter_lines_decode_unicode(self):
        """decode_unicode=True returns str instead of bytes."""
        response = MockHTTPResponse(content='line1\nline2')

        lines = list(response.iter_lines(decode_unicode=True))
        assert lines == ['line1', 'line2']

    def test_iter_lines_custom_delimiter(self):
        """Custom delimiter splits on the given character."""
        response = MockHTTPResponse(content='a|b|c')

        lines = list(response.iter_lines(delimiter='|'))
        assert lines == [b'a', b'b', b'c']


class TestMockHTTPResponseNormalization:
    """Test content normalization."""

    def test_normalize_leading_newline(self):
        """Leading newline is removed by default."""
        content = '\nActual content'
        response = MockHTTPResponse(content=content)

        assert response.text == 'Actual content'
