# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async HTTP client for the GitHub REST API."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Literal, Self, overload

import httpx
from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ArtifactsList,
    IssueComment,
    Label,
    PullRequest,
    PullRequestReviewComment,
    WorkflowDispatchResult,
    WorkflowJobsList,
    WorkflowRun,
)

GITHUB_API_VERSION = "2022-11-28"
DEFAULT_BASE_URL = "https://api.github.com"

_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


# ---------------------------------------------------------------------------
# Pagination + response wrappers
# ---------------------------------------------------------------------------


@dataclass
class PaginationData:
    """Parsed pagination links from a GitHub API Link header."""

    first: str | None = None
    prev: str | None = None
    next: str | None = None
    last: str | None = None

    @classmethod
    def from_header(cls, header: str | None) -> Self:
        """Parse a Link header value and return a PaginationData instance."""
        if not header:
            return cls()
        links: dict[str, str] = {}
        for url, rel in _LINK_RE.findall(header):
            links[rel] = url
        return cls(
            first=links.get("first"),
            prev=links.get("prev"),
            next=links.get("next"),
            last=links.get("last"),
        )


class GitHubResponse[T](BaseModel):
    """Generic wrapper for a GitHub API response."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: T = Field(...)
    headers: dict[str, str] = Field(default_factory=dict)


class AsyncGitHubClient:
    """
    Async HTTP client for the GitHub REST API.

    Uses a shared httpx.AsyncClient for connection pooling. Call `aclose()` when
    finished to release resources, or use the `async_github_client` context manager.
    """

    def __init__(
        self,
        token: str,
        default_timeout: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not token:
            raise ValueError("GitHub token must not be empty.")

        self._default_timeout = default_timeout
        self._headers = {
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "Accept": "application/vnd.github+json",
        }
        self._client = httpx.AsyncClient(
            base_url=DEFAULT_BASE_URL,
            headers=self._headers,
            timeout=default_timeout,
            transport=transport,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        endpoint: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        effective_timeout = timeout if timeout is not None else self._default_timeout
        try:
            response = await self._client.request(method, endpoint, timeout=effective_timeout, **kwargs)
        except httpx.TransportError as exc:
            raise type(exc)(f"{method} {endpoint}: {exc}") from exc
        response.raise_for_status()
        return response

    async def _paginated_request(
        self,
        method: str,
        endpoint: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[httpx.Response]:
        """Yield one httpx.Response per page, following Link headers."""
        url: str | None = endpoint
        first = True
        while url is not None:
            if first:
                response = await self._request(method, url, timeout=timeout, **kwargs)
                first = False
            else:
                # Subsequent pages: use the absolute next URL, no extra kwargs
                response = await self._request(method, url, timeout=timeout)
            yield response
            pagination = PaginationData.from_header(response.headers.get("link"))
            url = pagination.next

    @staticmethod
    def _parse_response[T: BaseModel](response: httpx.Response, model: type[T]) -> GitHubResponse[T]:
        """Validate the response body against *model* and wrap it in a GitHubResponse."""
        return GitHubResponse[T].model_validate(
            {"data": model.model_validate(response.json()), "headers": dict(response.headers)}
        )

    # ------------------------------------------------------------------
    # Endpoint methods
    # ------------------------------------------------------------------

    @overload
    async def create_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str,
        inputs: dict[str, str] | None = None,
        timeout: float | None = None,
        *,
        return_run_details: Literal[True],
    ) -> GitHubResponse[WorkflowDispatchResult]: ...

    @overload
    async def create_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str,
        inputs: dict[str, str] | None = None,
        timeout: float | None = None,
        *,
        return_run_details: Literal[False] = False,
    ) -> GitHubResponse[None]: ...

    async def create_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str,
        inputs: dict[str, str] | None = None,
        timeout: float | None = None,
        *,
        return_run_details: bool = False,
    ) -> GitHubResponse[WorkflowDispatchResult] | GitHubResponse[None]:
        """
        Calls the GitHub API to trigger a workflow dispatch event.

        GitHub API Documentation:
        https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            workflow_id: Workflow file name or numeric ID.
            ref: Branch or tag name to run the workflow on.
            inputs: Optional key/value inputs forwarded to the workflow.
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.
            return_run_details: When True, requests a 200 response with the new run's metadata
                (workflow_run_id, run_url, html_url) instead of the default 204 No Content.
                See https://github.blog/changelog/2026-02-19-workflow-dispatch-api-now-returns-run-ids/.

        Returns:
            When ``return_run_details=False`` (default): ``GitHubResponse[None]`` wrapping the 204.
            When ``return_run_details=True``: ``GitHubResponse[WorkflowDispatchResult]`` with the new run's
            IDs and URLs.
        """
        body: dict[str, Any] = {"ref": ref}
        if inputs is not None:
            body["inputs"] = inputs
        if return_run_details:
            body["return_run_details"] = True
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
            timeout=timeout,
            json=body,
        )
        if return_run_details:
            return self._parse_response(response, WorkflowDispatchResult)
        return GitHubResponse[None].model_validate({"data": None, "headers": dict(response.headers)})

    async def get_workflow_run(
        self,
        owner: str,
        repo: str,
        run_id: int,
        timeout: float | None = None,
    ) -> GitHubResponse[WorkflowRun]:
        """
        Calls the GitHub API to get a single workflow run.

        GitHub API Documentation:
        https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            run_id: Numeric ID of the workflow run.
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[WorkflowRun]: The validated workflow run data and headers.
        """
        response = await self._request("GET", f"/repos/{owner}/{repo}/actions/runs/{run_id}", timeout=timeout)
        return self._parse_response(response, WorkflowRun)

    async def list_workflow_run_artifacts(
        self,
        owner: str,
        repo: str,
        run_id: int,
        per_page: int = 30,
        timeout: float | None = None,
    ) -> AsyncIterator[GitHubResponse[ArtifactsList]]:
        """
        Calls the GitHub API to list artifacts for a workflow run (paginated).

        GitHub API Documentation:
        https://docs.github.com/en/rest/actions/artifacts#list-workflow-run-artifacts

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            run_id: Numeric ID of the workflow run.
            per_page: Number of artifacts per page (default 30, max 100).
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            AsyncIterator[GitHubResponse[ArtifactsList]]: One page of artifacts per iteration.
        """
        endpoint = f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        async for response in self._paginated_request("GET", endpoint, timeout=timeout, params={"per_page": per_page}):
            yield self._parse_response(response, ArtifactsList)

    async def list_workflow_run_jobs(
        self,
        owner: str,
        repo: str,
        run_id: int,
        per_page: int = 30,
        timeout: float | None = None,
    ) -> AsyncIterator[GitHubResponse[WorkflowJobsList]]:
        """
        Calls the GitHub API to list jobs for a workflow run (paginated).

        GitHub API Documentation:
        https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            run_id: Numeric ID of the workflow run.
            per_page: Number of jobs per page (default 30, max 100).
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            AsyncIterator[GitHubResponse[WorkflowJobsList]]: One page of jobs per iteration.
        """
        endpoint = f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        async for response in self._paginated_request("GET", endpoint, timeout=timeout, params={"per_page": per_page}):
            yield self._parse_response(response, WorkflowJobsList)

    async def create_issue_comment(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        body: str,
        timeout: float | None = None,
    ) -> GitHubResponse[IssueComment]:
        """
        Calls the GitHub API to create a comment on an issue or pull request.

        GitHub API Documentation:
        https://docs.github.com/en/rest/issues/comments#create-an-issue-comment

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            issue_number: Issue or pull request number.
            body: Markdown body text of the comment.
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[IssueComment]: The validated comment data and headers.
        """
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            timeout=timeout,
            json={"body": body},
        )
        return self._parse_response(response, IssueComment)

    async def get_pull_request(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        timeout: float | None = None,
    ) -> GitHubResponse[PullRequest]:
        """
        Calls the GitHub API to get a single pull request.

        GitHub API Documentation:
        https://docs.github.com/en/rest/pulls/pulls#get-a-pull-request

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            pull_number: Pull request number.
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[PullRequest]: The validated pull request data and headers.
        """
        response = await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pull_number}", timeout=timeout)
        return self._parse_response(response, PullRequest)

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
        draft: bool = False,
        timeout: float | None = None,
    ) -> GitHubResponse[PullRequest]:
        """
        Calls the GitHub API to create a pull request.

        GitHub API Documentation:
        https://docs.github.com/en/rest/pulls/pulls#create-a-pull-request

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            title: Pull request title.
            head: Name of the branch containing the changes.
            base: Name of the branch to merge into.
            body: Pull request body.
            draft: Whether to open the pull request as a draft.
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[PullRequest]: The validated pull request data and headers.
        """
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            timeout=timeout,
            json={"title": title, "head": head, "base": base, "body": body, "draft": draft},
        )
        return self._parse_response(response, PullRequest)

    async def add_labels_to_issue(
        self,
        owner: str,
        repo: str,
        issue_number: int,
        labels: list[str],
        timeout: float | None = None,
    ) -> GitHubResponse[list[Label]]:
        """
        Calls the GitHub API to add one or more labels to an issue or pull request.

        GitHub API Documentation:
        https://docs.github.com/en/rest/issues/labels#add-labels-to-an-issue

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            issue_number: Issue or pull request number.
            labels: Labels to add. Existing labels on the issue are preserved.
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[list[Label]]: The full label list resulting from the operation (preserves
            any pre-existing labels alongside the newly added ones).
        """
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{issue_number}/labels",
            timeout=timeout,
            json={"labels": labels},
        )
        labels_out = [Label.model_validate(item) for item in response.json()]
        return GitHubResponse[list[Label]].model_validate({"data": labels_out, "headers": dict(response.headers)})

    async def create_pr_review_comment(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        body: str,
        commit_id: str,
        path: str,
        position: int | None = None,
        line: int | None = None,
        side: Literal["LEFT", "RIGHT"] | None = None,
        timeout: float | None = None,
    ) -> GitHubResponse[PullRequestReviewComment]:
        """
        Calls the GitHub API to create an inline review comment on a pull request diff.

        GitHub API Documentation:
        https://docs.github.com/en/rest/pulls/comments#create-a-review-comment-for-a-pull-request

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            pull_number: Pull request number.
            body: Markdown body text of the comment.
            commit_id: SHA of the commit to comment on.
            path: Path of the file to comment on.
            position: Line index in the diff (mutually exclusive with line/side).
            line: Line number in the file (newer style, paired with side).
            side: 'LEFT' or 'RIGHT' (newer style, paired with line).
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[PullRequestReviewComment]: The validated comment data and headers.
        """
        payload: dict[str, Any] = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
        }
        if position is not None:
            payload["position"] = position
        if line is not None:
            payload["line"] = line
        if side is not None:
            payload["side"] = side
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{pull_number}/comments",
            timeout=timeout,
            json=payload,
        )
        return self._parse_response(response, PullRequestReviewComment)


# ---------------------------------------------------------------------------
# Async context manager
# ---------------------------------------------------------------------------


@asynccontextmanager
async def async_github_client(
    token: str,
    default_timeout: float = 30.0,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncIterator[AsyncGitHubClient]:
    """
    Async context manager that creates an AsyncGitHubClient and ensures it is closed on exit.

    Args:
        token: GitHub personal access token or app token.
        default_timeout: Default request timeout in seconds.
        transport: Optional custom HTTPX transport (useful for testing with MockTransport).

    Yields:
        AsyncGitHubClient: A ready-to-use async GitHub client.
    """
    client = AsyncGitHubClient(token=token, default_timeout=default_timeout, transport=transport)
    try:
        yield client
    finally:
        await client.aclose()
