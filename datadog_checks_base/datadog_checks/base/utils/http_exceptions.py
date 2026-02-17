"""Library-agnostic HTTP exception hierarchy.

This module provides exception classes that abstract away the underlying
HTTP library (requests, httpx). Conversion functions map library-specific
exceptions to these abstractions.
"""

from typing import Any

__all__ = [
    'HTTPError',
    'HTTPRequestError',
    'HTTPStatusError',
    'HTTPTimeoutError',
    'HTTPConnectionError',
    'HTTPSSLError',
    'from_requests_exception',
    'from_httpx_exception',
]


class HTTPError(Exception):
    """Base exception for all HTTP-related errors.

    Attributes:
        response: Optional HTTP response object (if available)
        request: Optional HTTP request object (if available)
    """

    def __init__(self, message: str, response: Any = None, request: Any = None):
        super().__init__(message)
        self.response = response
        self.request = request


class HTTPRequestError(HTTPError):
    """Exception raised when a request cannot be sent.

    Examples: DNS resolution failure, connection refused, protocol errors.
    """

    pass


class HTTPStatusError(HTTPError):
    """Exception raised for HTTP error status codes (4xx, 5xx).

    Similar to requests.HTTPError and httpx.HTTPStatusError.
    """

    pass


class HTTPTimeoutError(HTTPRequestError):
    """Exception raised when a request times out.

    Covers both connection timeout and read timeout.
    """

    pass


class HTTPConnectionError(HTTPRequestError):
    """Exception raised when connection to server fails.

    Examples: connection refused, network unreachable, DNS failure.
    """

    pass


class HTTPSSLError(HTTPConnectionError):
    """Exception raised for SSL/TLS-related errors.

    Examples: certificate verification failure, protocol mismatch.
    """

    pass


def from_requests_exception(exc: Exception) -> HTTPError:
    """Convert requests library exception to HTTPError abstraction.

    Args:
        exc: Exception from requests library

    Returns:
        Corresponding HTTPError subclass

    Examples:
        >>> import requests
        >>> try:
        ...     requests.get('https://invalid-domain-12345.com', timeout=1)
        ... except requests.exceptions.RequestException as e:
        ...     http_error = from_requests_exception(e)
        ...     raise http_error
    """
    import requests.exceptions

    # Get response and request if available
    response = getattr(exc, 'response', None)
    request = getattr(exc, 'request', None)
    message = str(exc)

    # Map to specific exception types
    if isinstance(exc, requests.exceptions.Timeout):
        return HTTPTimeoutError(message, response, request)
    elif isinstance(exc, requests.exceptions.SSLError):
        return HTTPSSLError(message, response, request)
    elif isinstance(exc, requests.exceptions.ConnectionError):
        return HTTPConnectionError(message, response, request)
    elif isinstance(exc, requests.exceptions.HTTPError):
        return HTTPStatusError(message, response, request)
    elif isinstance(exc, requests.exceptions.RequestException):
        return HTTPRequestError(message, response, request)
    else:
        # Fallback for unknown exception types
        return HTTPError(message, response, request)


def from_httpx_exception(exc: Exception) -> HTTPError:
    """Convert httpx library exception to HTTPError abstraction.

    Args:
        exc: Exception from httpx library

    Returns:
        Corresponding HTTPError subclass

    Note:
        This function is prepared for Phase 2+ when httpx is introduced.
        Currently returns generic HTTPError for non-httpx exceptions.

        Coverage: This function is not covered by tests until Phase 2+ when
        httpx integration is implemented. The try block and all exception
        conversion logic will be tested during the httpx migration.

    Examples:
        >>> # Future usage in Phase 2+
        >>> import httpx
        >>> try:
        ...     httpx.get('https://invalid-domain-12345.com', timeout=1)
        ... except httpx.RequestError as e:
        ...     http_error = from_httpx_exception(e)
        ...     raise http_error
    """
    # Coverage note: The following try block is Phase 2+ preparation code
    # and will not be covered by tests until httpx integration begins.
    try:
        import httpx
    except ImportError:
        # httpx not available yet (Phase 1)
        return HTTPError(str(exc))

    # Get response and request if available
    response = getattr(exc, 'response', None)
    request = getattr(exc, 'request', None)
    message = str(exc)

    # Check for SSL/TLS errors by examining the exception chain
    # httpx doesn't have a dedicated SSLError, but ssl.SSLError appears in __cause__
    import ssl

    current_exc = exc
    while current_exc is not None:
        if isinstance(current_exc, ssl.SSLError):
            return HTTPSSLError(message, response, request)
        current_exc = current_exc.__cause__

    # Map to specific exception types
    if isinstance(exc, httpx.TimeoutException):
        return HTTPTimeoutError(message, response, request)
    elif isinstance(exc, httpx.ConnectError):
        return HTTPConnectionError(message, response, request)
    elif isinstance(exc, httpx.HTTPStatusError):
        return HTTPStatusError(message, response, request)
    elif isinstance(exc, httpx.RequestError):
        return HTTPRequestError(message, response, request)
    else:
        return HTTPError(message, response, request)
