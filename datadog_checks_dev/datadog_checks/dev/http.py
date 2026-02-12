# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
HTTP test helpers: MockResponse (requests-based) and protocol-based mocks for implementation-agnostic tests.

Use HTTPResponseMock and RequestWrapperMock when testing code that uses check.http or get_http_handler,
so tests do not depend on requests/httpx and work with either wrapper. Use mock_response / mock_http_response
fixtures (in datadog_checks.dev.plugin.pytest) for the legacy Session.get patch pattern.

When to use which:
- **RequestWrapperMock / HTTPResponseMock**: Use in tests where the *subject under test*
  is a *check* (or any code) that calls ``check.http`` or ``get_http_handler``. Inject
  RequestWrapperMock so the test does not depend on requests/httpx and works with either
  wrapper. Example:
  ``with RequestWrapperMock(check, get=lambda url, **kw: HTTPResponseMock(200, content=b'...')):``
  or ``mock.patch.object(check, 'get_http_handler', return_value=RequestWrapperMock(get=...))``.
- **Legacy base tests:** Tests that target RequestsWrapper itself (e.g. test_api.py,
  test_proxy.py, test_tls_and_certs.py) currently use ``requests.Session.get`` or similar
  patches. They are legacy and will be removed when the requests library is removed; use
  RequestWrapperMock for all new check-level tests.
"""
from __future__ import annotations

import json
from io import BytesIO
from textwrap import dedent
from typing import Any, Callable, Iterator

from requests import Response


class HTTPResponseMock:
    """
    Mock HTTP response that satisfies HTTPResponseProtocol (see datadog_checks.base.utils.http_protocol).
    Use in tests to provide response data without requests or httpx.

    Accepts the same convenience kwargs as MockResponse where applicable: file_path (read into
    content), content (str or bytes), json_data, headers, status_code, encoding. Optional
    normalize_content: if True and content is a str starting with \\n, dedent it.
    """

    def __init__(
        self,
        *args: Any,
        content: bytes | str = b'',
        file_path: str | None = None,
        json_data: Any = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        encoding: str | None = None,
        normalize_content: bool = True,
        **kwargs: Any,
    ) -> None:
        """Accepts MockResponse-style (content first) or HTTPResponseMock(200, content=b'...') (status_code first)."""
        if args and isinstance(args[0], int):
            status_code = args[0]
            content = args[1] if len(args) >= 2 else content
        elif args:
            content = args[0]
        if file_path is not None:
            with open(file_path, 'rb') as f:
                content = f.read()
        elif json_data is not None:
            content = json.dumps(json_data).encode('utf-8')
        elif isinstance(content, str):
            if normalize_content and content.startswith('\n'):
                content = dedent(content[1:])
            content = content.encode('utf-8')
        elif not isinstance(content, bytes):
            content = b''
        self._content = content
        self._status_code = int(status_code) if status_code is not None else 200
        self._headers = dict(headers or {})
        self._encoding = encoding or 'utf-8'
        self._json_data = json_data
        self.raw = BytesIO(self._content)

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

    @property
    def text(self) -> str:
        """Compatibility with code that expects response.text (e.g. MockResponse)."""
        return self._content.decode(self._encoding or 'utf-8', errors='replace')

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
            from datadog_checks.base.utils.http_exceptions import HTTPError

            raise HTTPError(
                '{} Client Error for url'.format(self._status_code),
                response=self,
            )

    def close(self) -> None:
        pass

    def __enter__(self) -> 'HTTPResponseMock':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def json(self, **kwargs: Any) -> Any:
        if self._json_data is not None:
            return self._json_data
        return json.loads(self._content.decode(self._encoding or 'utf-8'), **kwargs)


class _MockSession:
    """Minimal session-like object with close() for RequestWrapperMock.session."""

    def close(self) -> None:
        pass


def _default_response() -> HTTPResponseMock:
    return HTTPResponseMock(200, content=b'')


class RequestWrapperMock:
    """
    Mock HTTP client that implements HTTPClientProtocol (see datadog_checks.base.utils.http_protocol).
    Use in tests to replace check.http or get_http_handler so tests do not depend on requests or httpx.

    Pass callables for get, post, etc. (each receives url and **options and returns an HTTPResponseMock
    or any object satisfying HTTPResponseProtocol). As a context manager with a check instance,
    patches check._http for the duration.
    """

    def __init__(
        self,
        check: Any = None,
        *,
        get: Callable[..., HTTPResponseMock] | None = None,
        post: Callable[..., HTTPResponseMock] | None = None,
        head: Callable[..., HTTPResponseMock] | None = None,
        put: Callable[..., HTTPResponseMock] | None = None,
        patch: Callable[..., HTTPResponseMock] | None = None,
        delete: Callable[..., HTTPResponseMock] | None = None,
        options_method: Callable[..., HTTPResponseMock] | None = None,
        default_response: HTTPResponseMock | None = None,
        ignore_tls_warning: bool = False,
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
        self.ignore_tls_warning = ignore_tls_warning

    def _response(self, method: str, url: str, **options: Any) -> HTTPResponseMock:
        handler = self._handlers.get(method)
        if handler is not None:
            return handler(url, **options)
        if self._default is not None:
            return self._default
        return _default_response()

    def get(self, url: str, **options: Any) -> HTTPResponseMock:
        return self._response('get', url, **options)

    def post(self, url: str, **options: Any) -> HTTPResponseMock:
        return self._response('post', url, **options)

    def head(self, url: str, **options: Any) -> HTTPResponseMock:
        return self._response('head', url, **options)

    def put(self, url: str, **options: Any) -> HTTPResponseMock:
        return self._response('put', url, **options)

    def patch(self, url: str, **options: Any) -> HTTPResponseMock:
        return self._response('patch', url, **options)

    def delete(self, url: str, **options: Any) -> HTTPResponseMock:
        return self._response('delete', url, **options)

    def options_method(self, url: str, **options: Any) -> HTTPResponseMock:
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


class MockResponse(Response):
    def __init__(
        self,
        content='',
        file_path=None,
        json_data=None,
        status_code=200,
        headers=None,
        cookies=None,
        normalize_content=True,
    ):
        super(MockResponse, self).__init__()

        if file_path is not None:
            with open(file_path, 'rb') as f:
                self._content = f.read()
                self.raw = BytesIO(self._content)
        elif json_data is not None:
            self._content = json.dumps(json_data).encode('utf-8')
            self.raw = BytesIO(self._content)
        else:
            # For multi-line string literals
            if normalize_content and content.startswith('\n'):
                content = dedent(content[1:])

            self._content = content.encode('utf-8')
            self.raw = BytesIO(self._content)

        # Add new keyword arguments to set as needed
        self.status_code = status_code

        if headers is not None:
            self.headers.clear()
            self.headers.update(headers)

        if cookies is not None:
            self.cookies.clear()
            self.cookies.update(cookies)
