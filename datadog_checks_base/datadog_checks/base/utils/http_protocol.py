# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Protocols for the HTTP client wrapper and response, for static type checking only.
Both RequestsWrapper and HTTPXWrapper implement HTTPClientProtocol; ResponseWrapper
and HTTPXResponseAdapter satisfy HTTPResponseProtocol. Keeping these protocols
ensures type checkers and future implementations (e.g. async wrapper) stay consistent.
"""

from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable


@runtime_checkable
class HTTPResponseProtocol(Protocol):
    """
    Protocol for the HTTP response object returned by the wrapper's get/post/etc.
    Satisfied by ResponseWrapper (requests) and HTTPXResponseAdapter (httpx).
    """

    @property
    def content(self) -> bytes: ...
    @property
    def headers(self) -> Any: ...  # requests: CaseInsensitiveDict, httpx: Headers (Mapping-like)
    @property
    def encoding(self) -> str | None: ...
    @encoding.setter
    def encoding(self, value: str | None) -> None: ...
    @property
    def status_code(self) -> int: ...

    def iter_content(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
    ) -> Iterator[bytes | str]: ...
    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | None = None,
    ) -> Iterator[bytes | str]: ...
    def raise_for_status(self) -> None: ...
    def close(self) -> None: ...
    def json(self, **kwargs: Any) -> Any: ...


@runtime_checkable
class HTTPSessionLike(Protocol):
    """Minimal session-like object: has close() for compatibility (e.g. self.http.session.close())."""

    def close(self) -> None: ...


@runtime_checkable
class HTTPClientProtocol(Protocol):
    """
    Protocol for the HTTP client wrapper used by AgentCheck.http.
    Satisfied by RequestsWrapper and HTTPXWrapper so type checkers see a single interface.
    """

    options: dict[str, Any]
    session: HTTPSessionLike

    def get(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def post(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def head(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def put(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def patch(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def delete(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def options_method(self, url: str, **options: Any) -> HTTPResponseProtocol: ...
    def handle_auth_token(self, **request: Any) -> None: ...
