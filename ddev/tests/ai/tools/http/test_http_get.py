# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx
import pytest

from ddev.ai.tools.http.http_get import HttpGetTool
from ddev.ai.tools.http.response_store import ResponseStore

from .helpers import RecordingTransport, respond

METRICS_URL = "http://localhost:9090/metrics"


@pytest.mark.parametrize("url", ["ftp://example.com", "example.com", "", "//example.com"])
async def test_invalid_url(url: str, store: ResponseStore):
    result = await HttpGetTool(store).run({"url": url})

    assert result.success is False
    assert "http" in result.error and "https" in result.error


@pytest.mark.parametrize(
    "status_code,body",
    [
        (200, "# HELP requests_total counter\nrequests_total 42"),
        (201, "created"),
        (204, ""),
        (404, "not found"),
        (503, "unavailable"),
    ],
)
async def test_small_response_is_returned_inline(status_code: int, body: str, store: ResponseStore):
    tool = HttpGetTool(store, transport=respond(httpx.Response(status_code, text=body)))

    result = await tool.run({"url": METRICS_URL})

    assert result.success is True
    assert result.data == f"Status: {status_code}\n\n{body}"


async def test_query_is_sent_as_get(store: ResponseStore):
    transport = respond(httpx.Response(200, text="ok"))

    result = await HttpGetTool(store, transport=transport).run(
        {"url": f"{METRICS_URL}?a=1", "query": {"b": "x", "limit": 2, "tag": ["team:core", "env:dev"]}}
    )

    assert result.success is True

    (request,) = transport.requests
    assert request.method == "GET"
    assert request.content == b""
    assert request.url.params.multi_items() == [
        ("a", "1"),
        ("b", "x"),
        ("limit", "2"),
        ("tag", "team:core"),
        ("tag", "env:dev"),
    ]


async def test_redirect_is_not_followed(store: ResponseStore):
    transport = respond(httpx.Response(302, headers={"location": "http://elsewhere/"}))

    result = await HttpGetTool(store, transport=transport).run({"url": METRICS_URL})

    assert len(transport.requests) == 1
    assert result.data.startswith("Status: 302\nRedirect not followed: http://elsewhere/")


async def test_request_timeout(store: ResponseStore):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out")

    result = await HttpGetTool(store, transport=RecordingTransport(handler)).run({"url": METRICS_URL, "timeout": 1.0})

    assert result.success is False
    assert "timed out after 1.0s" in result.error


async def test_request_error(store: ResponseStore):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    result = await HttpGetTool(store, transport=RecordingTransport(handler)).run({"url": METRICS_URL})

    assert result.success is False
    assert "Request failed" in result.error
