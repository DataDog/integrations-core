# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import re
from collections.abc import Iterator, Mapping
from datetime import timedelta
from functools import lru_cache
from http.client import responses as http_responses
from io import BytesIO
from textwrap import dedent
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

from requests import Response

if TYPE_CHECKING:
    # Imported for static analyzers; runtime access goes through module-level __getattr__.
    from datadog_checks.base.utils.http_exceptions import (  # noqa: F401
        HTTPConnectionError,
        HTTPError,
        HTTPInvalidURLError,
        HTTPRequestError,
        HTTPSSLError,
        HTTPStatusError,
        HTTPTimeoutError,
    )
    from datadog_checks.base.utils.http_protocol import HTTPClient, HTTPResponse


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


class CaseInsensitiveDict(dict):
    """Case-insensitive header dict storing keys lowercased, mirroring httpx's decoded-key semantics."""

    def __init__(self, data=None):
        super().__init__()
        if data:
            for k, v in data.items():
                self[k] = v

    def __setitem__(self, key, value):
        super().__setitem__(key.lower() if isinstance(key, str) else key, value)

    def __getitem__(self, key):
        return super().__getitem__(key.lower() if isinstance(key, str) else key)

    def __contains__(self, key):
        return super().__contains__(key.lower() if isinstance(key, str) else key)

    def __delitem__(self, key):
        super().__delitem__(key.lower() if isinstance(key, str) else key)

    def get(self, key, default=None):
        return super().get(key.lower() if isinstance(key, str) else key, default)

    def pop(self, key, *args):
        return super().pop(key.lower() if isinstance(key, str) else key, *args)

    def update(self, other=(), **kwargs):
        if isinstance(other, Mapping):
            other = {(k.lower() if isinstance(k, str) else k): v for k, v in other.items()}
        elif other:
            other = [(k.lower() if isinstance(k, str) else k, v) for k, v in other]
        kwargs = {k.lower(): v for k, v in kwargs.items()}
        super().update(other, **kwargs)

    def setdefault(self, key, default=None):
        return super().setdefault(key.lower() if isinstance(key, str) else key, default)


class MockHTTPResponseImpl:
    """Rich agnostic mock response; wrapped by the protocol-enforcing MockHTTPResponse."""

    # Parameter order differs from MockResponse; not a compatibility concern since all callers use keyword args.
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
        url: str = '',
        history: list[Any] | None = None,
    ):
        self.url = url

        if json_data is not None:
            content = json.dumps(json_data)
            # Copy to avoid mutating the caller's dict
            headers = dict(headers) if headers is not None else {}
            headers.setdefault('Content-Type', 'application/json')
        elif file_path is not None:
            # Open binary files unchanged across encodings and platform newlines.
            with open(file_path, 'rb') as f:
                content = f.read()

        if normalize_content and (
            (isinstance(content, str) and content.startswith('\n'))
            or (isinstance(content, bytes) and content.startswith(b'\n'))
        ):
            content = dedent(content[1:]) if isinstance(content, str) else content[1:]

        self._content = content.encode('utf-8') if isinstance(content, str) else content
        self.status_code = status_code
        self.headers = CaseInsensitiveDict(headers or {})
        self.cookies = cookies or {}
        self.encoding: str | None = None
        self.elapsed = timedelta(seconds=elapsed_seconds)
        self.history: list[Any] = history if history is not None else []
        self._stream = BytesIO(self._content)

        self.raw = MagicMock()
        self.raw.read = self._stream.read
        self.raw.connection.sock.getpeercert.side_effect = lambda binary_form=False: b'mock-cert' if binary_form else {}

    @property
    def content(self) -> bytes:
        return self._content

    @property
    def text(self) -> str:
        return self._content.decode('utf-8')

    @property
    def ok(self) -> bool:
        # Mirrors requests.Response.ok until production code adopts httpx success helpers.
        return self.status_code < 400

    @property
    def reason(self) -> str:
        return http_responses.get(self.status_code, '')

    @property
    def links(self) -> dict[str, dict[str, str]]:
        """Parse Link header into a dict keyed by rel, matching requests.Response.links."""
        header = self.headers.get('link', '').strip().strip("'\"")
        result: dict[str, dict[str, str]] = {}
        if not header:
            return result
        # Split on ", <" to avoid breaking URLs that contain commas (matches requests behavior)
        for val in re.split(', *<', header):
            try:
                url, params_str = val.split(';', 1)
            except ValueError:
                url, params_str = val, ''
            link: dict[str, str] = {'url': url.strip("<> '\"")}
            for param in params_str.split(';'):
                try:
                    key, value = param.split('=')
                except ValueError:
                    break
                link[key.strip(" '\"")] = value.strip(" '\"")
            key = link.get('rel') or link.get('url')
            if key:
                result[key] = link
        return result

    def json(self, **kwargs: Any) -> Any:
        return json.loads(self.text, **kwargs)

    def raise_for_status(self) -> None:
        from datadog_checks.base.utils.http_exceptions import HTTPStatusError

        if self.status_code >= 400:
            message = (
                f'{self.status_code} Client Error' if self.status_code < 500 else f'{self.status_code} Server Error'
            )
            raise HTTPStatusError(message, response=self)

    def get_peer_cert(self, binary_form: bool = False) -> bytes | dict | None:
        return self.raw.connection.sock.getpeercert(binary_form=binary_form)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        # chunk_size=None means return the entire content as a single chunk (matches requests behavior)
        chunk_size = chunk_size if chunk_size is not None else len(self._content) or 1
        self._stream.seek(0)
        while chunk := self._stream.read(chunk_size):
            # Decode to string when decode_unicode=True (matches requests behavior)
            yield chunk.decode('utf-8') if decode_unicode else chunk

    def __iter__(self) -> Iterator[bytes | str]:
        # requests.Response.__iter__ delegates to iter_content(128); mirror that.
        return self.iter_content(128)

    def iter_lines(
        self, chunk_size: int | None = None, decode_unicode: bool = False, delimiter: bytes | str | None = None
    ) -> Iterator[bytes | str]:
        # Handle string delimiter by converting to bytes
        if isinstance(delimiter, str):
            delimiter = delimiter.encode('utf-8')
        delimiter = delimiter or b'\n'

        self._stream.seek(0)
        lines = self._stream.read().split(delimiter)
        # bytes.split leaves a trailing empty element when content ends with the delimiter.
        # Strip it to match requests' default splitlines behavior.
        if lines and not lines[-1]:
            lines.pop()
        for line in lines:
            # Decode to string when decode_unicode=True (matches requests behavior)
            yield line.decode('utf-8') if decode_unicode else line

    def close(self) -> None:
        # No-op because buffered mock responses can be reused after close.
        pass

    def __enter__(self) -> 'MockHTTPResponseImpl':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        return None


@lru_cache(maxsize=1)
def protocol_members() -> frozenset[str]:
    """External attribute names allowed on a mock response, derived from HTTPResponse."""
    from datadog_checks.base.utils.http_protocol import HTTPResponse

    members = set(getattr(HTTPResponse, '__annotations__', {}))
    members |= {name for name in vars(HTTPResponse) if not name.startswith('_')}
    return frozenset(members)


class MockHTTPResponse:
    """Protocol-enforcing wrapper: delegates HTTPResponse members, raises AttributeError otherwise."""

    __slots__ = ('__wrapped__',)

    def __init__(self, *args: Any, **kwargs: Any):
        object.__setattr__(self, '__wrapped__', MockHTTPResponseImpl(*args, **kwargs))

    def __getattr__(self, name: str) -> Any:
        # Enforce only the public protocol surface. Leading-underscore names are framework plumbing.
        if not name.startswith('_') and name not in protocol_members():
            raise AttributeError(f"{name!r} is not on the HTTPResponse protocol")
        return getattr(self.__wrapped__, name)

    def __setattr__(self, name: str, value: Any) -> None:
        # Enforce only the public protocol surface. Leading-underscore names are framework plumbing.
        if not name.startswith('_') and name not in protocol_members():
            raise AttributeError(f"cannot set {name!r}: not on the HTTPResponse protocol")
        setattr(self.__wrapped__, name, value)

    def raise_for_status(self) -> None:
        from datadog_checks.base.utils.http_exceptions import HTTPStatusError

        try:
            self.__wrapped__.raise_for_status()
        except HTTPStatusError as exc:
            exc.response = self
            raise

    def __enter__(self) -> 'MockHTTPResponse':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        return None

    def __iter__(self) -> Iterator[bytes | str]:
        return iter(self.__wrapped__)


# Re-export agnostic HTTP exceptions lazily so test setup has one import site without forcing base imports.
AGNOSTIC_EXCEPTIONS = frozenset(
    {
        'HTTPError',
        'HTTPRequestError',
        'HTTPStatusError',
        'HTTPTimeoutError',
        'HTTPConnectionError',
        'HTTPInvalidURLError',
        'HTTPSSLError',
    }
)


def __getattr__(name: str) -> Any:
    if name in AGNOSTIC_EXCEPTIONS:
        try:
            from datadog_checks.base.utils import http_exceptions
        except ImportError:
            raise ImportError('datadog-checks-base is not installed!')

        return getattr(http_exceptions, name)
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def dev_http_client(persist: bool = False, **options: Any) -> 'HTTPClient':
    """Build a real agnostic HTTP client for test fixtures and dev scripts.

    Traffic uses create_http_client, matching the Agent backend across the requests to httpx cutover.
    Prefer this to direct requests calls in test setup code.

    :param persist: Reuse one connection across calls, replacing requests.Session.
    :param options: Client-level request defaults; per-call verb options override these.
    """
    try:
        from datadog_checks.base.utils.http import create_http_client
    except ImportError:
        raise ImportError('datadog-checks-base is not installed!')

    client = create_http_client({}, {})
    client.persist_connections = persist
    if options:
        client.options.update(options)
    return client


def http_get(url: str, **options: Any) -> 'HTTPResponse':
    """One-shot agnostic GET. Use dev_http_client(persist=True) for cross-call connection reuse."""
    return dev_http_client().get(url, **options)


def http_post(url: str, **options: Any) -> 'HTTPResponse':
    """One-shot agnostic POST. See dev_http_client."""
    return dev_http_client().post(url, **options)


def http_head(url: str, **options: Any) -> 'HTTPResponse':
    """One-shot agnostic HEAD. See dev_http_client."""
    return dev_http_client().head(url, **options)


def http_put(url: str, **options: Any) -> 'HTTPResponse':
    """One-shot agnostic PUT. See dev_http_client."""
    return dev_http_client().put(url, **options)


def http_patch(url: str, **options: Any) -> 'HTTPResponse':
    """One-shot agnostic PATCH. See dev_http_client."""
    return dev_http_client().patch(url, **options)


def http_delete(url: str, **options: Any) -> 'HTTPResponse':
    """One-shot agnostic DELETE. See dev_http_client."""
    return dev_http_client().delete(url, **options)
