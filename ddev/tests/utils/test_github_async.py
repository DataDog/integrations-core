"""Tests for the async GitHub API client."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import httpx
import pytest

from ddev.utils.github_async import (
    GITHUB_API_VERSION,
    AsyncGitHubClient,
    GitHubResponse,
    PaginationData,
    async_github_client,
)
from ddev.utils.github_async.models import (
    ArtifactsList,
    GitHubUser,
    IssueComment,
    Label,
    PullRequest,
    PullRequestRef,
    PullRequestReviewComment,
    WorkflowRun,
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
        assert "inputs" not in body
        return httpx.Response(204, headers={"x-ratelimit-remaining": "59"})

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_workflow_dispatch("owner", "repo", "my-workflow.yml", "main")
    assert isinstance(result, GitHubResponse)
    assert result.data is None
    assert result.headers.get("x-ratelimit-remaining") == "59"


async def test_create_workflow_dispatch_with_inputs() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["inputs"] == {"env": "prod"}
        return httpx.Response(204)

    client = _make_client(httpx.MockTransport(handler))
    await client.create_workflow_dispatch("o", "r", 123, "main", inputs={"env": "prod"})


async def test_create_workflow_dispatch_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_workflow_dispatch("o", "r", "wf.yml", "main")
    assert exc_info.value.response.status_code == 422


# ---------------------------------------------------------------------------
# get_workflow_run
# ---------------------------------------------------------------------------


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


async def test_get_workflow_run_headers_forwarded() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response(_workflow_run_payload(), headers={"x-ratelimit-remaining": "50"})

    client = _make_client(httpx.MockTransport(handler))
    result = await client.get_workflow_run("o", "r", 42)
    assert result.headers.get("x-ratelimit-remaining") == "50"


async def test_get_workflow_run_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.get_workflow_run("o", "r", 99)
    assert exc_info.value.response.status_code == 404


# ---------------------------------------------------------------------------
# list_workflow_run_artifacts (pagination)
# ---------------------------------------------------------------------------


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


async def test_list_workflow_run_artifacts_pagination_stops_when_no_next() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return _json_response({"total_count": 1, "artifacts": [_artifact(1)]})

    client = _make_client(httpx.MockTransport(handler))
    count = 0
    async for _ in client.list_workflow_run_artifacts("owner", "repo", 1):
        count += 1
    assert count == 1


async def test_list_workflow_run_artifacts_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(403)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        async for _ in client.list_workflow_run_artifacts("o", "r", 1):
            pass
    assert exc_info.value.response.status_code == 403


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
    assert isinstance(result.data.user, GitHubUser)
    assert result.data.user.login == "octocat"


async def test_create_issue_comment_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
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
        return _json_response(_pr_review_comment_payload(), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
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
        return _json_response(_pr_review_comment_payload(), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pr_review_comment("o", "r", 1, "comment", "abc123", "file.py", line=10, side="RIGHT")
    assert isinstance(result.data, PullRequestReviewComment)


async def test_create_pr_review_comment_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_pr_review_comment("o", "r", 1, "body", "sha", "path")
    assert exc_info.value.response.status_code == 422


# ---------------------------------------------------------------------------
# create_pull_request
# ---------------------------------------------------------------------------


def _pull_request_payload(number: int = 1) -> dict[str, Any]:
    return {
        "number": number,
        "html_url": f"https://github.com/owner/repo/pull/{number}",
    }


def _full_pull_request_payload(number: int = 42) -> dict[str, Any]:
    """A richer PR payload exercising sub-models (user, labels, head/base)."""
    return {
        "id": 9000 + number,
        "number": number,
        "node_id": "PR_kwDOABCD123",
        "url": f"https://api.github.com/repos/owner/repo/pulls/{number}",
        "html_url": f"https://github.com/owner/repo/pull/{number}",
        "diff_url": f"https://github.com/owner/repo/pull/{number}.diff",
        "patch_url": f"https://github.com/owner/repo/pull/{number}.patch",
        "state": "open",
        "draft": True,
        "merged": False,
        "locked": False,
        "merge_commit_sha": None,
        "title": "Fix bug",
        "body": "Backport",
        "user": {
            "id": 1,
            "login": "octocat",
            "html_url": "https://github.com/octocat",
            "type": "User",
        },
        "assignees": [],
        "requested_reviewers": [
            {"id": 2, "login": "reviewer", "type": "User"},
        ],
        "labels": [
            {"id": 100, "name": "qa/skip-qa", "color": "5319e7"},
            {"id": 101, "name": "backport/7.62.x", "color": "5319e7"},
        ],
        "created_at": "2026-05-01T00:00:00Z",
        "updated_at": "2026-05-02T00:00:00Z",
        "closed_at": None,
        "merged_at": None,
        "head": {
            "ref": "alice/fix",
            "sha": "1234567890abcdef00",
            "label": "alice:alice/fix",
        },
        "base": {
            "ref": "master",
            "sha": "cafebabe00",
            "label": "owner:master",
        },
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
        return _json_response(_pull_request_payload(number=42), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("owner", "repo", "Fix bug", "alice/fix", "master", "Fix description")
    assert isinstance(result.data, PullRequest)
    assert result.data.number == 42
    assert result.data.html_url == "https://github.com/owner/repo/pull/42"


async def test_create_pull_request_draft_true_forwarded() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["draft"] is True
        return _json_response(_pull_request_payload(number=7), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("o", "r", "T", "h", "b", draft=True)
    assert result.data.number == 7


async def test_create_pull_request_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(422)))
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await client.create_pull_request("o", "r", "T", "h", "b")
    assert exc_info.value.response.status_code == 422


async def test_create_pull_request_parses_full_response() -> None:
    """Exercises sub-models (GitHubUser, Label, PullRequestRef) end-to-end."""

    def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(_full_pull_request_payload(number=42), status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("owner", "repo", "Fix bug", "alice/fix", "master")

    pr = result.data
    assert pr.id == 9042
    assert pr.number == 42
    assert pr.state == "open"
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
        payload = _full_pull_request_payload()
        payload["mergeable_state"] = "clean"
        payload["additions"] = 42
        payload["unknown_future_field"] = {"nested": True}
        return _json_response(payload, status_code=201)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.create_pull_request("o", "r", "T", "h", "b")
    assert result.data.number == 42


# ---------------------------------------------------------------------------
# add_labels_to_issue
# ---------------------------------------------------------------------------


async def test_add_labels_to_issue_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/repos/owner/repo/issues/3/labels" in request.url.path
        body = json.loads(request.content)
        assert body == {"labels": ["qa/skip-qa", "backport/7.62.x"]}
        return _json_response([{"id": 1, "name": "qa/skip-qa"}, {"id": 2, "name": "backport/7.62.x"}], status_code=200)

    client = _make_client(httpx.MockTransport(handler))
    result = await client.add_labels_to_issue("owner", "repo", 3, ["qa/skip-qa", "backport/7.62.x"])
    assert [label.name for label in result.data] == ["qa/skip-qa", "backport/7.62.x"]
    assert all(isinstance(label, Label) for label in result.data)


async def test_add_labels_to_issue_http_error_raises() -> None:
    client = _make_client(httpx.MockTransport(lambda r: httpx.Response(404)))
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
        return _json_response(_workflow_run_payload())

    client = AsyncGitHubClient(token=TOKEN, default_timeout=5.0, transport=httpx.MockTransport(handler))
    result = await client.get_workflow_run("o", "r", 42, timeout=2.0)
    assert result.data.id == 42
