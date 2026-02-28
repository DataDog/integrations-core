# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from io import BytesIO
from typing import Any, Iterator
from unittest.mock import MagicMock

__all__ = ['MockHTTPResponse']


class MockHTTPResponse:
    """Library-agnostic mock HTTP response implementing HTTPResponseProtocol."""

    def __init__(
        self,
        content: str | bytes = '',
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        json_data: Any = None,
        file_path: str | None = None,
        cookies: dict[str, str] | None = None,
        elapsed_seconds: float = 0.1,
        normalize_content: bool = True,
    ):
        if json_data is not None:
            content = json.dumps(json_data)
            # Copy to avoid mutating the caller's dict
            headers = dict(headers) if headers is not None else {}
            headers.setdefault('Content-Type', 'application/json')
        elif file_path is not None:
            # Open in binary mode to handle both text and binary files correctly
            # This prevents encoding errors and platform-specific newline translation
            with open(file_path, 'rb') as f:
                content = f.read()

        if normalize_content and (
            (isinstance(content, str) and content.startswith('\n'))
            or (isinstance(content, bytes) and content.startswith(b'\n'))
        ):
            content = content[1:]

        self._content = content.encode('utf-8') if isinstance(content, str) else content
        self.status_code = status_code
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.cookies = cookies or {}
        self.encoding: str | None = None

        from datetime import timedelta

        self.elapsed = timedelta(seconds=elapsed_seconds)
        self._stream = BytesIO(self._content)

        self.raw = MagicMock()
        self.raw.connection.sock.getpeercert.side_effect = lambda binary_form=False: b'mock-cert' if binary_form else {}

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        return self._content.decode('utf-8')

    def json(self, **kwargs: Any) -> Any:
        return json.loads(self.text, **kwargs)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            from datadog_checks.base.utils.http_exceptions import HTTPStatusError

            message = (
                f'{self.status_code} Client Error' if self.status_code < 500 else f'{self.status_code} Server Error'
            )
            raise HTTPStatusError(message, response=self)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        # chunk_size=None means return the entire content as a single chunk (matches requests behavior)
        chunk_size = chunk_size if chunk_size is not None else len(self._content) or 1
        self._stream.seek(0)
        while chunk := self._stream.read(chunk_size):
            # Decode to string when decode_unicode=True (matches requests behavior)
            yield chunk.decode('utf-8') if decode_unicode else chunk

    def iter_lines(
        self, chunk_size: int | None = None, decode_unicode: bool = False, delimiter: bytes | str | None = None
    ) -> Iterator[bytes | str]:
        # Handle string delimiter by converting to bytes
        if isinstance(delimiter, str):
            delimiter = delimiter.encode('utf-8')
        delimiter = delimiter or b'\n'

        self._stream.seek(0)
        lines = self._stream.read().split(delimiter)
        # bytes.split() produces a trailing empty element when content ends with the
        # delimiter (e.g. b'a\nb\n'.split(b'\n') == [b'a', b'b', b'']). requests uses
        # splitlines() for the default case which does not have this behavior, so we
        # strip the trailing empty element to match.
        if lines and not lines[-1]:
            lines.pop()
        for line in lines:
            # Decode to string when decode_unicode=True (matches requests behavior)
            yield line.decode('utf-8') if decode_unicode else line

    def close(self) -> None:
        # No-op: requests.Response.close() releases the network connection, but
        # content is already buffered in memory. Matching that behaviour here
        # so the same instance can be returned by a mock multiple times.
        pass

    def __enter__(self) -> 'MockHTTPResponse':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        return None
