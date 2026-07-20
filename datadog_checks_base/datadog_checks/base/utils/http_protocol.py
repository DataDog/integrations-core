# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Iterator, Mapping
from datetime import timedelta
from typing import Any, Protocol

# Provisional backend-neutral HTTP surface (stabilizes once the httpx backend lands). RequestsWrapper
# implements it on requests today; a future HTTPX2Wrapper implements the same surface on httpx. Do not
# change existing methods, attributes, or their semantics without coordinating both backends.
# Capabilities expose behavior, never a backend object (no requests or httpx type is returned).


class HTTPResponse(Protocol):
    status_code: int
    content: bytes
    text: str
    headers: Mapping[str, str]
    # Character encoding used to decode text. None until determined. Writable to force a default.
    encoding: str | None
    # Time elapsed between sending the request and finishing parsing of the response headers.
    elapsed: timedelta
    # Cookies the server set on this response.
    cookies: Mapping[str, str]
    # Parsed Link header, keyed by rel, or by URL when no rel is present.
    links: Mapping[str, Mapping[str, str]]
    # Final URL of the response, after any redirects.
    url: str
    # Redirect responses that led to this one, oldest first.
    history: list[HTTPResponse]

    @property
    def ok(self) -> bool: ...
    @property
    def reason(self) -> str: ...

    def json(self, **kwargs: Any) -> Any: ...
    def raise_for_status(self) -> None: ...
    def close(self) -> None: ...
    # Peer TLS certificate of the connection, or None if not HTTPS or already released.
    def get_peer_cert(self, binary_form: bool = False) -> bytes | dict | None: ...
    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]: ...
    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]: ...
    def __enter__(self) -> HTTPResponse: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None: ...
    def __iter__(self) -> Iterator[bytes | str]: ...


class HTTPClient(Protocol):
    options: dict[str, Any]

    # Whether the client trusts environment config (proxies, auth, CA bundles).
    trust_env: bool

    # Suppress the debug log emitted for an unverified HTTPS request. Writable to silence it.
    ignore_tls_warning: bool

    # Reuse a single persistent connection across requests by default. Writable after construction.
    persist_connections: bool

    # The verb methods also accept persist, overriding persist_connections for that single call.
    def get(self, url: str, **options: Any) -> HTTPResponse: ...
    def post(self, url: str, **options: Any) -> HTTPResponse: ...
    def head(self, url: str, **options: Any) -> HTTPResponse: ...
    def put(self, url: str, **options: Any) -> HTTPResponse: ...
    def patch(self, url: str, **options: Any) -> HTTPResponse: ...
    def delete(self, url: str, **options: Any) -> HTTPResponse: ...
    # The HTTP OPTIONS verb. Suffixed because ``options`` above is the request-defaults dict.
    def options_method(self, url: str, **options: Any) -> HTTPResponse: ...
    def get_header(self, name: str, default: str | None = None) -> str | None: ...
    def set_header(self, name: str, value: str) -> None: ...

    # Close any open connections. Idempotent (safe to call repeatedly or before any connection was
    # opened); the client stays usable and reconnects on the next request.
    def close(self) -> None: ...

    # Look up a persisted cookie by name, returning its value as a plain string, or default when the
    # cookie is absent or its name is ambiguous (the same name set for multiple domains or paths). A
    # backend must return default in the ambiguous case rather than raising.
    def get_cookie(self, name: str, default: str | None = None) -> str | None: ...

    # Whether url should bypass any configured proxy under the client's no_proxy rules, False if none match.
    def should_bypass_proxy(self, url: str) -> bool: ...
