# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import httpx2
import pytest


@pytest.fixture
def status_transport_factory() -> Callable[[int, bytes | str], httpx2.MockTransport]:
    def _factory(status_code: int, body: bytes | str = b''):
        def handler(_request: httpx2.Request) -> httpx2.Response:
            if isinstance(body, str):
                return httpx2.Response(status_code, text=body)
            return httpx2.Response(status_code, content=body)

        return httpx2.MockTransport(handler)

    return _factory


@pytest.fixture
def raising_transport_factory() -> Callable[[Exception], httpx2.MockTransport]:
    def _factory(exc: Exception):
        def handler(_request: httpx2.Request) -> httpx2.Response:
            raise exc

        return httpx2.MockTransport(handler)

    return _factory


@pytest.fixture
def mid_stream_raising_transport_factory() -> Callable[[Exception], httpx2.MockTransport]:
    def _factory(exc: Exception):
        def body():
            yield b'first\n'
            raise exc

        def handler(_request: httpx2.Request) -> httpx2.Response:
            return httpx2.Response(200, content=body())

        return httpx2.MockTransport(handler)

    return _factory


CA_ENV_VARS = ('REQUESTS_CA_BUNDLE', 'CURL_CA_BUNDLE', 'SSL_CERT_FILE', 'SSL_CERT_DIR')


@pytest.fixture
def clean_ca_env(monkeypatch):
    """Strip CA-bundle env vars so each test controls the CA environment it reads."""
    for name in CA_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


PROXY_ENV_VARS = (
    'HTTP_PROXY',
    'HTTPS_PROXY',
    'ALL_PROXY',
    'NO_PROXY',
    'http_proxy',
    'https_proxy',
    'all_proxy',
    'no_proxy',
    'REQUEST_METHOD',
)


@pytest.fixture
def clean_proxy_env(monkeypatch):
    """Strip proxy-related env vars so each test controls the environment it reads."""
    for name in PROXY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_requests() -> list[httpx2.Request]:
    return []


@pytest.fixture
def capturing_transport(captured_requests: list[httpx2.Request]) -> httpx2.MockTransport:
    def handler(request: httpx2.Request) -> httpx2.Response:
        _ = request.content
        captured_requests.append(request)
        return httpx2.Response(200, json={'ok': True})

    return httpx2.MockTransport(handler)
