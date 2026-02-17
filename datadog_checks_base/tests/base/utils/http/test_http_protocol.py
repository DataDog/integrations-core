"""Tests for HTTP protocol conformance."""

from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.base.utils.http_protocol import HTTPClientProtocol, HTTPResponseProtocol


class TestHTTPClientProtocol:
    """Test that RequestsWrapper implements HTTPClientProtocol."""

    def test_requests_wrapper_implements_protocol(self):
        """RequestsWrapper should implement HTTPClientProtocol."""
        wrapper = RequestsWrapper({}, {})
        assert isinstance(wrapper, HTTPClientProtocol)

    def test_protocol_has_required_methods(self):
        """HTTPClientProtocol requires all HTTP methods."""
        wrapper = RequestsWrapper({}, {})

        # Verify all methods exist
        assert hasattr(wrapper, 'get')
        assert hasattr(wrapper, 'post')
        assert hasattr(wrapper, 'put')
        assert hasattr(wrapper, 'patch')
        assert hasattr(wrapper, 'delete')
        assert hasattr(wrapper, 'head')
        assert hasattr(wrapper, 'options_method')

        # Verify methods are callable
        assert callable(wrapper.get)
        assert callable(wrapper.post)

    def test_protocol_has_required_properties(self):
        """HTTPClientProtocol requires options and session properties."""
        wrapper = RequestsWrapper({}, {})

        assert hasattr(wrapper, 'options')
        assert isinstance(wrapper.options, dict)

        assert hasattr(wrapper, 'session')
        assert hasattr(wrapper, '_session')


class TestHTTPResponseProtocol:
    """Test that responses implement HTTPResponseProtocol."""

    def test_protocol_attributes_defined(self):
        """HTTPResponseProtocol should have all required type annotations."""
        # Verify protocol has required annotations
        annotations = HTTPResponseProtocol.__annotations__
        assert 'status_code' in annotations
        assert 'content' in annotations
        assert 'text' in annotations
        assert 'headers' in annotations

    def test_protocol_is_runtime_checkable(self):
        """HTTPResponseProtocol should be runtime checkable."""
        assert hasattr(HTTPResponseProtocol, '__instancecheck__')

    def test_protocol_has_close_method(self):
        """HTTPResponseProtocol should require close() method for resource cleanup."""
        import requests

        # Verify requests.Response has close() method (production code relies on this)
        response = requests.Response()
        assert hasattr(response, 'close')
        assert callable(response.close)
