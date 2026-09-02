"""Client construction, auth headers, context manager, timeout, and pagination mechanics."""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx
import pytest

from ddev.utils.github_async import GITHUB_API_VERSION, AsyncGitHubClient, PaginationData, async_github_client
from ddev.utils.github_async.client import QUERY_MASK, SHUTDOWN_REQUEST_TIMEOUT, failure_reason, with_query_masked
from ddev.utils.github_async.retry import NO_RETRY
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


@pytest.mark.parametrize(
    ("call_kwargs", "expected"),
    [
        pytest.param({}, SHUTDOWN_REQUEST_TIMEOUT, id="caps-the-default"),
        pytest.param({"timeout": 60.0}, SHUTDOWN_REQUEST_TIMEOUT, id="caps-a-longer-explicit-timeout"),
        pytest.param({"timeout": 0.5}, 0.5, id="keeps-a-shorter-explicit-timeout"),
    ],
)
async def test_shutting_down_caps_how_long_one_request_may_take(call_kwargs: dict[str, float], expected: float) -> None:
    """A cleanup call has to fail in time for the next one to be tried at all.

    The cap applies to an explicit timeout too: a caller asking for longer than the process has left
    would spend the whole window on one request.
    """
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["timeout"] = request.extensions["timeout"]
        return json_response(workflow_run_payload())

    client = AsyncGitHubClient(token=TOKEN, default_timeout=30.0, transport=httpx.MockTransport(handler))
    client.enter_shutdown_mode()

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


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        pytest.param(
            "https://productionresultssa.blob.core.windows.net/zip?se=2026-08-25T15%3A00%3A00Z&sig=abc%2F1%3D&sp=r",
            f"https://productionresultssa.blob.core.windows.net/zip?{QUERY_MASK}",
            id="azure-blob",
        ),
        pytest.param(
            "https://s3.amazonaws.com/zip?X-Amz-Signature=deadbeef&X-Amz-Security-Token=tok",
            f"https://s3.amazonaws.com/zip?{QUERY_MASK}",
            id="s3",
        ),
        pytest.param("https://api.github.com/repos/o/r", "https://api.github.com/repos/o/r", id="no-query"),
    ],
)
def test_a_signed_url_keeps_nothing_of_its_query(url: str, expected: str) -> None:
    """Every parameter of a signed URL exists to sign it, so none of it is safe to keep.

    Which one holds the signature depends on the storage host, and keeping any of them means deciding
    that correctly for a host we have not seen yet.
    """
    assert with_query_masked(url) == expected


def test_a_failed_status_is_reported_without_httpx_quoting_the_url() -> None:
    """httpx builds a status error's message around the full URL, so we build our own from the status.

    Rewriting that message instead would leave the signature one encoding change away from the log.
    """
    request = httpx.Request("GET", "https://blob.example/zip?sig=secret")

    reason = failure_reason(httpx.HTTPStatusError("", request=request, response=httpx.Response(403, request=request)))

    assert reason == "HTTP 403 Forbidden"


def test_a_transport_failure_keeps_the_reason_the_os_gave() -> None:
    """A transport error names why the connection failed, which is the whole of its value."""
    assert failure_reason(httpx.ConnectError("[Errno 61] Connection refused")) == "[Errno 61] Connection refused"


def test_a_transport_failure_that_quotes_a_url_still_loses_the_query() -> None:
    """httpx keeps the URL on `.request` rather than in the message, but that is not ours to rely on."""
    error = httpx.ConnectError("connection to https://signed.example/zip?sig=secret refused")

    assert failure_reason(error) == f"connection to https://signed.example/zip?{QUERY_MASK}"


async def test_a_transport_failure_still_carries_the_request_it_failed_on() -> None:
    """The client adds context to a transport failure without discarding what httpx attached.

    A caller reaching for `exc.request` after a dropped connection would otherwise get
    `RuntimeError: The .request property has not been set` instead of the request.
    """
    client = make_client(httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("refused"))))

    with pytest.raises(httpx.ConnectError) as exc_info:
        await client.get_workflow_run("o", "r", 42, retry=NO_RETRY)

    assert exc_info.value.request.url.path == "/repos/o/r/actions/runs/42"
    assert "GET /repos/o/r/actions/runs/42" in str(exc_info.value)
