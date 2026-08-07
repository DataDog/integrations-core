# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base.utils.http_protocol import HTTPRequest, HTTPResponse

__all__ = [
    'HTTPError',
    'HTTPRequestError',
    'HTTPStatusError',
    'HTTPTimeoutError',
    'HTTPConnectTimeoutError',
    'HTTPReadTimeoutError',
    'HTTPConnectionError',
    'HTTPInvalidURLError',
    'HTTPSSLError',
]


class HTTPError(Exception):
    """Root of the backend-agnostic HTTP exception tree.

    Catch this to catch everything the HTTP client can raise. Note that it roots at Exception and not at
    OSError or ValueError, so arms written against the requests tree do not transfer by inheritance.

    The types in this module stay free of any backend import. The client does not raise them directly: it
    raises the subclasses built in ``http.py`` (``_COMPAT_EXCEPTIONS``), which add the matching requests
    classes as extra bases so handlers in checks outside this repository keep matching while requests is
    still the backend. Testing against the types here is unaffected, since those subclasses derive from them.
    """

    def __init__(
        self,
        message: str,
        response: HTTPResponse | None = None,
        request: HTTPRequest | None = None,
    ) -> None:
        super().__init__(message)
        self.response = response
        self.request = request


class HTTPRequestError(HTTPError):
    """A request that never produced a usable response.

    Also the fallthrough type: a backend failure with no more specific agnostic equivalent arrives as a bare
    HTTPRequestError, so an arm naming only the subclasses below can miss it.
    """


class HTTPStatusError(HTTPError):
    """An error status on a response that was received in full.

    This is a sibling of HTTPRequestError, not a subclass, so catching HTTPRequestError does not catch it. The
    response attribute is populated only by the raise_for_status seam. Other seams, notably the auth-token fetch,
    raise it with response set to None, so any status check must guard against that before dereferencing.
    """


class HTTPTimeoutError(HTTPRequestError):
    """A request that exceeded its configured timeout, at either phase."""


class HTTPConnectTimeoutError(HTTPTimeoutError):
    """A timeout while establishing the connection, before any request was sent."""


class HTTPReadTimeoutError(HTTPTimeoutError):
    """A timeout while waiting for response data, whether for the headers or for the body.

    Both read phases collapse into this one type, and code that needs to treat them differently cannot do so
    through the type. requests split them: the header-phase case was ReadTimeout but the body-phase case was
    ConnectionError.
    """


class HTTPConnectionError(HTTPRequestError):
    """A failure to establish or maintain the connection.

    Substantially narrower than requests.ConnectionError, which also carried connect timeouts and body-phase read
    timeouts. Neither reaches this type: they are HTTPConnectTimeoutError and HTTPReadTimeoutError, both of which
    sit under HTTPTimeoutError instead. So an arm ported from except requests.ConnectionError needs
    (HTTPConnectionError, HTTPTimeoutError) to keep catching what it used to, at the cost of newly catching
    header-phase read timeouts.
    """


class HTTPInvalidURLError(HTTPRequestError):
    """A URL the client rejected before attempting a connection."""


class HTTPSSLError(HTTPConnectionError):
    """A TLS handshake or certificate verification failure.

    A subclass of HTTPConnectionError, so it must be tested first where the two are distinguished.
    """
