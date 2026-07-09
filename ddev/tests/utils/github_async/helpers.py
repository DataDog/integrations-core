"""Shared payload factories, transports, and the endpoint registry for the async-client tests."""

from __future__ import annotations

import dataclasses
import io
import zipfile
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
from aiolimiter import AsyncLimiter

from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.rate_limiting import RATE_LIMIT_TIME_PERIOD, BudgetGovernor, InstrumentedAsyncLimiter
from tests.helpers.clock import FakeClock

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


def make_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return buf.getvalue()


def patch_signed_download(monkeypatch, handler: Any) -> None:
    """Route the anonymous signed-URL download through a mock transport."""
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        if kwargs.get("transport") is None:
            kwargs["transport"] = httpx.MockTransport(handler)
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("ddev.utils.github_async.client.httpx.AsyncClient", fake_async_client)


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


async def first_page(pages: AsyncIterator[GitHubResponse[Any]]) -> GitHubResponse[Any]:
    """Return the first page of a paginated endpoint (enough to exercise errors and headers)."""
    async for page in pages:
        return page
    raise AssertionError("expected at least one page")


@dataclasses.dataclass
class EndpointCase:
    id: str
    call: Callable[[AsyncGitHubClient], Awaitable[GitHubResponse[Any]]]
    ok_response: Callable[[], httpx.Response]


ENDPOINT_CALLS = [
    EndpointCase(
        "create_workflow_dispatch",
        lambda c: c.create_workflow_dispatch("o", "r", "wf.yml", "main", return_run_details=True),
        lambda: json_response(
            {"workflow_run_id": 1, "run_url": "https://api.github.com/x", "html_url": "https://github.com/x"}
        ),
    ),
    EndpointCase(
        "get_workflow_run", lambda c: c.get_workflow_run("o", "r", 42), lambda: json_response(workflow_run_payload())
    ),
    EndpointCase(
        "list_workflow_run_artifacts",
        lambda c: first_page(c.list_workflow_run_artifacts("o", "r", 1)),
        lambda: json_response({"total_count": 1, "artifacts": [artifact(1)]}),
    ),
    EndpointCase(
        "list_workflow_jobs",
        lambda c: first_page(c.list_workflow_jobs("o", "r", 42)),
        lambda: json_response({"total_count": 1, "jobs": [workflow_job(1)]}),
    ),
    EndpointCase(
        "create_issue_comment",
        lambda c: c.create_issue_comment("o", "r", 1, "body"),
        lambda: json_response(issue_comment_payload()),
    ),
    EndpointCase(
        "get_pull_request",
        lambda c: c.get_pull_request("o", "r", 5),
        lambda: json_response(full_pull_request_payload(number=5)),
    ),
    EndpointCase(
        "create_pull_request",
        lambda c: c.create_pull_request("o", "r", "t", "h", "b"),
        lambda: json_response(pull_request_payload(number=1), status_code=201),
    ),
    EndpointCase(
        "add_labels_to_issue",
        lambda c: c.add_labels_to_issue("o", "r", 1, ["bug"]),
        lambda: json_response([{"id": 1, "name": "bug"}]),
    ),
    EndpointCase(
        "create_pr_review_comment",
        lambda c: c.create_pr_review_comment("o", "r", 1, "body", "sha", "path", position=1),
        lambda: json_response(pr_review_comment_payload()),
    ),
    EndpointCase(
        "create_check_run",
        lambda c: c.create_check_run("o", "r", "ck", "abc", "in_progress"),
        lambda: json_response(check_run_payload()),
    ),
    EndpointCase(
        "update_check_run",
        lambda c: c.update_check_run("o", "r", 77, status="in_progress"),
        lambda: json_response(check_run_payload(id=77)),
    ),
]
