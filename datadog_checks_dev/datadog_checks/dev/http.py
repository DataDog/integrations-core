# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import codecs
import json
import re
from collections.abc import Iterator, Mapping
from datetime import timedelta
from functools import lru_cache
from http.client import responses as http_responses
from io import BytesIO
from textwrap import dedent
from typing import Any
from unittest.mock import MagicMock


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
            # Open in binary mode to handle both text and binary files correctly
            # This prevents encoding errors and platform-specific newline translation
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
        return self._decode(self._content)

    def _decode(self, content: bytes) -> str:
        return content.decode(self.encoding or 'utf-8', errors='replace')

    @property
    def ok(self) -> bool:
        # Transitional: mirrors requests.Response.ok for current production code.
        # httpx uses is_success/is_client_error/is_server_error instead.
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
        decoder = codecs.getincrementaldecoder(self.encoding or 'utf-8')(errors='replace') if decode_unicode else None
        while chunk := self._stream.read(chunk_size):
            if decoder is None:
                yield chunk
            elif decoded_chunk := decoder.decode(chunk):
                yield decoded_chunk

        if decoder is not None and (decoded_chunk := decoder.decode(b'', final=True)):
            yield decoded_chunk

    def __iter__(self) -> Iterator[bytes | str]:
        # requests.Response.__iter__ delegates to iter_content(128); mirror that.
        return self.iter_content(128)

    def iter_lines(
        self, chunk_size: int | None = None, decode_unicode: bool = False, delimiter: bytes | str | None = None
    ) -> Iterator[bytes | str]:
        self._stream.seek(0)
        content = self._stream.read()
        if decode_unicode:
            decoded_content = self._decode(content)
            decoded_delimiter = self._decode(delimiter) if isinstance(delimiter, bytes) else delimiter
            lines = (
                decoded_content.splitlines() if decoded_delimiter is None else decoded_content.split(decoded_delimiter)
            )
        else:
            if isinstance(delimiter, str):
                encoder = codecs.getincrementalencoder(self.encoding or 'utf-8')()
                encoder.encode('', final=False)
                encoded_delimiter = encoder.encode(delimiter, final=True)
            else:
                encoded_delimiter = delimiter
            lines = content.splitlines() if encoded_delimiter is None else content.split(encoded_delimiter)

        if lines and not lines[-1]:
            lines.pop()
        yield from lines

    def close(self) -> None:
        # No-op: requests.Response.close() releases the network connection, but
        # content is already buffered in memory. Matching that behaviour here
        # so the same instance can be returned by a mock multiple times.
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
        self.close()
        return None

    def __iter__(self) -> Iterator[bytes | str]:
        return iter(self.__wrapped__)


def get_http_capability(http, key):
    """Resolve a legacy HTTP options key via the HTTPClient capability surface."""
    if key == 'auth':
        return http.get_basic_auth()
    if key == 'timeout':
        timeout = http.default_timeout
        return (timeout.connect, timeout.read)
    if key == 'verify':
        tls = http.tls_config
        return tls.tls_ca_cert if tls.tls_ca_cert else tls.tls_verify
    if key == 'headers':
        return http.get_headers()
    if key == 'proxies':
        http_proxy = http.proxy_for_url('http://example.com')
        https_proxy = http.proxy_for_url('https://example.com')
        if http_proxy is None and https_proxy is None:
            return None
        return {'http': http_proxy or '', 'https': https_proxy or ''}
    if key == 'cert':
        tls = http.tls_config
        if not tls.tls_cert:
            return None
        if tls.tls_private_key:
            return (tls.tls_cert, tls.tls_private_key)
        return tls.tls_cert
    raise KeyError(key)


def assert_http_capability(http, key, expected):
    actual = get_http_capability(http, key)
    assert actual == expected, "Expected {!r} to be {!r} but was {!r}".format(key, expected, actual)


def assert_request_timeout(check, expected, *, attr='_request_timeout'):
    """Assert an integration-local request timeout matches the expected value."""
    from datadog_checks.base.utils.http_protocol import HTTPTimeoutConfig

    timeout = getattr(check, attr)
    if isinstance(expected, tuple):
        assert isinstance(timeout, HTTPTimeoutConfig)
        assert (timeout.connect, timeout.read) == expected
    else:
        assert isinstance(timeout, HTTPTimeoutConfig)
        assert timeout.connect == expected
        assert timeout.read == expected
