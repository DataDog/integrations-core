# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Shared HTTP exception types used by HTTP client wrappers (RequestsWrapper, HTTPXWrapper)
and by checks (openmetrics, prometheus, etc.) so that code can catch HTTP failures
without depending on requests or httpx.

Use these types in except clauses instead of requests.HTTPError so the codebase
can work with any backend (requests, httpx, or mocks).
"""

from __future__ import annotations


class HTTPError(Exception):
    """
    Raised when an HTTP response has a status code >= 400.

    Compatible with the shape of requests.HTTPError: has a .response attribute
    (satisfying HTTPResponseProtocol) so callers can do response.close(), etc.
    """

    def __init__(self, message: str, response: object = None) -> None:
        super().__init__(message)
        self.response = response


class SSLError(Exception):
    """
    Raised when an SSL/TLS error occurs during the request (e.g. certificate
    verification failure). Used so callers can catch SSL failures without
    depending on requests or httpx.

    Catch this together with ConnectionError and RequestException where
    connection/request failures are handled (e.g. in OpenMetricsBaseCheckV2.check)
    so that both requests-backed and httpx-backed wrappers get consistent
    error handling.
    """
