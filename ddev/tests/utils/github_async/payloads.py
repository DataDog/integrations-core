"""Pure GitHub API response payload factories. Stdlib-only: no httpx, models, or client imports."""

from __future__ import annotations

from typing import Any


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
