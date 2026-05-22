# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable

import httpx
import pytest


@pytest.fixture
def make_transport() -> Callable[[Callable[[httpx.Request], httpx.Response]], httpx.MockTransport]:
    """Returns a factory for building httpx.MockTransport from a handler callable."""

    def _factory(handler):
        return httpx.MockTransport(handler)

    return _factory


@pytest.fixture
def echo_transport() -> httpx.MockTransport:
    """Mock transport that echoes the request method, URL, headers, and body as JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = b''
        try:
            body = request.content
        except httpx.RequestNotRead:
            pass
        payload = {
            'method': request.method,
            'url': str(request.url),
            'headers': dict(request.headers),
            'body': body.decode('utf-8') if body else '',
        }
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


@pytest.fixture
def status_transport_factory() -> Callable[[int, bytes | str], httpx.MockTransport]:
    """Builds a transport that returns a fixed status code and body."""

    def _factory(status_code: int, body: bytes | str = b''):
        def handler(_request: httpx.Request) -> httpx.Response:
            if isinstance(body, str):
                return httpx.Response(status_code, text=body)
            return httpx.Response(status_code, content=body)

        return httpx.MockTransport(handler)

    return _factory


@pytest.fixture
def json_transport_factory() -> Callable[[dict, int], httpx.MockTransport]:
    def _factory(payload: dict, status_code: int = 200):
        def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code, json=payload)

        return httpx.MockTransport(handler)

    return _factory


@pytest.fixture
def raising_transport_factory() -> Callable[[Exception], httpx.MockTransport]:
    """Builds a transport that raises a given exception when invoked."""

    def _factory(exc: Exception):
        def handler(_request: httpx.Request) -> httpx.Response:
            raise exc

        return httpx.MockTransport(handler)

    return _factory


@pytest.fixture
def captured_requests() -> list[httpx.Request]:
    return []


@pytest.fixture
def capturing_transport(captured_requests: list[httpx.Request]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        # Read the body so tests can inspect it.
        _ = request.content
        captured_requests.append(request)
        return httpx.Response(200, json={'ok': True})

    return httpx.MockTransport(handler)


def parse_basic_auth(header_value: str) -> tuple[str, str]:
    """Decode a Basic auth header value into (user, pass)."""
    import base64

    scheme, _, b64 = header_value.partition(' ')
    assert scheme.lower() == 'basic'
    user_pass = base64.b64decode(b64).decode('utf-8')
    user, _, password = user_pass.partition(':')
    return user, password
