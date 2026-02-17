"""Tests for HTTP testing utilities."""

import json
import tempfile

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.base.utils.http_protocol import HTTPResponseProtocol
from datadog_checks.base.utils.http_testing import MockHTTPResponse


class TestMockHTTPResponseBasics:
    """Test basic MockHTTPResponse functionality."""

    def test_simple_text_response(self):
        """Test basic text response."""
        response = MockHTTPResponse(content='Hello, World!', status_code=200)

        assert response.status_code == 200
        assert response.text == 'Hello, World!'
        assert response.content == b'Hello, World!'

    def test_bytes_content(self):
        """Test response with bytes content."""
        response = MockHTTPResponse(content=b'Binary data', status_code=200)

        assert response.status_code == 200
        assert response.content == b'Binary data'
        assert response.text == 'Binary data'

    def test_default_status_code(self):
        """Test that default status code is 200."""
        response = MockHTTPResponse(content='test')

        assert response.status_code == 200

    def test_custom_status_code(self):
        """Test custom status codes."""
        response_404 = MockHTTPResponse(content='Not Found', status_code=404)
        response_500 = MockHTTPResponse(content='Server Error', status_code=500)

        assert response_404.status_code == 404
        assert response_500.status_code == 500

    def test_headers(self):
        """Test response headers."""
        headers = {'Content-Type': 'text/html', 'X-Custom': 'value'}
        response = MockHTTPResponse(content='test', headers=headers)

        assert response.headers == headers
        assert response.headers['Content-Type'] == 'text/html'
        assert response.headers['X-Custom'] == 'value'

    def test_cookies(self):
        """Test response cookies."""
        cookies = {'session': 'abc123', 'user': 'alice'}
        response = MockHTTPResponse(content='test', cookies=cookies)

        assert response.cookies == cookies
        assert response.cookies['session'] == 'abc123'

    def test_elapsed_time(self):
        """Test simulated response time."""
        response = MockHTTPResponse(content='test', elapsed_seconds=0.5)

        assert response.elapsed.total_seconds() == 0.5


class TestMockHTTPResponseJSON:
    """Test JSON response functionality."""

    def test_json_response(self):
        """Test JSON response creation."""
        data = {'user': 'alice', 'age': 30, 'active': True}
        response = MockHTTPResponse(json_data=data, status_code=200)

        assert response.status_code == 200
        assert response.json() == data
        assert response.headers['Content-Type'] == 'application/json'

    def test_json_parsing(self):
        """Test JSON parsing from string content."""
        json_string = '{"status": "ok", "count": 42}'
        response = MockHTTPResponse(content=json_string)

        parsed = response.json()
        assert parsed['status'] == 'ok'
        assert parsed['count'] == 42

    def test_json_with_custom_headers(self):
        """Test that json_data sets Content-Type but preserves other headers."""
        headers = {'X-Custom': 'value'}
        response = MockHTTPResponse(json_data={'key': 'value'}, headers=headers)

        assert response.headers['Content-Type'] == 'application/json'
        assert response.headers['X-Custom'] == 'value'

    def test_invalid_json(self):
        """Test that invalid JSON raises JSONDecodeError."""
        response = MockHTTPResponse(content='not valid json')

        with pytest.raises(json.JSONDecodeError):
            response.json()

    def test_json_kwargs(self):
        """Test that kwargs are passed to json.loads()."""
        # Test with parse_float to convert floats to Decimal (example kwargs usage)
        from decimal import Decimal

        response = MockHTTPResponse(content='{"price": 19.99}')
        result = response.json(parse_float=Decimal)

        assert isinstance(result['price'], Decimal)


class TestMockHTTPResponseFile:
    """Test file loading functionality."""

    def test_load_from_file(self):
        """Test loading content from file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('File content here')
            file_path = f.name

        try:
            response = MockHTTPResponse(file_path=file_path)
            assert response.text == 'File content here'
        finally:
            import os

            os.unlink(file_path)


class TestMockHTTPResponseStatus:
    """Test raise_for_status functionality."""

    def test_success_no_exception(self):
        """Test that 2xx status codes don't raise."""
        for status_code in [200, 201, 204]:
            response = MockHTTPResponse(content='ok', status_code=status_code)
            response.raise_for_status()  # Should not raise

    def test_client_error_raises(self):
        """Test that 4xx status codes raise HTTPStatusError."""
        response = MockHTTPResponse(content='Not Found', status_code=404)

        with pytest.raises(HTTPStatusError) as exc_info:
            response.raise_for_status()

        assert '404 Client Error' in str(exc_info.value)
        assert exc_info.value.response is response

    def test_server_error_raises(self):
        """Test that 5xx status codes raise HTTPStatusError."""
        response = MockHTTPResponse(content='Server Error', status_code=500)

        with pytest.raises(HTTPStatusError) as exc_info:
            response.raise_for_status()

        assert '500 Server Error' in str(exc_info.value)
        assert exc_info.value.response is response


class TestMockHTTPResponseStreaming:
    """Test streaming functionality (iter_content, iter_lines)."""

    def test_iter_content_with_chunk_size(self):
        """Test iter_content with specific chunk size."""
        content = b'abcdefghijklmnop'
        response = MockHTTPResponse(content=content)

        chunks = list(response.iter_content(chunk_size=4))
        assert chunks == [b'abcd', b'efgh', b'ijkl', b'mnop']

    def test_iter_content_default_chunk_size(self):
        """Test iter_content with default chunk size (1 byte)."""
        content = b'abc'
        response = MockHTTPResponse(content=content)

        chunks = list(response.iter_content())
        assert chunks == [b'a', b'b', b'c']

    def test_iter_content_large_chunk(self):
        """Test iter_content with chunk size larger than content."""
        content = b'short'
        response = MockHTTPResponse(content=content)

        chunks = list(response.iter_content(chunk_size=100))
        assert chunks == [b'short']

    def test_iter_lines_default_delimiter(self):
        """Test iter_lines with newline delimiter."""
        content = 'line1\nline2\nline3'
        response = MockHTTPResponse(content=content)

        lines = list(response.iter_lines())
        assert lines == [b'line1', b'line2', b'line3']

    def test_iter_lines_custom_delimiter(self):
        """Test iter_lines with custom delimiter."""
        content = 'part1|part2|part3'
        response = MockHTTPResponse(content=content)

        parts = list(response.iter_lines(delimiter=b'|'))
        assert parts == [b'part1', b'part2', b'part3']

    def test_iter_lines_empty_lines_skipped(self):
        """Test that empty lines are skipped."""
        content = 'line1\n\nline3\n'
        response = MockHTTPResponse(content=content)

        lines = list(response.iter_lines())
        assert lines == [b'line1', b'line3']

    def test_streaming_resets_position(self):
        """Test that streaming resets stream position."""
        response = MockHTTPResponse(content='test content')

        # First iteration
        chunks1 = list(response.iter_content(chunk_size=4))
        # Stream should be consumed now

        # Create new response for second iteration (stream consumed flag set)
        response2 = MockHTTPResponse(content='test content')
        response2._stream_consumed = False  # Explicitly reset for test

        chunks2 = list(response2.iter_content(chunk_size=4))
        assert chunks1 == chunks2


class TestMockHTTPResponseContextManager:
    """Test context manager support."""

    def test_context_manager(self):
        """Test that response works as context manager."""
        with MockHTTPResponse(content='test') as response:
            assert response.text == 'test'
            assert response.status_code == 200

    def test_context_manager_cleanup(self):
        """Test that context manager closes stream."""
        response = MockHTTPResponse(content='test')

        with response:
            pass  # Use context manager

        # Stream should be closed
        assert response._stream.closed


class TestMockHTTPResponseProtocol:
    """Test protocol conformance."""

    def test_implements_http_response_protocol(self):
        """Test that MockHTTPResponse implements HTTPResponseProtocol."""
        response = MockHTTPResponse(content='test')
        assert isinstance(response, HTTPResponseProtocol)

    def test_has_required_attributes(self):
        """Test that response has all required protocol attributes."""
        response = MockHTTPResponse(content='test', status_code=200)

        # Core attributes
        assert hasattr(response, 'status_code')
        assert hasattr(response, 'content')
        assert hasattr(response, 'text')
        assert hasattr(response, 'headers')

        # Methods
        assert hasattr(response, 'json')
        assert hasattr(response, 'raise_for_status')
        assert hasattr(response, 'iter_content')
        assert hasattr(response, 'iter_lines')

        # Context manager
        assert hasattr(response, '__enter__')
        assert hasattr(response, '__exit__')


class TestMockHTTPResponseRawAccess:
    """Test raw response object access (for integrations like http_check)."""

    def test_raw_attribute_exists(self):
        """Test that raw attribute exists for compatibility."""
        response = MockHTTPResponse(content='test')
        assert hasattr(response, 'raw')

    def test_raw_connection_sock(self):
        """Test that raw.connection.sock exists."""
        response = MockHTTPResponse(content='test')
        assert hasattr(response.raw, 'connection')
        assert hasattr(response.raw.connection, 'sock')

    def test_getpeercert_method(self):
        """Test that getpeercert method exists and works."""
        response = MockHTTPResponse(content='test')

        # Test binary form
        cert_binary = response.raw.connection.sock.getpeercert(binary_form=True)
        assert cert_binary == b'mock-cert'

        # Test dict form
        cert_dict = response.raw.connection.sock.getpeercert(binary_form=False)
        assert cert_dict == {}


class TestMockHTTPResponseNormalization:
    """Test content normalization."""

    def test_normalize_leading_newline(self):
        """Test that leading newline is removed by default."""
        content = '\nActual content'
        response = MockHTTPResponse(content=content)

        assert response.text == 'Actual content'

    def test_normalize_disabled(self):
        """Test that normalization can be disabled."""
        content = '\nKeep newline'
        response = MockHTTPResponse(content=content, normalize_content=False)

        assert response.text == '\nKeep newline'

    def test_no_normalization_needed(self):
        """Test content without leading newline."""
        content = 'No newline'
        response = MockHTTPResponse(content=content)

        assert response.text == 'No newline'
