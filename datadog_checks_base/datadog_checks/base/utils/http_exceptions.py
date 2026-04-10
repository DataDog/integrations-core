# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

__all__ = [
    'HTTPError',
    'HTTPRequestError',
    'HTTPStatusError',
    'HTTPTimeoutError',
    'HTTPConnectionError',
    'HTTPSSLError',
]


class HTTPError(Exception):
    def __init__(self, message: str, response: Any = None, request: Any = None):
        super().__init__(message)
        self.response = response
        self.request = request


class HTTPRequestError(HTTPError):
    pass


class HTTPStatusError(HTTPError):
    pass


class HTTPTimeoutError(HTTPRequestError):
    pass


class HTTPConnectionError(HTTPRequestError):
    pass


class HTTPSSLError(HTTPConnectionError):
    pass
