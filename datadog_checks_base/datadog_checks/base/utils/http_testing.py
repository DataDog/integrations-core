"""Testing utilities for HTTP client mocking.

This module provides library-agnostic mock implementations for HTTP responses
that don't depend on requests or httpx libraries.
"""

import json
from io import BytesIO
from typing import Any, Iterator

__all__ = ['MockHTTPResponse']


class MockHTTPResponse:
    """Library-agnostic mock HTTP response.

    Implements HTTPResponseProtocol without depending on requests or httpx.
    Suitable for testing code that works with any HTTP client implementation.

    Args:
        content: Response body as string or bytes
        status_code: HTTP status code (default: 200)
        headers: Response headers dict (default: {})
        json_data: If provided, serializes to JSON and sets content
        file_path: If provided, loads content from file
        cookies: Response cookies dict (default: {})
        elapsed_seconds: Simulated response time (default: 0.1)
        normalize_content: Remove leading newline from content (default: True)

    Examples:
        >>> # Simple text response
        >>> response = MockHTTPResponse(content='{"status": "ok"}', status_code=200)
        >>> response.json()
        {'status': 'ok'}

        >>> # JSON response
        >>> response = MockHTTPResponse(json_data={'user': 'alice'}, status_code=200)
        >>> response.json()
        {'user': 'alice'}

        >>> # Error response
        >>> response = MockHTTPResponse(content='Not Found', status_code=404)
        >>> response.raise_for_status()  # Raises HTTPStatusError

        >>> # Streaming response
        >>> response = MockHTTPResponse(content='chunk1\\nchunk2\\nchunk3')
        >>> list(response.iter_lines())
        [b'chunk1', b'chunk2', b'chunk3']
    """

    def __init__(
        self,
        content: str | bytes = '',
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        file_path: str | None = None,
        cookies: dict[str, str] | None = None,
        elapsed_seconds: float = 0.1,
        normalize_content: bool = True,
    ):
        # Handle different content sources
        if json_data is not None:
            content = json.dumps(json_data)
            if headers is None:
                headers = {}
            headers.setdefault('Content-Type', 'application/json')
        elif file_path is not None:
            with open(file_path) as f:
                content = f.read()

        # Normalize content (remove leading newline from multi-line strings)
        if normalize_content and isinstance(content, str) and content.startswith('\n'):
            content = content[1:]

        # Store as bytes internally
        if isinstance(content, str):
            self._content = content.encode('utf-8')
        else:
            self._content = content

        # Public attributes
        self.status_code = status_code
        self.headers = headers or {}
        self.cookies = cookies or {}

        # Simulated timing
        from datetime import timedelta

        self.elapsed = timedelta(seconds=elapsed_seconds)

        # Raw stream for iter_content/iter_lines
        self._stream = BytesIO(self._content)
        self._stream_consumed = False

        # Mock raw response object (for integrations that access response.raw)
        self.raw = type(
            'MockRaw',
            (),
            {
                'connection': type(
                    'MockConnection',
                    (),
                    {
                        'sock': type(
                            'MockSocket',
                            (),
                            {'getpeercert': lambda binary_form=False: b'mock-cert' if binary_form else {}},
                        )()
                    },
                )()
            },
        )()

    @property
    def content(self) -> bytes:
        """Response body as bytes."""
        return self._content

    @property
    def text(self) -> str:
        """Response body as string."""
        return self._content.decode('utf-8')

    def json(self, **kwargs: Any) -> Any:
        """Parse response body as JSON.

        Args:
            **kwargs: Passed to json.loads()

        Returns:
            Parsed JSON data

        Raises:
            json.JSONDecodeError: If content is not valid JSON
        """
        return json.loads(self.text, **kwargs)

    def raise_for_status(self) -> None:
        """Raise exception for 4xx/5xx status codes.

        Raises:
            HTTPStatusError: For status codes >= 400
        """
        if self.status_code >= 400:
            from datadog_checks.base.utils.http_exceptions import HTTPStatusError

            message = (
                f'{self.status_code} Client Error' if self.status_code < 500 else f'{self.status_code} Server Error'
            )
            raise HTTPStatusError(message, response=self)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes]:
        """Iterate over response content in chunks.

        Args:
            chunk_size: Size of each chunk (default: 1 for compatibility)
            decode_unicode: Not implemented (kept for API compatibility)

        Yields:
            Chunks of response content as bytes
        """
        if chunk_size is None:
            chunk_size = 1

        # Reset stream if not yet consumed
        if not self._stream_consumed:
            self._stream.seek(0)

        while True:
            chunk = self._stream.read(chunk_size)
            if not chunk:
                break
            yield chunk

        self._stream_consumed = True

    def iter_lines(
        self, chunk_size: int | None = None, decode_unicode: bool = False, delimiter: bytes | None = None
    ) -> Iterator[bytes]:
        """Iterate over response content line by line.

        Args:
            chunk_size: Not used (kept for API compatibility)
            decode_unicode: Not implemented (kept for API compatibility)
            delimiter: Line delimiter (default: b'\\n')

        Yields:
            Lines of response content as bytes
        """
        if delimiter is None:
            delimiter = b'\n'

        # Reset stream if not yet consumed
        if not self._stream_consumed:
            self._stream.seek(0)

        # Read all content and split by delimiter
        content = self._stream.read()
        lines = content.split(delimiter)

        for line in lines:
            if line:  # Skip empty lines
                yield line

        self._stream_consumed = True

    def __enter__(self) -> 'MockHTTPResponse':
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit (cleanup)."""
        self._stream.close()
