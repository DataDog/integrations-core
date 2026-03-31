"""Tests for the async GitHub API client."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from ddev.utils.github_async import (
    ArtifactsList,
    AsyncGitHubClient,
    GitHubResponse,
    IssueComment,
    PaginationData,
    PullRequestReviewComment,
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


# ---------------------------------------------------------------------------
# PaginationData
# ---------------------------------------------------------------------------


class TestPaginationData:
    def test_empty_header(self) -> None:
        p = PaginationData.from_header(None)
        assert p.first is None
        assert p.prev is None
        assert p.next is None
        assert p.last is None

    def test_blank_header(self) -> None:
        p = PaginationData.from_header("")
        assert p.next is None

    def test_only_next(self) -> None:
        header = '<https://api.github.com/page2>; rel="next"'
        p = PaginationData.from_header(header)
        assert p.next == "https://api.github.com/page2"
        assert p.prev is None
        assert p.first is None
        assert p.last is None

    def test_only_last(self) -> None:
        header = '<https://api.github.com/page10>; rel="last"'
        p = PaginationData.from_header(header)
        assert p.last == "https://api.github.com/page10"
        assert p.next is None

    def test_next_and_last(self) -> None:
        header = '<https://api.github.com/page2>; rel="next", <https://api.github.com/page5>; rel="last"'
        p = PaginationData.from_header(header)
        assert p.next == "https://api.github.com/page2"
        assert p.last == "https://api.github.com/page5"
        assert p.prev is None
        assert p.first is None

    def test_all_links(self) -> None:
        header = (
            '<https://api.github.com/page1>; rel="first", '
            '<https://api.github.com/page1>; rel="prev", '
            '<https://api.github.com/page3>; rel="next", '
            '<https://api.github.com/page5>; rel="last"'
        )
        p = PaginationData.from_header(header)
        assert p.first == "https://api.github.com/page1"
        assert p.prev == "https://api.github.com/page1"
        assert p.next == "https://api.github.com/page3"
        assert p.last == "https://api.github.com/page5"

    def test_prev_and_last(self) -> None:
        header = '<https://api.github.com/page1>; rel="prev", <https://api.github.com/page5>; rel="last"'
        p = PaginationData.from_header(header)
        assert p.prev == "https://api.github.com/page1"
        assert p.last == "https://api.github.com/page5"
        assert p.next is None
        assert p.first is None

    def test_only_first(self) -> None:
        header = '<https://api.github.com/page1>; rel="first"'
        p = PaginationData.from_header(header)
        assert p.first == "https://api.github.com/page1"
        assert p.next is None


# ---------------------------------------------------------------------------
# AsyncGitHubClient construction
# ---------------------------------------------------------------------------


class TestClientInit:
    def test_empty_token_raises(self) -> None:
        with pytest.raises(ValueError, match="token"):
            AsyncGitHubClient(token="")

    def test_valid_token_builds_client(self) -> None:
        client = AsyncGitHubClient(token=TOKEN)
        assert client._client is not None

    @pytest.mark.asyncio
    async def test_aclose(self) -> None:
        client = AsyncGitHubClient(token=TOKEN)
        await client.aclose()  # must not raise


# ---------------------------------------------------------------------------
# async_github_client context manager
# ---------------------------------------------------------------------------


class TestAsyncGitHubClientContextManager:
    @pytest.mark.asyncio
    async def test_yields_client(self) -> None:
        async with async_github_client(token=TOKEN) as client:
            assert isinstance(client, AsyncGitHubClient)

    @pytest.mark.asyncio
    async def test_closes_on_exit(self) -> None:
        async with async_github_client(token=TOKEN) as client:
            inner = client._client
        # After exit the underlying client is closed; a new request would fail
        assert inner.is_closed


# ---------------------------------------------------------------------------
# Fixtures / transport helpers
# ---------------------------------------------------------------------------


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
# create_workflow_dispatch
# ---------------------------------------------------------------------------


class TestCreateWorkflowDispatch:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert "/actions/workflows/my-workflow.yml/dispatches" in request.url.path
            body = json.loads(request.content)
            assert body["ref"] == "main"
            assert "inputs" not in body
            return httpx.Response(204, headers={"x-ratelimit-remaining": "59"})

        client = _make_client(httpx.MockTransport(handler))
        result = await client.create_workflow_dispatch("owner", "repo", "my-workflow.yml", "main")
        assert isinstance(result, GitHubResponse)
        assert result.data is None
        assert result.headers.get("x-ratelimit-remaining") == "59"

    @pytest.mark.asyncio
    async def test_with_inputs(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["inputs"] == {"env": "prod"}
            return httpx.Response(204)

        client = _make_client(httpx.MockTransport(handler))
        await client.create_workflow_dispatch("o", "r", 123, "main", inputs={"env": "prod"})

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_workflow_dispatch("o", "r", "wf.yml", "main")


# ---------------------------------------------------------------------------
# get_workflow_run
# ---------------------------------------------------------------------------


class TestGetWorkflowRun:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
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
    async def test_headers_forwarded(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _json_response(_workflow_run_payload(), headers={"x-ratelimit-remaining": "50"})

        client = _make_client(httpx.MockTransport(handler))
        result = await client.get_workflow_run("o", "r", 42)
        assert result.headers.get("x-ratelimit-remaining") == "50"

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_workflow_run("o", "r", 99)


# ---------------------------------------------------------------------------
# list_workflow_run_artifacts (pagination)
# ---------------------------------------------------------------------------


class TestListWorkflowRunArtifacts:
    @pytest.mark.asyncio
    async def test_single_page(self) -> None:
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
    async def test_two_pages(self) -> None:
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
    async def test_pagination_stops_when_no_next(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return _json_response({"total_count": 1, "artifacts": [_artifact(1)]})

        client = _make_client(httpx.MockTransport(handler))
        count = 0
        async for _ in client.list_workflow_run_artifacts("owner", "repo", 1):
            count += 1
        assert count == 1

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        client = _make_client(httpx.MockTransport(lambda r: httpx.Response(403)))
        with pytest.raises(httpx.HTTPStatusError):
            async for _ in client.list_workflow_run_artifacts("o", "r", 1):
                pass


# ---------------------------------------------------------------------------
# create_issue_comment
# ---------------------------------------------------------------------------


class TestCreateIssueComment:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert "/issues/7/comments" in request.url.path
            body = json.loads(request.content)
            assert body["body"] == "LGTM"
            return _json_response(_issue_comment_payload(), status_code=201)

        client = _make_client(httpx.MockTransport(handler))
        result = await client.create_issue_comment("owner", "repo", 7, "LGTM")
        assert isinstance(result.data, IssueComment)
        assert result.data.body == "Hello world"

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_issue_comment("o", "r", 1, "hi")


# ---------------------------------------------------------------------------
# create_pr_review_comment
# ---------------------------------------------------------------------------


class TestCreatePrReviewComment:
    @pytest.mark.asyncio
    async def test_success_with_position(self) -> None:
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
    async def test_success_with_line_and_side(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["line"] == 10
            assert body["side"] == "RIGHT"
            assert "position" not in body
            return _json_response(_pr_review_comment_payload(), status_code=201)

        client = _make_client(httpx.MockTransport(handler))
        await client.create_pr_review_comment("o", "r", 1, "comment", "abc123", "file.py", line=10, side="RIGHT")

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
        with pytest.raises(httpx.HTTPStatusError):
            await client.create_pr_review_comment("o", "r", 1, "body", "sha", "path")


# ---------------------------------------------------------------------------
# Custom timeout per request
# ---------------------------------------------------------------------------


class TestPerRequestTimeout:
    @pytest.mark.asyncio
    async def test_timeout_forwarded(self) -> None:
        """Ensure per-request timeout reaches the transport without raising."""

        def handler(request: httpx.Request) -> httpx.Response:
            return _json_response(_workflow_run_payload())

        client = AsyncGitHubClient(token=TOKEN, default_timeout=5.0, transport=httpx.MockTransport(handler))
        result = await client.get_workflow_run("o", "r", 42, timeout=2.0)
        assert result.data.id == 42
