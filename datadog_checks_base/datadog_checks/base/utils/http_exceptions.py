# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datadog_checks.base.utils.http_protocol import HTTPRequest, HTTPResponse

__all__ = [
    'HTTPClientError',
    'HTTPClientRequestError',
    'HTTPClientStatusError',
    'HTTPClientTimeoutError',
    'HTTPClientConnectTimeoutError',
    'HTTPClientReadTimeoutError',
    'HTTPClientConnectionError',
    'HTTPClientInvalidURLError',
    'HTTPClientSSLError',
]


class HTTPClientError(Exception):
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


class HTTPClientRequestError(HTTPClientError):
    """A request that produced no usable response, including unmapped backend failures."""


class HTTPClientStatusError(HTTPClientError):
    """An error status on a received response.

    This is a sibling of HTTPClientRequestError. ``response`` may be None outside ``raise_for_status``.
    """


class HTTPClientTimeoutError(HTTPClientRequestError):
    """A request that exceeded its configured timeout, at either phase."""


class HTTPClientConnectTimeoutError(HTTPClientTimeoutError):
    """A timeout while establishing the connection, before any request was sent."""


class HTTPClientReadTimeoutError(HTTPClientTimeoutError):
    """A timeout waiting for response headers or body data."""


class HTTPClientConnectionError(HTTPClientRequestError):
    """A connection failure, excluding timeouts.

    Ports of ``except requests.ConnectionError`` usually also need ``HTTPClientTimeoutError``.
    """


class HTTPClientInvalidURLError(HTTPClientRequestError):
    """A URL the client rejected before attempting a connection."""


class HTTPClientSSLError(HTTPClientConnectionError):
    """A TLS failure; catch before HTTPClientConnectionError when distinguishing them."""
