# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any, Iterator

import httpx

from .http_exceptions import (
    HTTPConnectionError,
    HTTPError,
    HTTPRequestError,
    HTTPStatusError,
    HTTPTimeoutError,
)


def _translate_httpx_error(e: httpx.HTTPError) -> HTTPError:
    if isinstance(e, httpx.HTTPStatusError):
        return HTTPStatusError(str(e), response=e.response, request=e.request)
    if isinstance(e, httpx.TimeoutException):
        return HTTPTimeoutError(str(e), request=e.request)
    if isinstance(e, httpx.ConnectError):
        return HTTPConnectionError(str(e), request=e.request)
    if isinstance(e, httpx.RequestError):
        return HTTPRequestError(str(e), request=e.request)
    return HTTPError(str(e))


class HTTPXResponseAdapter:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._response, name)

    def iter_content(self, chunk_size: int | None = None, decode_unicode: bool = False) -> Iterator[bytes | str]:
        if decode_unicode:
            return self._response.iter_text(chunk_size=chunk_size)
        return self._response.iter_bytes(chunk_size=chunk_size)

    def iter_lines(
        self,
        chunk_size: int | None = None,
        decode_unicode: bool = False,
        delimiter: bytes | str | None = None,
    ) -> Iterator[bytes | str]:
        # httpx.iter_lines() yields str; encode to bytes unless decode_unicode is requested.
        # Note: httpx normalizes \r\n to \n, which differs from requests behavior.
        for line in self._response.iter_lines():
            yield line if decode_unicode else line.encode()

    def raise_for_status(self) -> None:
        try:
            self._response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPStatusError(str(e), response=e.response, request=e.request) from e

    def __enter__(self) -> HTTPXResponseAdapter:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._response.close()


class HTTPXWrapper:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def _request(self, method: str, url: str, **options: Any) -> HTTPXResponseAdapter:
        try:
            return HTTPXResponseAdapter(self._client.request(method, url, **options))
        except httpx.HTTPError as e:
            raise _translate_httpx_error(e) from e
        except httpx.InvalidURL as e:
            # InvalidURL is not a subclass of httpx.HTTPError; catch it separately.
            raise HTTPRequestError(str(e)) from e

    def get(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("GET", url, **options)

    def post(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("POST", url, **options)

    def head(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("HEAD", url, **options)

    def put(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("PUT", url, **options)

    def patch(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("PATCH", url, **options)

    def delete(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("DELETE", url, **options)

    def options_method(self, url: str, **options: Any) -> HTTPXResponseAdapter:
        return self._request("OPTIONS", url, **options)
