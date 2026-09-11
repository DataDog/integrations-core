# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Provisional backend-neutral HTTP interfaces.

Coordinate member and semantic changes across implementations until a second backend implements the protocols.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from types import MappingProxyType
from typing import Any, Protocol, TypedDict, Unpack


class HTTPHeaders(Mapping[str, str]):
    """Immutable, case-insensitive HTTP headers."""

    __slots__ = ('_values',)

    def __init__(self, headers: Mapping[str, str]) -> None:
        values = {name.lower(): (name, value) for name, value in headers.items()}
        self._values = MappingProxyType(values)

    def __getitem__(self, name: str) -> str:
        return self._values[name.lower()][1]

    def __iter__(self) -> Iterator[str]:
        return (name for name, _ in self._values.values())

    def __len__(self) -> int:
        return len(self._values)


class HTTPRequest(Protocol):
    @property
    def method(self) -> str | None: ...

    @property
    def url(self) -> str | None: ...

    @property
    def headers(self) -> Mapping[str, str]: ...


@dataclass(frozen=True, slots=True)
class HTTPRequestSnapshot:
    """Backend-neutral request metadata captured when an HTTP error occurs."""

    method: str | None
    url: str | None
    headers: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, 'headers', HTTPHeaders(self.headers))


class HTTPResponse(Protocol):
    @property
    def status_code(self) -> int: ...
    @property
    def content(self) -> bytes: ...
    @property
    def text(self) -> str: ...
    @property
    def headers(self) -> Mapping[str, str]:
        """Case-insensitive headers whose iteration casing is backend-defined."""
        ...

    @property
    def encoding(self) -> str | None: ...
    @encoding.setter
    def encoding(self, value: str | None) -> None: ...
    @property
    def elapsed(self) -> timedelta: ...
    @property
    def cookies(self) -> Mapping[str, str]: ...
    @property
    def links(self) -> Mapping[str, Mapping[str, str]]: ...
    @property
    def url(self) -> str: ...
    @property
    def history(self) -> Sequence[HTTPResponse]: ...
    @property
    def ok(self) -> bool: ...
    @property
    def reason(self) -> str: ...

    def json(self, **kwargs: Any) -> Any: ...
    def raise_for_status(self) -> None: ...
    def close(self) -> None: ...
    def get_peer_cert(self, binary_form: bool = False) -> bytes | dict | None:
        """Return None for plain HTTP or a released connection."""
        ...

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]: ...
    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        """Iterate records with requests-compatible line and delimiter boundaries."""
        ...

    def __enter__(self) -> HTTPResponse: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None: ...
    def __iter__(self) -> Iterator[bytes | str]: ...


class HTTPRequestOptions(TypedDict, total=False):
    params: Mapping[str, Any] | None
    """Query parameters appended to the request URL."""
    headers: Mapping[str, str] | None
    """Headers for this request. Values override configured client headers with matching names."""
    data: Any
    """Request body encoded according to the value's type."""
    json: Any
    """JSON-serializable request body."""
    auth: Any
    """Authentication applied to the request."""
    cookies: Mapping[str, str] | None
    """Cookies sent with the request."""
    timeout: float | tuple[float, float] | None
    """Timeout in seconds, or separate connect and read timeouts."""
    allow_redirects: bool
    """Whether the request should follow redirects."""
    verify: bool | str | None
    """Whether to verify TLS, or the path to a CA bundle."""
    cert: str | tuple[str, str] | None
    """Client certificate, optionally paired with its private key."""
    proxies: Mapping[str, str] | None
    """Proxy URLs keyed by scheme; None uses configured client proxies."""
    extra_headers: Mapping[str, str]
    """Headers merged after configured and per-request headers."""
    stream: bool
    """Whether response body consumption should be deferred."""
    persist: bool
    """Whether this request should use the persistent client."""


class HTTPClient(Protocol):
    options: dict[str, Any]
    """Mutable defaults read by the backend before every request."""

    tls_config: dict[str, Any]
    """TLS settings for callers that build their own SSL context."""

    trust_env: bool

    ignore_tls_warning: bool

    persist_connections: bool

    def get(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform a GET request using :class:`HTTPRequestOptions`."""
        ...

    def post(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform a POST request using :class:`HTTPRequestOptions`."""
        ...

    def head(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform a HEAD request using :class:`HTTPRequestOptions`."""
        ...

    def put(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform a PUT request using :class:`HTTPRequestOptions`."""
        ...

    def patch(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform a PATCH request using :class:`HTTPRequestOptions`."""
        ...

    def delete(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform a DELETE request using :class:`HTTPRequestOptions`."""
        ...

    def options_method(self, url: str, **options: Unpack[HTTPRequestOptions]) -> HTTPResponse:
        """Perform an OPTIONS request using :class:`HTTPRequestOptions`; suffixed to avoid the defaults attribute."""
        ...

    def get_header(self, name: str, default: str | None = None) -> str | None:
        """Return the wire value using case-insensitive lookup."""
        ...

    def set_header(self, name: str, value: str) -> None: ...

    # TODO: This currently has no callers; VoltDB and NiFi will use it in their backend-neutral HTTP migrations.
    def disable_auth(self) -> None:
        """Clear configured and .netrc auth without disabling other environment settings."""
        ...

    def close(self) -> None: ...

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        """Return default for missing or ambiguous persisted cookies."""
        ...

    def should_bypass_proxy(self, url: str) -> bool: ...
