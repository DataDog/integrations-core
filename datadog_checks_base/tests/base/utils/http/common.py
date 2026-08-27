# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
from collections import OrderedDict, deque
from collections.abc import Iterable, Iterator, Mapping
from http.client import responses as http_reasons
from typing import Any

import requests
from requests.adapters import HTTPAdapter

from datadog_checks.base.utils.http import RequestsWrapper

DEFAULT_OPTIONS = {
    'auth': None,
    'cert': None,
    'headers': OrderedDict(
        [
            ('User-Agent', 'Datadog Agent/0.0.0'),
            ('Accept', '*/*'),
            ('Accept-Encoding', 'gzip, deflate'),
        ]
    ),
    'proxies': None,
    'timeout': (10.0, 10.0),
    'verify': True,
    'allow_redirects': True,
}

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'fixtures')


class RawResponse:
    def __init__(
        self,
        *,
        status_code: int,
        content: bytes,
        headers: Mapping[str, str],
        reason: str,
        content_chunks: Iterable[bytes] | None,
        stream_error: Exception | None,
    ) -> None:
        self.status = status_code
        self.headers = headers
        self.reason = reason
        self.version = 11
        self.closed = False
        self.released = False
        self._content = content
        self._content_chunks = tuple(content_chunks) if content_chunks is not None else None
        self._stream_error = stream_error

    def stream(self, chunk_size: int, decode_content: bool = False) -> Iterator[bytes]:
        if self._content_chunks is None:
            yield from (
                self._content[offset : offset + chunk_size] for offset in range(0, len(self._content), chunk_size)
            )
        else:
            yield from self._content_chunks
        if self._stream_error is not None:
            raise self._stream_error

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class RequestsTransport(HTTPAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.closed = False
        self.requests: list[requests.PreparedRequest] = []
        self.raw_responses: list[RawResponse] = []
        self._outcomes: deque[RawResponse | Exception] = deque()

    def respond(
        self,
        *,
        status_code: int = 200,
        content: bytes = b'',
        headers: Mapping[str, str] | None = None,
        reason: str | None = None,
        content_chunks: Iterable[bytes] | None = None,
        stream_error: Exception | None = None,
    ) -> None:
        self._outcomes.append(
            RawResponse(
                status_code=status_code,
                content=content,
                headers=headers or {},
                reason=http_reasons.get(status_code, '') if reason is None else reason,
                content_chunks=content_chunks,
                stream_error=stream_error,
            )
        )

    def raise_exception(self, error: Exception) -> None:
        self._outcomes.append(error)

    def close(self) -> None:
        self.closed = True
        super().close()

    def send(
        self,
        request: requests.PreparedRequest,
        stream: bool = False,
        timeout: Any = None,
        verify: bool | str = True,
        cert: Any = None,
        proxies: Mapping[str, str] | None = None,
    ) -> requests.Response:
        self.requests.append(request)
        if not self._outcomes:
            raise AssertionError(f'No transport outcome configured for {request.method} {request.url}')

        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            if isinstance(outcome, requests.RequestException) and outcome.request is None:
                outcome.request = request
            raise outcome

        self.raw_responses.append(outcome)
        return self.build_response(request, outcome)


def create_requests_client(transport: RequestsTransport) -> RequestsWrapper:
    session = requests.Session()
    session.mount('http://', transport)
    client = RequestsWrapper({}, {}, session=session)
    client.persist_connections = True
    return client


def get_wire_headers(http, url='http://example.com/hello', **options):
    """Return headers from the prepared outgoing request."""
    transport = RequestsTransport()
    transport.respond()
    http.session.mount('http://', transport)
    http.get(url, persist=True, **options)

    return transport.requests[0].headers
