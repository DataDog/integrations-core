"""Protocol definitions for HTTP client abstraction.

This module defines protocol interfaces using PEP 544 that enable
library-agnostic HTTP client implementations. These protocols are
compile-time only and have zero runtime overhead.
"""

from typing import Any, Iterator, Protocol, runtime_checkable

__all__ = ['HTTPClientProtocol', 'HTTPResponseProtocol']


@runtime_checkable
class HTTPResponseProtocol(Protocol):
    """Protocol defining the interface for HTTP responses.

    Any HTTP response implementation (requests.Response, httpx.Response,
    or custom mock) must provide these attributes and methods.
    """

    # Core attributes
    status_code: int
    content: bytes
    text: str
    headers: dict[str, Any]

    # Methods
    def json(self, **kwargs: Any) -> Any:
        """Parse response body as JSON."""
        ...  # no cov

    def raise_for_status(self) -> None:
        """Raise exception for 4xx/5xx status codes."""
        ...  # no cov

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes]:
        """Iterate over response content in chunks."""
        ...  # no cov

    def iter_lines(
        self, chunk_size: int | None = None, decode_unicode: bool = False, delimiter: bytes | None = None
    ) -> Iterator[bytes]:
        """Iterate over response content line by line."""
        ...  # no cov

    def close(self) -> None:
        """Close the response and release connection back to pool."""
        ...  # no cov

    # Context manager support
    def __enter__(self) -> 'HTTPResponseProtocol': ...  # no cov

    def __exit__(self, *args: Any) -> None: ...  # no cov


@runtime_checkable
class HTTPClientProtocol(Protocol):
    """Protocol defining the interface for HTTP clients.

    Any HTTP client implementation (RequestsWrapper, HTTPXClient) must
    provide these methods and properties.
    """

    # Properties
    options: dict[str, Any]  # Default request options
    session: Any  # Session object (requests.Session or httpx.Client)
    _session: Any  # Direct session slot for manual lifecycle management

    # HTTP methods
    def get(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP GET request."""
        ...  # no cov

    def post(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP POST request."""
        ...  # no cov

    def head(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP HEAD request."""
        ...  # no cov

    def put(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP PUT request."""
        ...  # no cov

    def patch(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP PATCH request."""
        ...  # no cov

    def delete(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP DELETE request."""
        ...  # no cov

    def options_method(self, url: str, **options: Any) -> HTTPResponseProtocol:
        """Perform HTTP OPTIONS request.

        Note: Named 'options_method' to avoid conflict with Python keyword.
        """
        ...  # no cov
