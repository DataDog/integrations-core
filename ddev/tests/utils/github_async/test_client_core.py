"""Client construction, auth headers, context manager, timeout, and pagination mechanics."""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx
import pytest

from ddev.utils.github_async import GITHUB_API_VERSION, AsyncGitHubClient, PaginationData, async_github_client
from tests.utils.github_async.helpers import TOKEN, json_response, make_client
from tests.utils.github_async.payloads import artifact, workflow_run_payload

BASE = "https://api.github.com"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, PaginationData()),
        ("", PaginationData()),
        (f'<{BASE}/page2>; rel="next"', PaginationData(next=f"{BASE}/page2")),
        (f'<{BASE}/page10>; rel="last"', PaginationData(last=f"{BASE}/page10")),
        (
            f'<{BASE}/page2>; rel="next", <{BASE}/page5>; rel="last"',
            PaginationData(next=f"{BASE}/page2", last=f"{BASE}/page5"),
        ),
        (
            f'<{BASE}/page1>; rel="first", <{BASE}/page1>; rel="prev",'
            f' <{BASE}/page3>; rel="next", <{BASE}/page5>; rel="last"',
            PaginationData(first=f"{BASE}/page1", prev=f"{BASE}/page1", next=f"{BASE}/page3", last=f"{BASE}/page5"),
        ),
        (
            f'<{BASE}/page1>; rel="prev", <{BASE}/page5>; rel="last"',
            PaginationData(prev=f"{BASE}/page1", last=f"{BASE}/page5"),
        ),
        (f'<{BASE}/page1>; rel="first"', PaginationData(first=f"{BASE}/page1")),
    ],
    ids=["none", "blank", "next_only", "last_only", "next_and_last", "all_links", "prev_and_last", "first_only"],
)
def test_pagination_data_from_header(header: str | None, expected: PaginationData) -> None:
    p = PaginationData.from_header(header)
    for f in dataclasses.fields(expected):
        assert getattr(p, f.name) == getattr(expected, f.name)


def test_client_empty_token_raises() -> None:
    with pytest.raises(ValueError, match="token"):
        AsyncGitHubClient(token="")


async def test_client_request_headers() -> None:
    captured: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request.headers
        return json_response(workflow_run_payload())

    client = make_client(httpx.MockTransport(handler))
    await client.get_workflow_run("o", "r", 42)

    assert captured is not None
    assert captured["authorization"] == f"Bearer {TOKEN}"
    assert captured["x-github-api-version"] == GITHUB_API_VERSION


async def test_context_manager_yields_client() -> None:
    async with async_github_client(token=TOKEN) as client:
        assert not client._client.is_closed


async def test_context_manager_closes_on_exit() -> None:
    async with async_github_client(token=TOKEN) as client:
        inner = client._client
    # After exit the underlying client is closed; a new request would fail
    assert inner.is_closed


@pytest.mark.parametrize(
    ("call_kwargs", "expected"),
    [
        pytest.param({"timeout": 2.0}, 2.0, id="per-request-override"),
        pytest.param({}, 5.0, id="constructor-default"),
    ],
)
async def test_request_timeout_forwarded_to_transport(call_kwargs: dict[str, float], expected: float) -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["timeout"] = request.extensions["timeout"]
        return json_response(workflow_run_payload())

    client = AsyncGitHubClient(token=TOKEN, default_timeout=5.0, transport=httpx.MockTransport(handler))
    await client.get_workflow_run("o", "r", 42, **call_kwargs)

    assert captured["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), expected)


async def test_list_workflow_run_artifacts_two_pages() -> None:
    page1_artifacts = [artifact(1)]
    page2_artifacts = [artifact(2)]
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            link = f'<{request.url.scheme}://{request.url.host}/page2>; rel="next"'
            return json_response(
                {"total_count": 2, "artifacts": page1_artifacts},
                headers={"link": link},
            )
        return json_response({"total_count": 2, "artifacts": page2_artifacts})

    client = make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_run_artifacts("owner", "repo", 1):
        pages.append(page)

    assert len(pages) == 2
    assert pages[0].data.artifacts[0].id == 1
    assert pages[1].data.artifacts[0].id == 2
