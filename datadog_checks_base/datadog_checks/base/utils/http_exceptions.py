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
    'HTTPInvalidURLError',
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
    def __init__(self, message: str, response: Any = None, request: Any = None, status_code: int | None = None):
        super().__init__(message, response=response, request=request)
        self.status_code = status_code


class HTTPTimeoutError(HTTPRequestError):
    pass


class HTTPConnectionError(HTTPRequestError):
    pass


class HTTPInvalidURLError(HTTPRequestError):
    pass


class HTTPSSLError(HTTPConnectionError):
    pass
