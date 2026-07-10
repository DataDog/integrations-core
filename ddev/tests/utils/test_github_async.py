"""Tests for the async GitHub API client."""

from __future__ import annotations

import asyncio
import dataclasses
import io
import json
import time
import zipfile
from typing import Any

import httpx
import pytest
from aiolimiter import AsyncLimiter
from pydantic import ValidationError

from ddev.utils.github_async import (
    GITHUB_API_VERSION,
    AsyncGitHubClient,
    GitHubResponse,
    PaginationData,
    async_github_client,
)
from ddev.utils.github_async.client import github_rate_limit_snapshot
from ddev.utils.github_async.models import (
    ArtifactsList,
    CheckRun,
    CheckRunConclusion,
    CheckRunStatus,
    GitHubUser,
    IssueComment,
    JobStep,
    JobStepStatus,
    Label,
    PullRequest,
    PullRequestRef,
    PullRequestReviewComment,
    PullRequestState,
    WorkflowDispatchResult,
    WorkflowJob,
    WorkflowJobConclusion,
    WorkflowJobsList,
    WorkflowJobStatus,
    WorkflowRun,
)
from ddev.utils.rate_limiting import (
    RATE_LIMIT_TIME_PERIOD,
    BucketEvent,
    BudgetGovernor,
    BudgetSnapshot,
    InstrumentedAsyncLimiter,
    PacingEvent,
    PacingReason,
    RateLimitEvent,
    SecondaryLimitEvent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOKEN = "ghp_test_token"


def json_response(data: Any, status_code: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    all_headers = {"content-type": "application/json"}
    if headers:
        all_headers.update(headers)
    return httpx.Response(status_code, json=data, headers=all_headers)


def make_client(handler: httpx.MockTransport | None = None) -> AsyncGitHubClient:
    transport = handler or httpx.MockTransport(lambda r: httpx.Response(200))
    return AsyncGitHubClient(token=TOKEN, transport=transport)


def artifact(idx: int, expired: bool = False, **extra: Any) -> dict[str, Any]:
    return {
        "id": idx,
        "name": f"artifact-{idx}",
        "size_in_bytes": 100 * idx,
        "url": f"https://api.github.com/artifact/{idx}",
        "archive_download_url": f"https://api.github.com/artifact/{idx}/zip",
        "expired": expired,
        **extra,
    }


def workflow_run_payload(
    id: int = 42,
    name: str = "CI",
    status: str = "completed",
    conclusion: str | None = "success",
    html_url: str = "https://github.com/owner/repo/actions/runs/42",
    created_at: str = "2024-01-01T00:00:00Z",
    updated_at: str = "2024-01-01T01:00:00Z",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "html_url": html_url,
        "created_at": created_at,
        "updated_at": updated_at,
        **extra,
    }


def workflow_job(
    idx: int = 1,
    run_id: int = 42,
    name: str | None = None,
    status: str = "completed",
    conclusion: str | None = "success",
    html_url: str | None = None,
    steps: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": idx,
        "run_id": run_id,
        "name": name if name is not None else f"job-{idx}",
        "status": status,
        "conclusion": conclusion,
        "html_url": html_url if html_url is not None else f"https://github.com/owner/repo/actions/runs/42/job/{idx}",
        "steps": steps
        if steps is not None
        else [{"name": "Run tests", "status": "completed", "conclusion": "success", "number": 1}],
        **extra,
    }


def issue_comment_payload(
    id: int = 1,
    body: str = "Hello world",
    user: dict[str, Any] | None = None,
    created_at: str = "2024-01-01T00:00:00Z",
    updated_at: str = "2024-01-01T00:00:00Z",
    html_url: str = "https://github.com/owner/repo/issues/1#issuecomment-1",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": id,
        "body": body,
        "user": user if user is not None else {"login": "octocat"},
        "created_at": created_at,
        "updated_at": updated_at,
        "html_url": html_url,
        **extra,
    }


def pr_review_comment_payload(
    id: int = 10,
    body: str = "Nice change",
    path: str = "src/foo.py",
    commit_id: str = "abc123",
    html_url: str = "https://github.com/owner/repo/pull/1#discussion_r10",
    created_at: str = "2024-01-01T00:00:00Z",
    updated_at: str = "2024-01-01T00:00:00Z",
    user: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": id,
        "body": body,
        "path": path,
        "commit_id": commit_id,
        "html_url": html_url,
        "created_at": created_at,
        "updated_at": updated_at,
        "user": user if user is not None else {"login": "reviewer"},
        **extra,
    }


# ---------------------------------------------------------------------------
# PaginationData
# ---------------------------------------------------------------------------

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
    assert captured["accept"] == "application/vnd.github+json"


# ---------------------------------------------------------------------------
# async_github_client context manager
# ---------------------------------------------------------------------------


async def test_context_manager_yields_client() -> None:
    async with async_github_client(token=TOKEN) as client:
        assert not client._client.is_closed


async def test_context_manager_closes_on_exit() -> None:
    async with async_github_client(token=TOKEN) as client:
        inner = client._client
    # After exit the underlying client is closed; a new request would fail
    assert inner.is_closed


# ---------------------------------------------------------------------------
# create_workflow_dispatch
# ---------------------------------------------------------------------------


async def test_create_workflow_dispatch_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/actions/workflows/my-workflow.yml/dispatches" in request.url.path
        body = json.loads(request.content)
        assert body["ref"] == "main"
        assert body["return_run_details"] is True
        assert "inputs" not in body
        return json_response(
            {
                "workflow_run_id": 999,
                "run_url": "https://api.github.com/repos/owner/repo/actions/runs/999",
                "html_url": "https://github.com/owner/repo/actions/runs/999",
            },
            headers={"x-ratelimit-remaining": "59"},
        )

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch("owner", "repo", "my-workflow.yml", "main", return_run_details=True)
    assert isinstance(result, GitHubResponse)
    assert isinstance(result.data, WorkflowDispatchResult)
    assert result.data.workflow_run_id == 999
    assert result.headers.get("x-ratelimit-remaining") == "59"


async def test_create_workflow_dispatch_with_inputs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["inputs"] == {"env": "prod"}
        assert body["return_run_details"] is True
        return json_response(
            {
                "workflow_run_id": 1,
                "run_url": "https://api.github.com/repos/o/r/actions/runs/1",
                "html_url": "https://github.com/o/r/actions/runs/1",
            }
        )

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch(
        "o", "r", 123, "main", inputs={"env": "prod"}, return_run_details=True
    )
    assert result.data.workflow_run_id == 1


async def test_create_workflow_dispatch_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_workflow_dispatch("o", "r", "wf.yml", "main")
    assert exc_info.value.response.status_code == 422


async def test_create_workflow_dispatch_return_run_details_parses_response() -> None:
    payload = {
        "workflow_run_id": 987,
        "run_url": "https://api.github.com/repos/o/r/actions/runs/987",
        "html_url": "https://github.com/o/r/actions/runs/987",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["return_run_details"] is True
        return json_response(payload)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch("o", "r", "wf.yml", "main", return_run_details=True)
    assert result.data.workflow_run_id == 987
    assert result.data.html_url == "https://github.com/o/r/actions/runs/987"


async def test_create_workflow_dispatch_omits_return_run_details_when_false() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert "return_run_details" not in body
        return httpx.Response(204)

    client = make_client(httpx.MockTransport(handler))
    await client.create_workflow_dispatch("o", "r", "wf.yml", "main")


# ---------------------------------------------------------------------------
# get_workflow_run
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "is_completed"),
    [("completed", True), ("in_progress", False), ("queued", False)],
    ids=["completed", "in_progress", "queued"],
)
async def test_get_workflow_run_success(status: str, is_completed: bool) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/actions/runs/42" in request.url.path
        return json_response(workflow_run_payload(status=status))

    client = make_client(httpx.MockTransport(handler))
    result = await client.get_workflow_run("owner", "repo", 42)
    assert isinstance(result.data, WorkflowRun)
    assert result.data.id == 42
    assert result.data.status == status
    assert result.data.is_completed is is_completed


async def test_get_workflow_run_headers_forwarded() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response(workflow_run_payload(), headers={"x-ratelimit-remaining": "50"})

    client = make_client(httpx.MockTransport(handler))
    result = await client.get_workflow_run("o", "r", 42)
    assert result.headers.get("x-ratelimit-remaining") == "50"


async def test_get_workflow_run_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.get_workflow_run("o", "r", 99)
    assert exc_info.value.response.status_code == 404


# ---------------------------------------------------------------------------
# list_workflow_run_artifacts (pagination)
# ---------------------------------------------------------------------------


async def test_list_workflow_run_artifacts_single_page() -> None:
    artifacts = [artifact(1), artifact(2)]

    def handler(_: httpx.Request) -> httpx.Response:
        return json_response({"total_count": 2, "artifacts": artifacts})

    client = make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_run_artifacts("owner", "repo", 1):
        pages.append(page)

    assert len(pages) == 1
    assert isinstance(pages[0].data, ArtifactsList)
    assert pages[0].data.total_count == 2
    assert len(pages[0].data.artifacts) == 2


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


async def test_list_workflow_run_artifacts_pagination_stops_when_no_next() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response({"total_count": 1, "artifacts": [artifact(1)]})

    client = make_client(httpx.MockTransport(handler))
    count = 0
    async for _ in client.list_workflow_run_artifacts("owner", "repo", 1):
        count += 1
    assert count == 1


async def test_list_workflow_run_artifacts_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(403)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        async for _ in client.list_workflow_run_artifacts("o", "r", 1):
            pass
    assert exc_info.value.response.status_code == 403


async def test_list_workflow_run_artifacts_per_page_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        return json_response({"total_count": 0, "artifacts": []})

    client = make_client(httpx.MockTransport(handler))
    async for _ in client.list_workflow_run_artifacts("owner", "repo", 1, per_page=100):
        pass


# ---------------------------------------------------------------------------
# list_workflow_jobs (pagination)
# ---------------------------------------------------------------------------


async def test_list_workflow_jobs_single_page() -> None:
    jobs = [workflow_job(1), workflow_job(2, status="in_progress", conclusion=None)]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/actions/runs/42/jobs" in request.url.path
        return json_response({"total_count": 2, "jobs": jobs})

    client = make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_jobs("owner", "repo", 42):
        pages.append(page)

    assert len(pages) == 1
    assert isinstance(pages[0].data, WorkflowJobsList)
    assert pages[0].data.total_count == 2

    first, second = pages[0].data.jobs
    assert isinstance(first, WorkflowJob)
    assert first.status is WorkflowJobStatus.COMPLETED
    assert first.conclusion is WorkflowJobConclusion.SUCCESS
    assert second.status is WorkflowJobStatus.IN_PROGRESS
    assert second.conclusion is None
    assert second.html_url == "https://github.com/owner/repo/actions/runs/42/job/2"

    # A step's status is its own StrEnum; its conclusion has no declared enum (stays str).
    step = first.steps[0]
    assert isinstance(step, JobStep)
    assert step.status is JobStepStatus.COMPLETED


@pytest.mark.parametrize("status", list(WorkflowJobStatus), ids=[s.value for s in WorkflowJobStatus])
async def test_list_workflow_jobs_parses_every_status(status: WorkflowJobStatus) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"total_count": 1, "jobs": [workflow_job(1, status=status.value, conclusion=None)]})

    client = make_client(httpx.MockTransport(handler))
    pages = [page async for page in client.list_workflow_jobs("owner", "repo", 42)]
    assert pages[0].data.jobs[0].status is status


async def test_list_workflow_jobs_unexpected_status_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"total_count": 1, "jobs": [workflow_job(1, status="bogus")]})

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        async for _ in client.list_workflow_jobs("owner", "repo", 42):
            pass


async def test_list_workflow_jobs_two_pages() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            link = f'<{request.url.scheme}://{request.url.host}/page2>; rel="next"'
            return json_response({"total_count": 2, "jobs": [workflow_job(1)]}, headers={"link": link})
        return json_response({"total_count": 2, "jobs": [workflow_job(2)]})

    client = make_client(httpx.MockTransport(handler))
    pages = []
    async for page in client.list_workflow_jobs("owner", "repo", 42):
        pages.append(page)

    assert len(pages) == 2
    assert pages[0].data.jobs[0].id == 1
    assert pages[1].data.jobs[0].id == 2


async def test_list_workflow_jobs_per_page_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["per_page"] == "100"
        return json_response({"total_count": 0, "jobs": []})

    client = make_client(httpx.MockTransport(handler))
    async for _ in client.list_workflow_jobs("owner", "repo", 42, per_page=100):
        pass


# ---------------------------------------------------------------------------
# create_issue_comment
# ---------------------------------------------------------------------------


async def test_create_issue_comment_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/issues/7/comments" in request.url.path
        body = json.loads(request.content)
        assert body["body"] == "LGTM"
        return json_response(issue_comment_payload(body="LGTM"), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_issue_comment("owner", "repo", 7, "LGTM")
    assert isinstance(result.data, IssueComment)
    assert result.data.body == "LGTM"
    assert isinstance(result.data.user, GitHubUser)
    assert result.data.user.login == "octocat"


async def test_create_issue_comment_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_issue_comment("o", "r", 1, "hi")
    assert exc_info.value.response.status_code == 404


# ---------------------------------------------------------------------------
# create_pr_review_comment
# ---------------------------------------------------------------------------


async def test_create_pr_review_comment_success_with_position() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/pulls/3/comments" in request.url.path
        body = json.loads(request.content)
        assert body["commit_id"] == "abc123"
        assert body["path"] == "src/foo.py"
        assert body["position"] == 5
        assert "line" not in body
        return json_response(pr_review_comment_payload(), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment(
        "owner", "repo", 3, "Nice change", "abc123", "src/foo.py", position=5
    )
    assert isinstance(result.data, PullRequestReviewComment)
    assert result.data.commit_id == "abc123"
    assert isinstance(result.data.user, GitHubUser)
    assert result.data.user.login == "reviewer"


async def test_create_pr_review_comment_success_with_line_and_side() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["line"] == 10
        assert body["side"] == "RIGHT"
        assert "position" not in body
        return json_response(pr_review_comment_payload(), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment("o", "r", 1, "comment", "abc123", "file.py", line=10, side="RIGHT")
    assert isinstance(result.data, PullRequestReviewComment)


async def test_create_pr_review_comment_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_pr_review_comment("o", "r", 1, "body", "sha", "path")
    assert exc_info.value.response.status_code == 422


# ---------------------------------------------------------------------------
# create_pull_request
# ---------------------------------------------------------------------------


def pull_request_payload(number: int = 1, html_url: str | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "number": number,
        "html_url": html_url if html_url is not None else f"https://github.com/owner/repo/pull/{number}",
        **extra,
    }


def full_pull_request_payload(
    number: int = 42,
    state: str = "open",
    draft: bool = True,
    merged: bool = False,
    locked: bool = False,
    title: str = "Fix bug",
    body: str = "Backport",
    node_id: str = "PR_kwDOABCD123",
    merge_commit_sha: str | None = None,
    created_at: str = "2026-05-01T00:00:00Z",
    updated_at: str = "2026-05-02T00:00:00Z",
    closed_at: str | None = None,
    merged_at: str | None = None,
    user: dict[str, Any] | None = None,
    assignees: list[dict[str, Any]] | None = None,
    requested_reviewers: list[dict[str, Any]] | None = None,
    labels: list[dict[str, Any]] | None = None,
    head: dict[str, Any] | None = None,
    base: dict[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """A richer PR payload exercising sub-models (user, labels, head/base)."""
    return {
        "id": 9000 + number,
        "number": number,
        "node_id": node_id,
        "url": f"https://api.github.com/repos/owner/repo/pulls/{number}",
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "diff_url": f"https://github.com/owner/repo/pull/{number}.diff",
        "patch_url": f"https://github.com/owner/repo/pull/{number}.patch",
        "state": state,
        "draft": draft,
        "merged": merged,
        "locked": locked,
        "merge_commit_sha": merge_commit_sha,
        "title": title,
        "body": body,
        "user": user
        if user is not None
        else {"id": 1, "login": "octocat", "html_url": "https://github.com/octocat", "type": "User"},
        "assignees": assignees if assignees is not None else [],
        "requested_reviewers": requested_reviewers
        if requested_reviewers is not None
        else [{"id": 2, "login": "reviewer", "type": "User"}],
        "labels": labels
        if labels is not None
        else [
            {"id": 100, "name": "qa/skip-qa", "color": "5319e7"},
            {"id": 101, "name": "backport/7.62.x", "color": "5319e7"},
        ],
        "created_at": created_at,
        "updated_at": updated_at,
        "closed_at": closed_at,
        "merged_at": merged_at,
        "head": head
        if head is not None
        else {"ref": "alice/fix", "sha": "1234567890abcdef00", "label": "alice:alice/fix"},
        "base": base if base is not None else {"ref": "master", "sha": "cafebabe00", "label": "owner:master"},
        **extra,
    }


async def test_create_pull_request_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/owner/repo/pulls" in request.url.path
        body = json.loads(request.content)
        assert body == {
            "title": "Fix bug",
            "head": "alice/fix",
            "base": "master",
            "body": "Fix description",
            "draft": False,
        }
        return json_response(pull_request_payload(number=42), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("owner", "repo", "Fix bug", "alice/fix", "master", "Fix description")
    assert isinstance(result.data, PullRequest)
    assert result.data.number == 42
    assert result.data.html_url == "https://github.com/owner/repo/pull/42"


async def test_create_pull_request_draft_true_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["draft"] is True
        return json_response(pull_request_payload(number=7), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("o", "r", "T", "h", "b", draft=True)
    assert result.data.number == 7


async def test_create_pull_request_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_pull_request("o", "r", "T", "h", "b")
    assert exc_info.value.response.status_code == 422


async def test_create_pull_request_parses_full_response() -> None:
    """Exercises sub-models (GitHubUser, Label, PullRequestRef) end-to-end."""

    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(full_pull_request_payload(number=42), status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("owner", "repo", "Fix bug", "alice/fix", "master")

    pr = result.data
    assert pr.id == 9042
    assert pr.number == 42
    assert pr.state is PullRequestState.OPEN
    assert pr.draft is True
    assert pr.title == "Fix bug"

    assert isinstance(pr.user, GitHubUser)
    assert pr.user.login == "octocat"

    assert [label.name for label in pr.labels] == ["qa/skip-qa", "backport/7.62.x"]
    assert all(isinstance(label, Label) for label in pr.labels)

    assert isinstance(pr.head, PullRequestRef)
    assert pr.head.ref == "alice/fix"
    assert pr.head.sha == "1234567890abcdef00"
    assert isinstance(pr.base, PullRequestRef)
    assert pr.base.ref == "master"

    assert [r.login for r in pr.requested_reviewers] == ["reviewer"]
    assert pr.created_at == "2026-05-01T00:00:00Z"


async def test_create_pull_request_ignores_extra_fields() -> None:
    """Unknown top-level fields in the response must not break parsing."""

    def handler(request: httpx.Request) -> httpx.Response:
        payload = full_pull_request_payload(
            mergeable_state="clean", additions=42, unknown_future_field={"nested": True}
        )
        return json_response(payload, status_code=201)

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("o", "r", "T", "h", "b")
    assert result.data.number == 42


# ---------------------------------------------------------------------------
# get_pull_request
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", list(PullRequestState), ids=[s.value for s in PullRequestState])
async def test_get_pull_request_success(state: PullRequestState) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert "/repos/owner/repo/pulls/5" in request.url.path
        return json_response(full_pull_request_payload(number=5, state=state.value))

    client = make_client(httpx.MockTransport(handler))
    result = await client.get_pull_request("owner", "repo", 5)
    assert isinstance(result.data, PullRequest)
    assert result.data.number == 5
    assert result.data.state is state


async def test_get_pull_request_headers_forwarded() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response(full_pull_request_payload(number=5), headers={"x-ratelimit-remaining": "50"})

    client = make_client(httpx.MockTransport(handler))
    result = await client.get_pull_request("o", "r", 5)
    assert result.headers.get("x-ratelimit-remaining") == "50"


async def test_get_pull_request_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.get_pull_request("o", "r", 5)
    assert exc_info.value.response.status_code == 404


async def test_get_pull_request_unexpected_state_raises() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return json_response(full_pull_request_payload(number=5, state="merged"))

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        await client.get_pull_request("o", "r", 5)


# ---------------------------------------------------------------------------
# add_labels_to_issue
# ---------------------------------------------------------------------------


async def test_add_labels_to_issue_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/owner/repo/issues/3/labels" in request.url.path
        body = json.loads(request.content)
        assert body == {"labels": ["qa/skip-qa", "backport/7.62.x"]}
        return json_response([{"id": 1, "name": "qa/skip-qa"}, {"id": 2, "name": "backport/7.62.x"}], status_code=200)

    client = make_client(httpx.MockTransport(handler))
    result = await client.add_labels_to_issue("owner", "repo", 3, ["qa/skip-qa", "backport/7.62.x"])
    assert [label.name for label in result.data] == ["qa/skip-qa", "backport/7.62.x"]
    assert all(isinstance(label, Label) for label in result.data)


async def test_add_labels_to_issue_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.add_labels_to_issue("o", "r", 1, ["bug"])
    assert exc_info.value.response.status_code == 404


# ---------------------------------------------------------------------------
# Lazy-loading guarantees for the `models` subpackage
# ---------------------------------------------------------------------------


def test_models_subpackage_loads_only_requested_submodule() -> None:
    """Importing one model must not eagerly load every other model submodule.

    Runs each scenario in a clean subprocess so the import effect is observable
    (the parent test process has already loaded everything for other tests).
    """
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent(
        """
        import sys
        from ddev.utils.github_async.models import PullRequest  # noqa: F401

        assert 'ddev.utils.github_async.client' not in sys.modules, 'client module should not be loaded'
        assert 'httpx' not in sys.modules, 'httpx should not be loaded when only models are imported'

        prefix = 'ddev.utils.github_async.models.'
        loaded = sorted(name[len(prefix):] for name in sys.modules if name.startswith(prefix))
        print(','.join(loaded))
        """
    )
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, check=True)
    loaded = set(result.stdout.strip().split(','))

    # `pull_request` and its two type dependencies (`user`, `label`) must load.
    assert {'pull_request', 'user', 'label'} <= loaded
    # Unrelated model submodules must stay unloaded.
    assert 'workflow' not in loaded
    assert 'comment' not in loaded


def test_models_subpackage_unknown_attribute_raises_attribute_error() -> None:
    import ddev.utils.github_async.models as models

    with pytest.raises(AttributeError, match='no attribute'):
        models.NotARealModel  # noqa: B018


# ---------------------------------------------------------------------------
# Custom timeout per request
# ---------------------------------------------------------------------------


async def test_per_request_timeout_forwarded() -> None:
    """Ensure per-request timeout reaches the transport without raising."""

    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(workflow_run_payload())

    client = AsyncGitHubClient(token=TOKEN, default_timeout=5.0, transport=httpx.MockTransport(handler))
    result = await client.get_workflow_run("o", "r", 42, timeout=2.0)
    assert result.data.id == 42


# ---------------------------------------------------------------------------
# Rate limiter wiring in AsyncGitHubClient
# ---------------------------------------------------------------------------


async def test_client_request_without_rate_limiter_goes_through() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(workflow_run_payload())

    async with async_github_client(token=TOKEN, transport=httpx.MockTransport(handler)) as client:
        result = await client.get_workflow_run("o", "r", 42)

    assert result.data.id == 42


async def test_client_request_with_rate_limiter_consumes_token() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(workflow_run_payload())

    real_limiter = AsyncLimiter(max_rate=1, time_period=1000)
    events: list[RateLimitEvent] = []
    rate_limiter = InstrumentedAsyncLimiter(real_limiter, on_event=events.append)

    async with async_github_client(
        token=TOKEN, rate_limiter=rate_limiter, transport=httpx.MockTransport(handler)
    ) as client:
        result = await client.get_workflow_run("o", "r", 42)

    assert result.data.id == 42
    bucket_events = [event for event in events if isinstance(event, BucketEvent)]
    assert bucket_events == [BucketEvent(throttled=False, name="")]
    assert not real_limiter.has_capacity()


async def test_client_request_throttled_when_bucket_exhausted() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(workflow_run_payload())

    # A short time_period lets the second, throttled acquire actually complete instead of
    # blocking forever, so its BucketEvent fires.
    real_limiter = AsyncLimiter(max_rate=1, time_period=0.1)
    events: list[RateLimitEvent] = []
    rate_limiter = InstrumentedAsyncLimiter(real_limiter, on_event=events.append)

    async with async_github_client(
        token=TOKEN, rate_limiter=rate_limiter, transport=httpx.MockTransport(handler)
    ) as client:
        await client.get_workflow_run("o", "r", 42)  # drains the single token

    async with async_github_client(
        token=TOKEN, rate_limiter=rate_limiter, transport=httpx.MockTransport(handler)
    ) as client:
        await client.get_workflow_run("o", "r", 42)  # blocks until the 0.1s period refills it

    bucket_events = [event for event in events if isinstance(event, BucketEvent)]
    assert [event.throttled for event in bucket_events] == [False, True]


# ---------------------------------------------------------------------------
# github_rate_limit_snapshot
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        (
            {
                "x-ratelimit-limit": "5000",
                "x-ratelimit-remaining": "4321",
                "x-ratelimit-reset": "1700000000",
                "retry-after": "30",
            },
            BudgetSnapshot(limit=5000, remaining=4321, reset_at=1700000000.0, retry_after=30.0),
        ),
        (
            {"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "4999"},
            BudgetSnapshot(limit=5000, remaining=4999),
        ),
        ({"x-ratelimit-limit": "5000", "retry-after": "not-a-number"}, BudgetSnapshot(limit=5000)),
        ({"x-ratelimit-limit": "not-a-number"}, None),
        ({"content-type": "application/json"}, None),
    ],
    ids=["all_present", "partial_primary", "non_integer_retry_after", "all_unparseable", "no_ratelimit_headers"],
)
def test_github_rate_limit_snapshot(headers: dict[str, str], expected: BudgetSnapshot | None) -> None:
    assert github_rate_limit_snapshot(httpx.Headers(headers)) == expected


async def test_client_request_observes_rate_limit_headers_into_governor() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            workflow_run_payload(),
            headers={"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "4999", "x-ratelimit-reset": "1700000000"},
        )

    governor = BudgetGovernor()
    rate_limiter = InstrumentedAsyncLimiter(AsyncLimiter(max_rate=1, time_period=1000), budget_governor=governor)

    async with async_github_client(
        token=TOKEN, rate_limiter=rate_limiter, transport=httpx.MockTransport(handler)
    ) as client:
        await client.get_workflow_run("o", "r", 42)

    assert governor.budget.limit == 5000
    assert governor.budget.remaining == 4999
    assert governor.budget.reset_at == 1700000000.0


# ---------------------------------------------------------------------------
# create_check_run / update_check_run
# ---------------------------------------------------------------------------


def check_run_payload(
    id: int = 1,
    name: str = "ck",
    status: str = "in_progress",
    head_sha: str = "abc",
    conclusion: str | None = None,
    html_url: str = "https://github.com/o/r/check-runs/1",
    **extra: Any,
) -> dict[str, Any]:
    return {
        "id": id,
        "name": name,
        "status": status,
        "head_sha": head_sha,
        "conclusion": conclusion,
        "html_url": html_url,
        **extra,
    }


@pytest.mark.asyncio
async def test_create_check_run_success() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/o/r/check-runs" in request.url.path
        captured.update(json.loads(request.content))
        return json_response(check_run_payload(name=captured["name"], head_sha=captured["head_sha"]))

    client = make_client(httpx.MockTransport(handler))
    result = await client.create_check_run("o", "r", name="ck", head_sha="abc", status="in_progress")
    assert isinstance(result.data, CheckRun)
    assert result.data.id == 1
    assert result.data.status is CheckRunStatus.IN_PROGRESS
    assert captured == {"name": "ck", "head_sha": "abc", "status": "in_progress"}


@pytest.mark.asyncio
async def test_create_check_run_with_optional_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return json_response(check_run_payload())

    client = make_client(httpx.MockTransport(handler))
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
async def test_create_check_run_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_check_run("o", "r", name="ck", head_sha="abc", status="in_progress")
    assert exc_info.value.response.status_code == 422


# One case per non-completed status (conclusion is null until completed), plus every
# conclusion (incl. the GitHub-only ``stale``) paired with ``completed``.
CHECK_RUN_RESULT_CASES = [
    *[
        pytest.param(status, None, id=status.value)
        for status in CheckRunStatus
        if status is not CheckRunStatus.COMPLETED
    ],
    *[
        pytest.param(CheckRunStatus.COMPLETED, conclusion, id=f"completed-{conclusion.value}")
        for conclusion in CheckRunConclusion
    ],
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("status", "conclusion"), CHECK_RUN_RESULT_CASES)
async def test_update_check_run_success(status: CheckRunStatus, conclusion: CheckRunConclusion | None) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        assert "/repos/o/r/check-runs/77" in request.url.path
        return json_response(
            check_run_payload(id=77, status=status.value, conclusion=conclusion.value if conclusion else None)
        )

    client = make_client(httpx.MockTransport(handler))
    result = await client.update_check_run("o", "r", 77, status="in_progress")
    assert result.data.status is status
    assert result.data.conclusion is conclusion


@pytest.mark.asyncio
async def test_update_check_run_omits_unset_fields() -> None:
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return json_response(check_run_payload(id=77))

    client = make_client(httpx.MockTransport(handler))
    await client.update_check_run("o", "r", 77, conclusion="failure")
    assert captured == {"conclusion": "failure"}


@pytest.mark.asyncio
async def test_update_check_run_requires_conclusion_when_completed() -> None:
    requested = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requested
        requested = True
        return json_response(check_run_payload())

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="conclusion is required"):
        await client.update_check_run("o", "r", 77, status="completed")
    assert requested is False


@pytest.mark.asyncio
async def test_update_check_run_http_error_raises() -> None:
    client = make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.update_check_run("o", "r", 77, status="in_progress")
    assert exc_info.value.response.status_code == 404


@pytest.mark.asyncio
async def test_update_check_run_unexpected_status_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(check_run_payload(id=77, status="bogus"))

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(ValidationError):
        await client.update_check_run("o", "r", 77, status="in_progress")


# ---------------------------------------------------------------------------
# download_artifact
# ---------------------------------------------------------------------------


def make_zip(members: dict[str, bytes]) -> bytes:
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
        return httpx.Response(200, content=make_zip({"hello.txt": b"hi"}))

    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(signed_handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.client.httpx.AsyncClient", fake_async_client)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert "authorization" not in captured_signed_headers
    assert (tmp_path / "out" / "hello.txt").read_bytes() == b"hi"


@pytest.mark.asyncio
async def test_download_artifact_non_302_raises(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not a redirect")

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPError, match="Expected 302"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.asyncio
async def test_download_artifact_signed_url_error_raises(monkeypatch, tmp_path) -> None:
    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, content=b"expired")

    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(signed_handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.client.httpx.AsyncClient", fake_async_client)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    with pytest.raises(httpx.HTTPStatusError):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.asyncio
async def test_download_artifact_missing_location_header_raises(tmp_path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302)

    client = make_client(httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPError, match="Missing Location"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


@pytest.mark.parametrize(
    "malicious_member",
    [
        pytest.param("../escape.txt", id="parent-traversal"),
        pytest.param("/etc/passwd", id="absolute-path"),
    ],
)
@pytest.mark.asyncio
async def test_download_artifact_zip_slip_rejected(monkeypatch, tmp_path, malicious_member: str) -> None:
    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=make_zip({malicious_member: b"pwn"}))

    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(signed_handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.client.httpx.AsyncClient", fake_async_client)

    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    dest = tmp_path / "out"
    with pytest.raises(ValueError, match="(?i)zip-slip"):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", dest)

    # Nothing was extracted before the guard fired.
    assert list(dest.rglob("*")) == []


def patch_signed_download(monkeypatch, handler: Any) -> None:
    """Route the anonymous signed-URL download through a mock transport."""
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.client.httpx.AsyncClient", fake_async_client)


@pytest.mark.asyncio
async def test_download_artifact_server_error_propagates(monkeypatch, tmp_path) -> None:
    """A failed signed-URL download propagates as httpx.HTTPStatusError (no retries)."""

    def github_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, content=b"unavailable")

    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))
    with pytest.raises(httpx.HTTPStatusError):
        await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")


# ---------------------------------------------------------------------------
# Default rate-limit protection + rate-limit-aware retry
# ---------------------------------------------------------------------------


class FakeClock:
    """Injectable, manually-advanceable clock for deterministic governor-driven retries."""

    def __init__(self, start: float = 1000.0) -> None:
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


def recording_transport(items: list[httpx.Response | Exception]) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    """MockTransport that returns/raises *items* in order (last item repeats) and records each request."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        item = items[min(len(calls), len(items) - 1)]
        calls.append(request)
        if isinstance(item, Exception):
            raise item
        return item

    return httpx.MockTransport(handler), calls


def governed_client(
    clock: FakeClock,
    transport: httpx.MockTransport,
    on_event: Any = None,
    max_rate_limit_retries: int = 2,
) -> AsyncGitHubClient:
    """Client whose governor runs on *clock*, so retry waits are deterministic under a fake sleep."""
    governor = BudgetGovernor(now=clock, on_event=on_event)
    limiter = InstrumentedAsyncLimiter(
        AsyncLimiter(max_rate=5000, time_period=RATE_LIMIT_TIME_PERIOD),
        on_event=on_event,
        budget_governor=governor,
        name="github",
    )
    return AsyncGitHubClient(
        token=TOKEN, rate_limiter=limiter, transport=transport, max_rate_limit_retries=max_rate_limit_retries
    )


def advance_clock_on_sleep(clock: FakeClock, monkeypatch: pytest.MonkeyPatch) -> None:
    """Make asyncio.sleep advance the fake clock instead of blocking, so governor waits are instant."""

    async def fake_sleep(delay: float) -> None:
        clock.advance(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)


async def test_default_rate_limiter_is_constructed_and_observes_403() -> None:
    """rate_limiter=None builds a limiter with a governor that observes a 403's retry-after."""
    transport, calls = recording_transport([httpx.Response(403, headers={"retry-after": "30"})])
    client = AsyncGitHubClient(token=TOKEN, transport=transport, max_rate_limit_retries=0)

    assert client._rate_limiter is not None
    governor = client._rate_limiter.budget_governor
    assert governor is not None

    with pytest.raises(httpx.HTTPStatusError):
        await client._request("GET", "/x")

    # The 403's retry-after was observed (before raise_for_status), arming the shared pause.
    assert governor.pause_until - time.time() == pytest.approx(31.0, abs=2.0)
    assert len(calls) == 1  # retries disabled: one call, no wait


async def test_retry_on_secondary_limit_returns_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 403 with retry-after then a 200 is retried once and the wait goes through the governor."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    events: list[RateLimitEvent] = []
    transport, calls = recording_transport([httpx.Response(403, headers={"retry-after": "5"}), httpx.Response(200)])
    client = governed_client(clock, transport, on_event=events.append)

    response = await client._request("GET", "/x")

    assert response.status_code == 200
    assert len(calls) == 2
    secondary_index = next(i for i, e in enumerate(events) if isinstance(e, SecondaryLimitEvent))
    pacing_index = next(
        i for i, e in enumerate(events) if isinstance(e, PacingEvent) and e.reason is PacingReason.SECONDARY_LIMIT
    )
    assert secondary_index < pacing_index


async def test_retry_on_primary_exhaustion_waits_until_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 403 with x-ratelimit-remaining=0 is retried, and the retry waits until the window reset."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    events: list[RateLimitEvent] = []
    reset_at = clock.current + 30
    transport, calls = recording_transport(
        [
            httpx.Response(
                403,
                headers={"x-ratelimit-limit": "5000", "x-ratelimit-remaining": "0", "x-ratelimit-reset": str(reset_at)},
            ),
            httpx.Response(200),
        ]
    )
    client = governed_client(clock, transport, on_event=events.append)

    response = await client._request("GET", "/x")

    assert response.status_code == 200
    assert len(calls) == 2
    governor = client._rate_limiter.budget_governor
    assert clock.current == pytest.approx(reset_at + governor.buffer_seconds)
    assert any(isinstance(e, PacingEvent) and e.reason is PacingReason.EXHAUSTED for e in events)


async def test_no_retry_on_permission_denied_403() -> None:
    """A 403 with no retry-after and nonzero remaining is a permission denial: raise on first attempt."""
    transport, calls = recording_transport([httpx.Response(403, headers={"x-ratelimit-remaining": "5"})])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(httpx.HTTPStatusError):
        await client._request("GET", "/x")

    assert len(calls) == 1


async def test_no_retry_on_transport_error() -> None:
    """A transport error is never retried (the action may have executed); it propagates immediately."""
    transport, calls = recording_transport([httpx.ConnectError("boom")])
    client = AsyncGitHubClient(token=TOKEN, transport=transport)

    with pytest.raises(httpx.ConnectError):
        await client._request("GET", "/x")

    assert len(calls) == 1


async def test_retries_exhausted_raises_after_max(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two consecutive rate-limit responses with max_rate_limit_retries=1 raise after exactly two calls."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    transport, calls = recording_transport(
        [httpx.Response(403, headers={"retry-after": "5"}), httpx.Response(403, headers={"retry-after": "5"})]
    )
    client = governed_client(clock, transport, max_rate_limit_retries=1)

    with pytest.raises(httpx.HTTPStatusError):
        await client._request("GET", "/x")

    assert len(calls) == 2


async def test_download_redirect_302_is_not_retried(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """The artifact 302 redirect is not a rate-limit response, so it resolves without any retry."""
    github_calls: list[httpx.Request] = []

    def github_handler(request: httpx.Request) -> httpx.Response:
        github_calls.append(request)
        return httpx.Response(302, headers={"location": "https://signed.example/zip"})

    def signed_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=make_zip({"hello.txt": b"hi"}))

    patch_signed_download(monkeypatch, signed_handler)
    client = AsyncGitHubClient(token=TOKEN, transport=httpx.MockTransport(github_handler))

    await client.download_artifact("/repos/o/r/actions/artifacts/1/zip", tmp_path / "out")

    assert len(github_calls) == 1


async def test_pagination_retries_only_the_rate_limited_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """A rate-limited page is retried in place; the iterator then continues to the next page."""
    clock = FakeClock()
    advance_clock_on_sleep(clock, monkeypatch)
    transport, calls = recording_transport(
        [
            httpx.Response(200, json={"page": 1}, headers={"link": '<https://api.github.com/next>; rel="next"'}),
            httpx.Response(403, headers={"retry-after": "5"}),
            httpx.Response(200, json={"page": 2}),
        ]
    )
    client = governed_client(clock, transport)

    pages = [response async for response in client._paginated_request("GET", "/start")]

    assert [page.status_code for page in pages] == [200, 200]
    assert len(calls) == 3  # page 1, page 2 (rate-limited), page 2 (retry)
