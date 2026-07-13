# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, MutableMapping
from typing import Any, Iterator, Protocol, runtime_checkable

# Frozen backend-neutral HTTP surface. RequestsWrapper implements it on requests today; a future
# HTTPX2Wrapper implements the same surface on httpx. Do not change existing methods, attributes,
# or their semantics without coordinating both backends. Capabilities expose behavior, never a
# backend object (no requests or httpx type is returned).


@runtime_checkable
class HTTPResponseProtocol(Protocol):
    status_code: int
    content: bytes
    text: str
    headers: Mapping[str, str]

    @property
    def ok(self) -> bool: ...
    @property
    def reason(self) -> str: ...

    def json(self, **kwargs: Any) -> Any: ...
    def raise_for_status(self) -> None: ...
    def close(self) -> None: ...
    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]: ...
    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]: ...
    def __enter__(self) -> HTTPResponseProtocol: ...
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool | None: ...
    def __iter__(self) -> Iterator[bytes | str]: ...


class HTTPRequest(Protocol):
    # Mutable view of an outgoing request handed to an auth hook. A hook adds entries to headers
    # or params. Each backend applies those onto its native request. url is provided for
    # inspection only, such as request signing. Writing to url is not guaranteed to be honored.
    # Hooks must not rely on it.
    url: str
    headers: MutableMapping[str, str]
    params: MutableMapping[str, str]


class HTTPRequestAuth(ABC):
    # Backend-neutral auth hook that contributes headers or params to an outgoing request.
    # RequestsWrapper adapts it to requests.auth.AuthBase today. A future HTTPX2Wrapper adapts it
    # to httpx.Auth. Reactive challenge-response schemes (digest, kerberos, ntlm) stay in the
    # auth_type dispatch, not here.
    @abstractmethod
    def __call__(self, request: HTTPRequest) -> None:
        """Contribute headers or params to the outgoing request in place."""


class HTTPClientProtocol(Protocol):
    options: dict[str, Any]

    # Whether the client trusts environment config (proxies, auth, CA bundles).
    trust_env: bool

    def get(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def post(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def head(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def put(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def patch(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def delete(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def options_method(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def get_header(self, name: str, default: str | None = None) -> str | None: ...
    def set_header(self, name: str, value: str) -> None: ...

    # Close any open connections. Idempotent (safe to call repeatedly or before any connection was
    # opened); the client stays usable and reconnects on the next request.
    def close(self) -> None: ...

    # Look up a persisted cookie by name, returning its value (or default) as a plain string.
    def get_cookie(self, name: str, default: str | None = None) -> str | None: ...
