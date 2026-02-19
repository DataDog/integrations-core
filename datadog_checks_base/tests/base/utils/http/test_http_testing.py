# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for HTTP testing utilities.

Verifies MockHTTPResponse implementation details:
- Default status_code=200
- json_data auto-sets Content-Type header
- raise_for_status() logic for 4xx/5xx codes
- iter_lines() preserves empty lines (matches requests behavior)
- Raw response mock structure for certificate access
- Leading newline normalization
"""

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

        assert response.headers['Content-Type'] == 'application/json'
        assert response.headers['X-Custom'] == 'value'


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
