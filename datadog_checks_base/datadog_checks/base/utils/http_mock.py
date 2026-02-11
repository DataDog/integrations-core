# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Test helpers for HTTP client and response that implement the HTTP protocols.
Use these to mock self.http or inject responses without referencing requests or httpx,
keeping tests implementation-independent.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterator

from .http_protocol import HTTPResponseProtocol


class HTTPResponseMock:
    """
    Mock HTTP response that satisfies HTTPResponseProtocol.
    Use in tests to provide response data without requests or httpx.
    """

    def __init__(
        self,
        status_code: int = 200,
        content: bytes = b'',
        headers: dict[str, str] | None = None,
        encoding: str | None = None,
        json_data: Any = None,
    ) -> None:
        self._content = content
        self._status_code = status_code
        self._headers = dict(headers or {})
        self._encoding = encoding or 'utf-8'
        self._json_data = json_data

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def headers(self) -> dict[str, str]:
        return self._headers

    @property
    def encoding(self) -> str | None:
        return self._encoding

    @encoding.setter
    def encoding(self, value: str | None) -> None:
        self._encoding = value

    @property
    def status_code(self) -> int:
        return self._status_code

    def iter_content(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
    ) -> Iterator[bytes | str]:
        size = chunk_size or 8192
        enc = self._encoding or 'utf-8'
        for i in range(0, len(self._content), size):
            chunk = self._content[i : i + size]
            yield chunk.decode(enc, errors='replace') if decode_unicode else chunk

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | None = None,
    ) -> Iterator[bytes | str]:
        delim = delimiter if delimiter is not None else b'\n'
        enc = self._encoding or 'utf-8'
        start = 0
        while start < len(self._content):
            end = self._content.find(delim, start)
            if end == -1:
                part = self._content[start:]
                if part:
                    yield part.decode(enc, errors='replace') if decode_unicode else part
                break
            part = self._content[start:end]
            start = end + len(delim)
            yield part.decode(enc, errors='replace') if decode_unicode else part

    def raise_for_status(self) -> None:
        if 400 <= self._status_code:
            from requests.exceptions import HTTPError

            raise HTTPError(
                '{} Client Error for url'.format(self._status_code),
                response=self,
            )

    def close(self) -> None:
        pass

    def json(self, **kwargs: Any) -> Any:
        if self._json_data is not None:
            return self._json_data
        return json.loads(self._content.decode(self._encoding or 'utf-8'), **kwargs)


class _MockSession:
    """Minimal session-like object with close() for RequestWrapperMock.session."""

    def close(self) -> None:
        pass


# Type alias for handler callables: (url, **options) -> HTTPResponseProtocol
_RequestHandler = Callable[..., HTTPResponseProtocol]


def _default_response() -> HTTPResponseMock:
    return HTTPResponseMock(200, content=b'')


class RequestWrapperMock:
    """
    Mock HTTP client that implements HTTPClientProtocol.
    Use in tests to replace check.http so tests do not depend on requests or httpx.

    Pass callables for get, post, etc. (each receives url and **options and returns
    an HTTPResponseProtocol). If a method is not provided, it returns a default 200
    empty response.

    As a context manager with a check instance, patches check._http for the duration:

        with RequestWrapperMock(check, get=lambda url, **kwargs: HTTPResponseMock(200, content=b'...')):
            dd_run_check(check(instance))
    """

    def __init__(
        self,
        check: Any = None,
        *,
        get: _RequestHandler | None = None,
        post: _RequestHandler | None = None,
        head: _RequestHandler | None = None,
        put: _RequestHandler | None = None,
        patch: _RequestHandler | None = None,
        delete: _RequestHandler | None = None,
        options_method: _RequestHandler | None = None,
        default_response: HTTPResponseProtocol | None = None,
    ) -> None:
        self._check = check
        self._handlers = {
            'get': get,
            'post': post,
            'head': head,
            'put': put,
            'patch': patch,
            'delete': delete,
            'options_method': options_method,
        }
        self._default = default_response
        self._saved_http: Any = None
        self.options = {}
        self.session = _MockSession()

    def _response(self, method: str, url: str, **options: Any) -> HTTPResponseProtocol:
        handler = self._handlers.get(method)
        if handler is not None:
            return handler(url, **options)
        if self._default is not None:
            return self._default
        return _default_response()

    def get(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('get', url, **options)

    def post(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('post', url, **options)

    def head(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('head', url, **options)

    def put(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('put', url, **options)

    def patch(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('patch', url, **options)

    def delete(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('delete', url, **options)

    def options_method(self, url: str, **options: Any) -> HTTPResponseProtocol:
        return self._response('options_method', url, **options)

    def handle_auth_token(self, **request: Any) -> None:
        pass

    def __enter__(self) -> RequestWrapperMock:
        if self._check is not None:
            self._saved_http = getattr(self._check, '_http', None)
            self._check._http = self
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._check is not None and self._saved_http is not None:
            self._check._http = self._saved_http
        elif self._check is not None:
            if hasattr(self._check, '_http'):
                del self._check._http
        return None
