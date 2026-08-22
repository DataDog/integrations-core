# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import timedelta
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import requests

# Provisional until a second backend implements it. Coordinate member and semantic changes across implementations.
# apply_tls_to_requests_session is a requests-only keystoneauth1 escape hatch until that path uses ApiRest.


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
    status_code: int
    content: bytes
    text: str
    # Lookup and equality are case-insensitive; iteration casing is backend-defined.
    headers: Mapping[str, str]
    encoding: str | None
    elapsed: timedelta
    cookies: Mapping[str, str]
    links: Mapping[str, Mapping[str, str]]
    url: str
    history: list[HTTPResponse]

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


class HTTPClient(Protocol):
    # Public mutable defaults: auth, cert, headers, proxies, timeout, verify, and allow_redirects.
    # Backends read this mapping for every request so post-construction writes take effect.
    options: dict[str, Any]

    # tls_* settings for callers that build their own SSLContext.
    tls_config: dict[str, Any]

    trust_env: bool

    ignore_tls_warning: bool

    persist_connections: bool

    # Per-request options: params, headers, data, json, auth, cookies, timeout, allow_redirects, verify,
    # cert, extra_headers, stream, and persist. extra_headers merges; headers replaces.
    def get(self, url: str, **options: Any) -> HTTPResponse: ...
    def post(self, url: str, **options: Any) -> HTTPResponse: ...
    def head(self, url: str, **options: Any) -> HTTPResponse: ...
    def put(self, url: str, **options: Any) -> HTTPResponse: ...
    def patch(self, url: str, **options: Any) -> HTTPResponse: ...
    def delete(self, url: str, **options: Any) -> HTTPResponse: ...
    def options_method(self, url: str, **options: Any) -> HTTPResponse:
        """Perform OPTIONS; suffixed to avoid the request-defaults attribute."""
        ...

    def get_header(self, name: str, default: str | None = None) -> str | None:
        """Return the wire value using case-insensitive lookup."""
        ...

    def set_header(self, name: str, value: str) -> None: ...

    def disable_auth(self) -> None:
        """Clear configured and .netrc auth without disabling other environment settings."""
        ...

    def close(self) -> None: ...

    def get_cookie(self, name: str, default: str | None = None) -> str | None:
        """Return default for missing or ambiguous persisted cookies."""
        ...

    def should_bypass_proxy(self, url: str) -> bool: ...

    def apply_tls_to_requests_session(self, session: requests.Session) -> None:
        """Apply TLS to a keystoneauth1 requests session; proxies remain caller-owned."""
        raise NotImplementedError('a non-requests backend must not silently skip applying TLS configuration')
