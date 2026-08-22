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

from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError


class CaseInsensitiveDict(dict):
    """Dict with case-insensitive string keys stored lowercased."""

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

    def __eq__(self, other):
        # Plain dict equality would report false differences for header casing.
        if isinstance(other, Mapping):
            return dict(self) == {(k.lower() if isinstance(k, str) else k): v for k, v in other.items()}
        return NotImplemented


def encoding_from_content_type(content_type: str | None) -> str | None:
    """Match production Content-Type charset selection."""
    if not content_type:
        return None

    media_type, _, parameter_text = content_type.partition(';')
    for parameter in parameter_text.split(';'):
        name, sep, value = parameter.partition('=')
        if sep and name.strip().lower() == 'charset':
            return value.strip('"\' ')

    if 'text' in media_type.lower():
        return 'ISO-8859-1'
    if 'application/json' in media_type.lower():
        return 'utf-8'
    return None


class MockHTTPResponseImpl:
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
            headers = dict(headers) if headers is not None else {}
            headers.setdefault('Content-Type', 'application/json')
        elif file_path is not None:
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
        self.encoding: str | None = encoding_from_content_type(self.headers.get('content-type'))
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
        # Keep fixtures without Content-Type independent of content guessing.
        return content.decode(self.encoding or 'utf-8', errors='replace')

    @property
    def ok(self) -> bool:
        # Match requests.Response.ok.
        return self.status_code < 400

    def __bool__(self) -> bool:
        # Match production response truthiness.
        return self.ok

    @property
    def reason(self) -> str:
        return http_responses.get(self.status_code, '')

    @property
    def links(self) -> dict[str, dict[str, str]]:
        """Parse Link headers by rel, matching requests.Response.links."""
        header = self.headers.get('link', '').strip().strip("'\"")
        result: dict[str, dict[str, str]] = {}
        if not header:
            return result
        # Preserve commas inside URLs, matching requests.
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
        if self.status_code >= 400:
            message = (
                f'{self.status_code} Client Error' if self.status_code < 500 else f'{self.status_code} Server Error'
            )
            raise HTTPClientStatusError(message, response=self)

    def get_peer_cert(self, binary_form: bool = False) -> bytes | dict | None:
        return self.raw.connection.sock.getpeercert(binary_form=binary_form)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        chunk_size = chunk_size if chunk_size is not None else len(self._content) or 1
        self._stream.seek(0)
        # Without a known charset, decode_unicode still yields bytes.
        decoder = (
            codecs.getincrementaldecoder(self.encoding)(errors='replace') if decode_unicode and self.encoding else None
        )
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
        if not content:
            return

        if decode_unicode and self.encoding:
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

        yield from lines

    def close(self) -> None:
        # Buffered responses remain reusable across mock returns.
        pass

    def __enter__(self) -> 'MockHTTPResponseImpl':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        return None


@lru_cache(maxsize=1)
def protocol_members() -> frozenset[str]:
    """Return HTTPResponse attributes allowed on the mock."""
    from datadog_checks.base.utils.http_protocol import HTTPResponse

    members = set(getattr(HTTPResponse, '__annotations__', {}))
    members |= {name for name in vars(HTTPResponse) if not name.startswith('_')}
    return frozenset(members)


class MockHTTPResponse:
    """Expose only HTTPResponse members from the wrapped mock."""

    __slots__ = ('__wrapped__',)

    def __init__(self, *args: Any, **kwargs: Any):
        object.__setattr__(self, '__wrapped__', MockHTTPResponseImpl(*args, **kwargs))

    def __getattr__(self, name: str) -> Any:
        if not name.startswith('_') and name not in protocol_members():
            raise AttributeError(f"{name!r} is not on the HTTPResponse protocol")
        return getattr(self.__wrapped__, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if not name.startswith('_') and name not in protocol_members():
            raise AttributeError(f"cannot set {name!r}: not on the HTTPResponse protocol")
        setattr(self.__wrapped__, name, value)

    def raise_for_status(self) -> None:
        try:
            self.__wrapped__.raise_for_status()
        except HTTPClientStatusError as exc:
            exc.response = self
            raise

    def __enter__(self) -> 'MockHTTPResponse':
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None:
        self.close()
        return None

    def __iter__(self) -> Iterator[bytes | str]:
        return iter(self.__wrapped__)

    def __bool__(self) -> bool:
        # Dunder lookups skip __getattr__, so truthiness has to be forwarded by hand.
        return bool(self.__wrapped__)


def __getattr__(name: str) -> Any:
    # Lazy import keeps requests out of this module; http_legacy explains why MockResponse remains.
    if name == 'MockResponse':
        import warnings

        from datadog_checks.dev.http_legacy import MockResponse

        warnings.warn(
            'datadog_checks.dev.http.MockResponse is deprecated and will be removed in a future release. '
            'Use MockHTTPResponse, which mocks the backend-agnostic HTTPResponse protocol, once your '
            'integration runs against a datadog-checks-base that exposes it.',
            DeprecationWarning,
            stacklevel=2,
        )
        return MockResponse

    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
