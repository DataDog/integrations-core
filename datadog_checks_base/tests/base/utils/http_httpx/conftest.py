# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable

import httpx
import pytest


@pytest.fixture
def status_transport_factory() -> Callable[[int, bytes | str], httpx.MockTransport]:
    def _factory(status_code: int, body: bytes | str = b''):
        def handler(_request: httpx.Request) -> httpx.Response:
            if isinstance(body, str):
                return httpx.Response(status_code, text=body)
            return httpx.Response(status_code, content=body)

        return httpx.MockTransport(handler)

    return _factory


@pytest.fixture
def raising_transport_factory() -> Callable[[Exception], httpx.MockTransport]:
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
        _ = request.content
        captured_requests.append(request)
        return httpx.Response(200, json={'ok': True})

    return httpx.MockTransport(handler)
