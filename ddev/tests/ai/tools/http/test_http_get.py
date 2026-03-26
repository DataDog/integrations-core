# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from ddev.ai.tools.http.http_get import HttpGetTool

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def http_tool() -> HttpGetTool:
    return HttpGetTool()


def fake_response(status_code: int, text: str = "") -> MagicMock:
    """Fake a HTTP response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.is_success = 200 <= status_code < 300
    return resp


def patch_httpx(response=None, *, side_effect=None):
    """Patch httpx.AsyncClient so tests never hit the network."""
    mock_get = AsyncMock(return_value=response, side_effect=side_effect)
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get = mock_get
    return patch("ddev.ai.tools.http.http_get.httpx.AsyncClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


def test_tool_meta(http_tool: HttpGetTool) -> None:
    assert http_tool.name == "http_get"


# ---------------------------------------------------------------------------
# URL validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", ["ftp://example.com", "example.com", "", "//example.com"])
async def test_invalid_url(http_tool: HttpGetTool, url: str) -> None:
    result = await http_tool.run({"url": url})

    assert result.success is False
    assert "http" in result.error and "https" in result.error


# ---------------------------------------------------------------------------
# HTTP responses
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status_code,body",
    [
        (200, "# HELP requests_total counter\nrequests_total 42"),
        (201, "created"),
        (204, ""),
    ],
)
async def test_request_success(http_tool: HttpGetTool, status_code: int, body: str) -> None:
    with patch_httpx(fake_response(status_code, body)):
        result = await http_tool.run({"url": "http://localhost:9090/metrics"})

    assert result.success is True
    assert f"Status: {status_code}" in result.data
    assert body in result.data


@pytest.mark.parametrize("status_code", [400, 404, 500, 503])
async def test_request_non_success_status(http_tool: HttpGetTool, status_code: int) -> None:
    with patch_httpx(fake_response(status_code, "error body")):
        result = await http_tool.run({"url": "http://localhost:9090/metrics"})

    assert result.success is True
    assert f"Status: {status_code}" in result.data


# ---------------------------------------------------------------------------
# Network errors
# ---------------------------------------------------------------------------


async def test_request_timeout(http_tool: HttpGetTool) -> None:
    with patch_httpx(side_effect=httpx.TimeoutException("timed out")):
        result = await http_tool.run({"url": "http://localhost:9090/metrics", "timeout": 1.0})

    assert result.success is False
    assert "timed out after 1.0s" in result.error


async def test_request_error(http_tool: HttpGetTool) -> None:
    with patch_httpx(side_effect=httpx.RequestError("connection refused")):
        result = await http_tool.run({"url": "http://localhost:9090/metrics"})

    assert result.success is False
    assert "Request failed" in result.error


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("status_code", [200, 500])
async def test_response_truncated(http_tool: HttpGetTool, status_code: int) -> None:
    from ddev.ai.tools.core.truncation import MAX_CHARS

    large_body = "x" * (MAX_CHARS + 1000)
    with patch_httpx(fake_response(status_code, large_body)):
        result = await http_tool.run({"url": "http://localhost:9090/metrics"})

    assert result.success is True
    assert result.truncated is True
    assert result.total_size is not None
    assert result.hint is not None
    assert f"Status: {status_code}" in result.data
