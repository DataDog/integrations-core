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

# Provisional backend-neutral HTTP surface (stabilizes once the httpx backend lands). RequestsWrapper
# implements it on requests today; a future HTTPX2Wrapper implements the same surface on httpx. Do not
# change existing methods, attributes, or their semantics without coordinating both backends.
# Capabilities expose behavior, never a backend object, with one documented exception:
# apply_tls_to_requests_session takes a requests.Session, for third-party libraries that cannot be
# handed anything else. It is provisional and goes away once openstack_controller's SDK backend is
# routed through ApiRest.


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
    # Response headers. Lookup, containment and equality against another mapping MUST all be
    # case-insensitive. The casing reported by iteration, keys(), items() and dict() is
    # backend-defined and MUST NOT be relied on: requests reports wire casing, httpx lowercases.
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
    # Empty bodies yield no records. With default line splitting, one terminal line ending only closes
    # the current record, while complete empty records are preserved. With a custom delimiter, a complete
    # terminal delimiter produces an empty final record, while an incomplete delimiter remains part of
    # the final record.
    # Records are bytes by default; decode_unicode yields text when an encoding is configured or determined.
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
    # Request defaults, a plain mutable dict and public surface: integrations outside this repository
    # read and mutate it directly. A backend MUST populate exactly these keys, which callers index
    # unguarded: auth, cert, headers (mutable, case-insensitive), proxies, timeout as a (connect, read)
    # pair, verify as True/False/CA-bundle-path, allow_redirects.
    # Read per request, not snapshotted: a write after construction MUST affect the next request, and
    # copying it onto a backend client is not enough because httpx has no cert, proxies, verify or
    # allow_redirects attribute.
    options: dict[str, Any]

    # TLS settings keyed by their tls_ prefixed configuration names, for callers that build their own
    # SSL context outside the client. Today the tls integration, for intermediate-certificate discovery.
    tls_config: dict[str, Any]

    # Whether the client trusts environment config (proxies, auth, CA bundles).
    trust_env: bool

    # Suppress the debug log emitted for an unverified HTTPS request. Writable to silence it.
    ignore_tls_warning: bool

    # Reuse a single persistent connection across requests by default. Writable after construction.
    persist_connections: bool

    # Every verb also takes per-request keywords, all of which a backend MUST accept:
    #   params, headers, data, json, auth, cookies, timeout
    #                   override the same key in options for this request. headers REPLACES the
    #                   configured headers rather than adding to them.
    #   verify, cert    per-request TLS. httpx binds TLS to the transport at construction, so a
    #                   backend needs a per-configuration transport cache, not a pass-through.
    #   extra_headers   merged over whichever header set applies, adding without discarding.
    #   stream          defer reading the body so the caller can iterate it, relied on by the
    #                   OpenMetrics scrapers, the kubelet pod-list query and argocd's endless watch.
    #   persist         override persist_connections for this call.
    # Only the first group maps onto an httpx per-request keyword. A backend implements the rest.
    def get(self, url: str, **options: Any) -> HTTPResponse: ...
    def post(self, url: str, **options: Any) -> HTTPResponse: ...
    def head(self, url: str, **options: Any) -> HTTPResponse: ...
    def put(self, url: str, **options: Any) -> HTTPResponse: ...
    def patch(self, url: str, **options: Any) -> HTTPResponse: ...
    def delete(self, url: str, **options: Any) -> HTTPResponse: ...
    # The HTTP OPTIONS verb. Suffixed because ``options`` above is the request-defaults dict.
    def options_method(self, url: str, **options: Any) -> HTTPResponse: ...
    # Case-insensitive. When the same header is held under several spellings, this reports the one
    # the backend will actually send, so a caller can tell a configured value from an unset one.
    def get_header(self, name: str, default: str | None = None) -> str | None: ...
    def set_header(self, name: str, value: str) -> None: ...

    # Suppress all HTTP-level auth (config-derived and environment/.netrc) for later requests, leaving trust_env intact.
    def disable_auth(self) -> None: ...

    # Close any open connections. Idempotent (safe to call repeatedly or before any connection was
    # opened); the client stays usable and reconnects on the next request.
    def close(self) -> None: ...

    # Look up a persisted cookie by name, returning its value as a plain string, or default when the
    # cookie is absent or its name is ambiguous (the same name set for multiple domains or paths). A
    # backend must return default in the ambiguous case rather than raising.
    def get_cookie(self, name: str, default: str | None = None) -> str | None: ...

    # Whether url should bypass any configured proxy under the client's no_proxy rules, False if none match.
    def should_bypass_proxy(self, url: str) -> bool: ...

    # Escape hatch, requests-only. Applies this client's TLS configuration to a requests.Session owned
    # by a third-party library that is hard-bound to requests: today only keystoneauth1, reached through
    # openstack_controller's SDK backend. Scoped to TLS deliberately. Proxies are not covered, because
    # no_proxy is per-host and one shared transport cannot express per-host bypass, so callers set
    # session.proxies themselves.
    # A backend that is not requests-based MUST raise NotImplementedError rather than no-op, which the
    # body below enforces for any backend inheriting from this protocol. Nothing downstream of this
    # call can detect a no-op, so an unimplemented member would drop the caller's TLS options silently.
    def apply_tls_to_requests_session(self, session: requests.Session) -> None:
        raise NotImplementedError('a non-requests backend must not silently skip applying TLS configuration')
