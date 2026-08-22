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
    """Backend-agnostic HTTP error root under Exception, not OSError or ValueError.

    The client raises compatibility subclasses so existing requests exception handlers still match.
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
    """A request that produced no usable response, including unmapped backend failures."""


class HTTPStatusError(HTTPError):
    """An error status on a received response.

    This is a sibling of HTTPRequestError. ``response`` may be None outside ``raise_for_status``.
    """


class HTTPTimeoutError(HTTPRequestError):
    """A request that exceeded its configured timeout, at either phase."""


class HTTPConnectTimeoutError(HTTPTimeoutError):
    """A timeout while establishing the connection, before any request was sent."""


class HTTPReadTimeoutError(HTTPTimeoutError):
    """A timeout waiting for response headers or body data."""


class HTTPConnectionError(HTTPRequestError):
    """A connection failure, excluding timeouts.

    Ports of ``except requests.ConnectionError`` usually also need ``HTTPTimeoutError``.
    """


class HTTPInvalidURLError(HTTPRequestError):
    """A URL the client rejected before attempting a connection."""


class HTTPSSLError(HTTPConnectionError):
    """A TLS failure; catch before HTTPConnectionError when distinguishing them."""
