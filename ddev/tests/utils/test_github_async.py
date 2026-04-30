"""Tests for the async GitHub API client."""

from __future__ import annotations

import dataclasses
import io
import json
import zipfile
from typing import Any

import httpx
import pytest

from ddev.utils.github_async import (
    GITHUB_API_VERSION,
    ArtifactsList,
    AsyncGitHubClient,
    GitHubResponse,
    IssueComment,
    PaginationData,
    PullRequestReviewComment,
    WorkflowDispatchResult,
    WorkflowRun,
    async_github_client,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOKEN = "ghp_test_token"


def _json_response(data: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    all_headers = {"content-type": "application/json"}
    if headers:
        all_headers.update(headers)
    return httpx.Response(status_code, json=data, headers=all_headers)


def _make_client(handler: httpx.MockTransport | None = None) -> AsyncGitHubClient:
    transport = handler or httpx.MockTransport(lambda r: httpx.Response(200))
    return AsyncGitHubClient(token=TOKEN, transport=transport)


def _artifact(idx: int) -> dict[str, Any]:
    return {
        "id": idx,
        "name": f"artifact-{idx}",
        "size_in_bytes": 100 * idx,
        "url": f"https://api.github.com/artifact/{idx}",
        "archive_download_url": f"https://api.github.com/artifact/{idx}/zip",
        "expired": False,
    }


def _workflow_run_payload() -> dict[str, Any]:
    return {
        "id": 42,
        "name": "CI",
        "status": "completed",
        "conclusion": "success",
        "html_url": "https://github.com/owner/repo/actions/runs/42",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T01:00:00Z",
    }


def _issue_comment_payload() -> dict[str, Any]:
    return {
        "id": 1,
        "body": "Hello world",
        "user": {"login": "octocat"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "html_url": "https://github.com/owner/repo/issues/1#issuecomment-1",
    }


def _pr_review_comment_payload() -> dict[str, Any]:
    return {
        "id": 10,
        "body": "Nice change",
        "path": "src/foo.py",
        "commit_id": "abc123",
        "html_url": "https://github.com/owner/repo/pull/1#discussion_r10",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "user": {"login": "reviewer"},
    }


# ---------------------------------------------------------------------------
# PaginationData
# ---------------------------------------------------------------------------

_BASE = "https://api.github.com"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, PaginationData()),
        ("", PaginationData()),
        (f'<{_BASE}/page2>; rel="next"', PaginationData(next=f"{_BASE}/page2")),
        (f'<{_BASE}/page10>; rel="last"', PaginationData(last=f"{_BASE}/page10")),
        (
            f'<{_BASE}/page2>; rel="next", <{_BASE}/page5>; rel="last"',
            PaginationData(next=f"{_BASE}/page2", last=f"{_BASE}/page5"),
        ),
        (
            f'<{_BASE}/page1>; rel="first", <{_BASE}/page1>; rel="prev",'
            f' <{_BASE}/page3>; rel="next", <{_BASE}/page5>; rel="last"',
            PaginationData(first=f"{_BASE}/page1", prev=f"{_BASE}/page1", next=f"{_BASE}/page3", last=f"{_BASE}/page5"),
        ),
        (
            f'<{_BASE}/page1>; rel="prev", <{_BASE}/page5>; rel="last"',
            PaginationData(prev=f"{_BASE}/page1", last=f"{_BASE}/page5"),
        ),
        (f'<{_BASE}/page1>; rel="first"', PaginationData(first=f"{_BASE}/page1")),
    ],
    ids=["none", "blank", "next_only", "last_only", "next_and_last", "all_links", "prev_and_last", "first_only"],
)
def test_pagination_data_from_header(header: str | None, expected: PaginationData) -> None:
    p = PaginationData.from_header(header)
    for f in dataclasses.fields(expected):
        assert getattr(p, f.name) == getattr(expected, f.name)


# ---------------------------------------------------------------------------
# AsyncGitHubClient construction
# ---------------------------------------------------------------------------


def test_client_empty_token_raises() -> None:
    with pytest.raises(ValueError, match="token"):
        AsyncGitHubClient(token="")


def test_client_valid_token_builds_client() -> None:
    client = AsyncGitHubClient(token=TOKEN)
    assert isinstance(client._client, httpx.AsyncClient)
    assert "Bearer ghp_test_token" in client._client.headers.get("authorization", "")  # must not raise


@pytest.mark.asyncio
async def test_client_request_headers() -> None:
    captured: httpx.Headers | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request.headers
        return _json_response(_workflow_run_payload())

    client = _make_client(httpx.MockTransport(handler))
    await client.get_workflow_run("o", "r", 42)

    assert captured is not None
    assert captured["authorization"] == f"Bearer {TOKEN}"
    assert captured["x-github-api-version"] == GITHUB_API_VERSION
    assert captured["accept"] == "application/vnd.github+json"


# ---------------------------------------------------------------------------
# async_github_client context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_yields_client() -> None:
    async with async_github_client(token=TOKEN) as client:
        assert not client._client.is_closed


@pytest.mark.asyncio
async def test_context_manager_closes_on_exit() -> None:
    async with async_github_client(token=TOKEN) as client:
        inner = client._client
    # After exit the underlying client is closed; a new request would fail
    assert inner.is_closed


# ---------------------------------------------------------------------------
# create_workflow_dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_workflow_dispatch_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/actions/workflows/my-workflow.yml/dispatches" in request.url.path
        body = json.loads(request.content)
        assert body["ref"] == "main"
        assert "inputs" not in body
        return _json_response({"workflow_run_id": 999}, headers={"x-ratelimit-remaining": "59"})

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch("owner", "repo", "my-workflow.yml", "main")
    assert isinstance(result, GitHubResponse)
    assert isinstance(result.data, WorkflowDispatchResult)
    assert result.data.workflow_run_id == 999
    assert result.headers.get("x-ratelimit-remaining") == "59"


@pytest.mark.asyncio
async def test_create_workflow_dispatch_with_inputs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["inputs"] == {"env": "prod"}
        return _json_response({"workflow_run_id": 1})

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch("o", "r", 123, "main", inputs={"env": "prod"})
    assert result.data.workflow_run_id == 1


@pytest.mark.asyncio
async def test_create_workflow_dispatch_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_workflow_dispatch("o", "r", "wf.yml", "main")
    assert exc_info.value.response.status_code == 422


# ---------------------------------------------------------------------------
# get_workflow_run
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_workflow_run_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/actions/runs/42" in request.url.path
        return _json_response(_workflow_run_payload())

    client = _make_client(httpx.MockTransport(handler))
    result = await client.get_workflow_run("owner", "repo", 42)
    assert isinstance(result.data, WorkflowRun)
    assert result.data.id == 42
    assert result.data.status == "completed"


@pytest.mark.asyncio
async def test_get_workflow_run_headers_forwarded() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response(_workflow_run_payload(), headers={"x-ratelimit-remaining": "50"})

    client = _make_client(httpx.MockTransport(handler))
    result = await client.get_workflow_run("o", "r", 42)
    assert result.headers.get("x-ratelimit-remaining") == "50"


@pytest.mark.asyncio
async def test_get_workflow_run_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.get_workflow_run("o", "r", 99)
    assert exc_info.value.response.status_code == 404


# ---------------------------------------------------------------------------
# list_workflow_run_artifacts (pagination)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_workflow_run_artifacts_single_page() -> None:
    artifacts = [_artifact(1), _artifact(2)]

    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response({"total_count": 2, "artifacts": artifacts})

    client = _make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_run_artifacts("owner", "repo", 1):
        pages.append(page)

    assert len(pages) == 1
    assert isinstance(pages[0].data, ArtifactsList)
    assert pages[0].data.total_count == 2
    assert len(pages[0].data.artifacts) == 2


@pytest.mark.asyncio
async def test_list_workflow_run_artifacts_two_pages() -> None:
    page1_artifacts = [_artifact(1)]
    page2_artifacts = [_artifact(2)]
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            link = f'<{request.url.scheme}://{request.url.host}/page2>; rel="next"'
            return _json_response(
                {"total_count": 2, "artifacts": page1_artifacts},
                headers={"link": link},
            )
        return _json_response({"total_count": 2, "artifacts": page2_artifacts})

    client = _make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_run_artifacts("owner", "repo", 1):
        pages.append(page)

    assert len(pages) == 2
    assert pages[0].data.artifacts[0].id == 1
    assert pages[1].data.artifacts[0].id == 2


@pytest.mark.asyncio
async def test_list_workflow_run_artifacts_pagination_stops_when_no_next() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response({"total_count": 1, "artifacts": [_artifact(1)]})

    client = _make_client(httpx.MockTransport(handler))
    count = 0
    async for _ in client.list_workflow_run_artifacts("owner", "repo", 1):
        count += 1
    assert count == 1


@pytest.mark.asyncio
async def test_list_workflow_run_artifacts_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(403)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        async for _ in client.list_workflow_run_artifacts("o", "r", 1):
            pass
    assert exc_info.value.response.status_code == 403


@pytest.mark.asyncio
async def test_list_workflow_run_artifacts_per_page_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        return _json_response({"total_count": 0, "artifacts": []})

    client = _make_client(httpx.MockTransport(handler))
    async for _ in client.list_workflow_run_artifacts("owner", "repo", 1, per_page=100):
        pass


# ---------------------------------------------------------------------------
# create_issue_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_issue_comment_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/issues/7/comments" in request.url.path
        body = json.loads(request.content)
        assert body["body"] == "LGTM"
        return _json_response({**_issue_comment_payload(), "body": "LGTM"}, status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_issue_comment("owner", "repo", 7, "LGTM")
    assert isinstance(result.data, IssueComment)
    assert result.data.body == "LGTM"


@pytest.mark.asyncio
async def test_create_issue_comment_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_issue_comment("o", "r", 1, "hi")
    assert exc_info.value.response.status_code == 404


# ---------------------------------------------------------------------------
# create_pr_review_comment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_pr_review_comment_success_with_position() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/pulls/3/comments" in request.url.path
        body = json.loads(request.content)
        assert body["commit_id"] == "abc123"
        assert body["path"] == "src/foo.py"
        assert body["position"] == 5
        assert "line" not in body
        return _json_response(_pr_review_comment_payload(), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment(
        "owner", "repo", 3, "Nice change", "abc123", "src/foo.py", position=5
    )
    assert isinstance(result.data, PullRequestReviewComment)
    assert result.data.commit_id == "abc123"


@pytest.mark.asyncio
async def test_create_pr_review_comment_success_with_line_and_side() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["line"] == 10
        assert body["side"] == "RIGHT"
        assert "position" not in body
        return _json_response(_pr_review_comment_payload(), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment("o", "r", 1, "comment", "abc123", "file.py", line=10, side="RIGHT")
    assert isinstance(result.data, PullRequestReviewComment)


@pytest.mark.asyncio
async def test_create_pr_review_comment_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_pr_review_comment("o", "r", 1, "body", "sha", "path")
    assert exc_info.value.response.status_code == 422


# ---------------------------------------------------------------------------
# Custom timeout per request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_request_timeout_forwarded() -> None:
    """Ensure per-request timeout reaches the transport without raising."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(_workflow_run_payload())

    client = AsyncGitHubClient(token=TOKEN, default_timeout=5.0, transport=httpx.MockTransport(handler))
    result = await client.get_workflow_run("o", "r", 42, timeout=2.0)
    assert result.data.id == 42


# ---------------------------------------------------------------------------
# create_check_run / update_check_run
# ---------------------------------------------------------------------------


def _check_run_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "id": 1,
        "name": "ck",
        "status": "in_progress",
        "head_sha": "abc",
        "conclusion": None,
        "html_url": "https://github.com/o/r/check-runs/1",
    }
    payload.update(overrides)
    return payload


@pytest.mark.asyncio
async def test_create_check_run_success() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/o/r/check-runs" in request.url.path
        captured.update(json.loads(request.content))
        return _json_response(_check_run_payload(name=captured["name"], head_sha=captured["head_sha"]))

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_check_run("o", "r", name="ck", head_sha="abc", status="in_progress")
    assert result.data.id == 1
    assert captured == {"name": "ck", "head_sha": "abc", "status": "in_progress"}


@pytest.mark.asyncio
async def test_create_check_run_with_optional_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return _json_response(_check_run_payload())

    client = _make_client(httpx.MockTransport(handler))
    await client.create_check_run(
        "o",
        "r",
        name="ck",
        head_sha="abc",
        status="in_progress",
        details_url="https://x",
        output={"title": "t", "summary": "s"},
    )
    assert captured["details_url"] == "https://x"
    assert captured["output"] == {"title": "t", "summary": "s"}


@pytest.mark.asyncio
async def test_update_check_run_success() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert "/repos/o/r/check-runs/77" in request.url.path
        captured.update(json.loads(request.content))
        return _json_response(_check_run_payload(id=77, status="completed", conclusion="success"))

    client = _make_client(httpx.MockTransport(handler))
    await client.update_check_run("o", "r", 77, status="completed", conclusion="success")
    assert captured == {"status": "completed", "conclusion": "success"}


@pytest.mark.asyncio
async def test_update_check_run_omits_unset_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return _json_response(_check_run_payload(id=77))

    client = _make_client(httpx.MockTransport(handler))
    await client.update_check_run("o", "r", 77, conclusion="failure")
    assert captured == {"conclusion": "failure"}


# ---------------------------------------------------------------------------
# download_artifact
# ---------------------------------------------------------------------------


def _make_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_download_artifact_token_not_leaked_to_redirect_target(monkeypatch, tmp_path) -> None:
    captured_signed_headers: dict[str, str] = {}

    def github_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"].startswith("Bearer ")
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        captured_signed_headers.update({k.lower(): v for k, v in request.headers.items()})
        return httpx.Response(200, content=_make_zip({"hello.txt": b"hi"}))

    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(signed_handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.httpx.AsyncClient", fake_async_client)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert "authorization" not in captured_signed_headers
    assert (tmp_path / "out" / "hello.txt").read_bytes() == b"hi"


@pytest.mark.asyncio
async def test_download_artifact_non_302_raises(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not a redirect")

    client = _make_client(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPError):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.asyncio
async def test_download_artifact_missing_location_header_raises(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302)

    client = _make_client(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPError, match="Missing Location"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.asyncio
async def test_download_artifact_zip_slip_rejected(monkeypatch, tmp_path) -> None:
    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_make_zip({"../escape.txt": b"pwn"}))

    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(signed_handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.httpx.AsyncClient", fake_async_client)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    dest = tmp_path / "out"
    with pytest.raises(httpx.HTTPError, match="(?i)zip-slip"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", dest)

    assert not (tmp_path / "escape.txt").exists()
