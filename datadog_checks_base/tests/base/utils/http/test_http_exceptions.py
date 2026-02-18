# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for HTTP exception abstraction."""

import requests.exceptions

from datadog_checks.base.utils.http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPRequestError,
    HTTPSSLError,
    HTTPStatusError,
    HTTPTimeoutError,
    from_requests_exception,
)


class TestHTTPExceptionHierarchy:
    """Test exception hierarchy and attributes."""

    def test_base_exception_attributes(self):
        """HTTPError should have response and request attributes."""
        exc = HTTPError('test error', response='mock_response', request='mock_request')

        assert str(exc) == 'test error'
        assert exc.response == 'mock_response'
        assert exc.request == 'mock_request'

    def test_base_exception_without_response(self):
        """HTTPError should work without response and request."""
        exc = HTTPError('test error')

        assert str(exc) == 'test error'
        assert exc.response is None
        assert exc.request is None

    def test_inheritance_hierarchy(self):
        """Test exception inheritance relationships."""
        # HTTPRequestError inherits from HTTPError
        assert issubclass(HTTPRequestError, HTTPError)

        # HTTPStatusError inherits from HTTPError
        assert issubclass(HTTPStatusError, HTTPError)

        # HTTPTimeoutError inherits from HTTPRequestError
        assert issubclass(HTTPTimeoutError, HTTPRequestError)

        # HTTPConnectionError inherits from HTTPRequestError
        assert issubclass(HTTPConnectionError, HTTPRequestError)

        # HTTPSSLError inherits from HTTPConnectionError
        assert issubclass(HTTPSSLError, HTTPConnectionError)

    def test_exception_instantiation(self):
        """Test that all exception types can be instantiated."""
        exceptions = [
            HTTPError('base error'),
            HTTPRequestError('request error'),
            HTTPStatusError('status error'),
            HTTPTimeoutError('timeout error'),
            HTTPConnectionError('connection error'),
            HTTPSSLError('ssl error'),
        ]

        for exc in exceptions:
            assert isinstance(exc, HTTPError)
            assert str(exc)  # Has a message


class TestRequestsExceptionConversion:
    """Test conversion from requests exceptions."""

    def test_convert_timeout_exception(self):
        """requests.Timeout should convert to HTTPTimeoutError."""
        req_exc = requests.exceptions.Timeout('Request timeout')
        http_exc = from_requests_exception(req_exc)

        assert isinstance(http_exc, HTTPTimeoutError)
        assert isinstance(http_exc, HTTPRequestError)
        assert isinstance(http_exc, HTTPError)
        assert str(http_exc) == 'Request timeout'

    def test_convert_connection_error(self):
        """requests.ConnectionError should convert to HTTPConnectionError."""
        req_exc = requests.exceptions.ConnectionError('Connection failed')
        http_exc = from_requests_exception(req_exc)

        assert isinstance(http_exc, HTTPConnectionError)
        assert isinstance(http_exc, HTTPRequestError)
        assert str(http_exc) == 'Connection failed'

    def test_convert_ssl_error(self):
        """requests.SSLError should convert to HTTPSSLError."""
        req_exc = requests.exceptions.SSLError('SSL verification failed')
        http_exc = from_requests_exception(req_exc)

        assert isinstance(http_exc, HTTPSSLError)
        assert isinstance(http_exc, HTTPConnectionError)
        assert isinstance(http_exc, HTTPRequestError)

    def test_convert_http_error(self):
        """requests.HTTPError should convert to HTTPStatusError."""
        req_exc = requests.exceptions.HTTPError('404 Not Found')
        http_exc = from_requests_exception(req_exc)

        assert isinstance(http_exc, HTTPStatusError)
        assert isinstance(http_exc, HTTPError)
        assert str(http_exc) == '404 Not Found'

    def test_convert_generic_request_exception(self):
        """requests.RequestException should convert to HTTPRequestError."""
        req_exc = requests.exceptions.RequestException('Generic request error')
        http_exc = from_requests_exception(req_exc)

        assert isinstance(http_exc, HTTPRequestError)
        assert isinstance(http_exc, HTTPError)

    def test_preserve_exception_message(self):
        """Exception message should be preserved."""
        original_message = 'Custom error message'
        req_exc = requests.exceptions.RequestException(original_message)
        http_exc = from_requests_exception(req_exc)

        assert str(http_exc) == original_message

    def test_preserve_response_and_request(self):
        """Response and request objects should be preserved."""
        req_exc = requests.exceptions.RequestException('Error with context')
        req_exc.response = 'mock_response'
        req_exc.request = 'mock_request'

        http_exc = from_requests_exception(req_exc)

        assert http_exc.response == 'mock_response'
        assert http_exc.request == 'mock_request'

    def test_convert_unknown_exception(self):
        """Unknown exception types should convert to base HTTPError."""
        unknown_exc = ValueError('Not an HTTP exception')
        http_exc = from_requests_exception(unknown_exc)

        assert isinstance(http_exc, HTTPError)
        assert not isinstance(http_exc, HTTPRequestError)


class TestExceptionCatching:
    """Test that exceptions can be caught by parent types."""

    def test_catch_by_parent_type(self):
        """Specific exceptions should be catchable by parent type."""
        timeout_error = HTTPTimeoutError('timeout')

        # Should be catchable as HTTPRequestError
        try:
            raise timeout_error
        except HTTPRequestError:
            pass  # Expected

        # Should be catchable as HTTPError
        try:
            raise timeout_error
        except HTTPError:
            pass  # Expected

    def test_catch_ssl_as_connection_error(self):
        """HTTPSSLError should be catchable as HTTPConnectionError."""
        ssl_error = HTTPSSLError('ssl issue')

        try:
            raise ssl_error
        except HTTPConnectionError:
            pass  # Expected
