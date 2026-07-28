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
    pass


class HTTPStatusError(HTTPError):
    pass


class HTTPTimeoutError(HTTPRequestError):
    pass


class HTTPConnectTimeoutError(HTTPTimeoutError):
    pass


class HTTPReadTimeoutError(HTTPTimeoutError):
    pass


class HTTPConnectionError(HTTPRequestError):
    pass


class HTTPInvalidURLError(HTTPRequestError):
    pass


class HTTPSSLError(HTTPConnectionError):
    pass
