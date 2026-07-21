# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async HTTP client for the GitHub REST API."""

from __future__ import annotations

import io
import re
import zipfile
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self, overload

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ddev.utils.rate_limiting import NULL_SNAPSHOT, BudgetSnapshot, InstrumentedAsyncLimiter

from .defaults import default_github_rate_limiter
from .models import (
    ArtifactsList,
    CheckRun,
    CheckRunConclusion,
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


def parse_header[T](headers: httpx.Headers, key: str, cast: Callable[[str], T]) -> T | None:
    """Return the header at *key* run through *cast*, or None if it is absent or unparseable."""
    raw = headers.get(key)
    if raw is None:
        return None
    with suppress(ValueError, TypeError):
        return cast(raw)
    return None


def github_rate_limit_snapshot(headers: httpx.Headers) -> BudgetSnapshot | None:
    """Parse GitHub's `x-ratelimit-*` / `retry-after` response headers into a BudgetSnapshot."""
    snapshot = BudgetSnapshot(
        limit=parse_header(headers, "x-ratelimit-limit", int),
        remaining=parse_header(headers, "x-ratelimit-remaining", int),
        reset_at=parse_header(headers, "x-ratelimit-reset", float),
        retry_after=parse_header(headers, "retry-after", lambda raw: float(int(raw))),
    )
    return snapshot if snapshot != NULL_SNAPSHOT else None


class AsyncGitHubClient:
    """
    Async HTTP client for the GitHub REST API.

    Uses a shared httpx.AsyncClient for connection pooling. Call `aclose()` when
    finished to release resources, or use the `async_github_client` context manager.

    Rate-limit protection is on by default: requests are paced and, when GitHub signals a
    rate-limit rejection, retried in reaction to the response headers. The governor supplies the
    backoff, so there is no sleeping or backoff arithmetic in this client. The default protection
    logs through the ``ddev.utils.github_async.defaults`` logger.

    Args:
        token: GitHub token; must be non-empty.
        rate_limiter: Overrides the default rate limiter; it does not enable protection, which is
            already on. None builds the default (a permissive local bucket fronting a reactive
            BudgetGovernor). There is deliberately no way to disable protection: GitHub requires
            clients to honor ``retry-after``, and persistent violations risk the shared token being
            throttled harder or banned. Because octo-sts mints the token against one installation
            for the whole company, a single unprotected client instance degrades every other
            consumer of that token. Callers with special needs pass their own limiter; they do not
            turn protection off.
        default_timeout: Default per-request HTTP timeout in seconds. Bounds individual HTTP
            requests only; it does not bound governor waits. To bound total wait, pass a limiter
            whose governor sets ``max_wait_seconds``.
        max_rate_limit_retries: Extra attempts for a header-confirmed rate-limit response (403/429).
            Each retry is a full fresh acquisition (governor wait plus bucket token); the default of
            2 covers the common "hit a secondary limit once, wait, succeed" case plus one repeat.
            Only rate-limit responses are retried: transport errors and non-rate-limit statuses
            propagate immediately, and RateLimitWaitAbandoned (the governor's ``max_wait_seconds``
            killswitch) propagates to the caller.
        transport: Optional custom HTTPX transport (useful for testing with MockTransport).
    """

    def __init__(
        self,
        token: str,
        *,
        rate_limiter: InstrumentedAsyncLimiter | None = None,
        default_timeout: float = 30.0,
        max_rate_limit_retries: int = 2,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not token:
            raise ValueError("GitHub token must not be empty.")

        # A None limiter means "use the default protection," not "no protection." The local bucket
        # is deliberately permissive because the governor is the protection; with a healthy budget
        # and no secondary limits the governor adds zero wait, so this default is invisible to
        # well-behaved callers and engages only once GitHub has already signaled backpressure.
        self._rate_limiter = rate_limiter if rate_limiter is not None else default_github_rate_limiter()
        self._default_timeout = default_timeout
        self._max_rate_limit_retries = max_rate_limit_retries
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

    def _effective_timeout(self, timeout: float | None) -> float:
        return timeout if timeout is not None else self._default_timeout

    @staticmethod
    def _is_rate_limit_response(response: httpx.Response) -> bool:
        """Whether *response* is a retryable rate-limit rejection, by GitHub's own discrimination rule.

        A 403 is also used for plain permission denials, which waiting cannot fix; retrying one would
        sleep out a pause (up to a full window) and then fail identically. Only header-confirmed
        rate-limit responses are retryable.
        """
        if response.status_code not in (403, 429):
            return False
        return "retry-after" in response.headers or response.headers.get("x-ratelimit-remaining") == "0"

    async def _execute_request(
        self,
        method: str,
        endpoint: str,
        timeout: float,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            response = await self._client.request(method, endpoint, timeout=timeout, **kwargs)
        except httpx.TransportError as exc:
            raise type(exc)(f"{method} {endpoint}: {exc}") from exc
        # Observe before raise_for_status, never after: learning must not be gated on success. A
        # failed response's rate-limit headers arm the shared pause even if the caller swallows the
        # exception, so one request's 403 protects every other in-flight and future request in this
        # process.
        snapshot = github_rate_limit_snapshot(response.headers)
        if snapshot is not None:
            self._rate_limiter.observe(snapshot)
        response.raise_for_status()
        return response

    async def _request(
        self,
        method: str,
        endpoint: str,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        effective_timeout = self._effective_timeout(timeout)
        # Rate-limit-aware retry lives here, not in _execute_request: re-entering the limiter IS the
        # backoff. The failed response's headers were observed inside _execute_request before the
        # exception propagated, so the governor already holds the pause this very 403 armed;
        # re-acquiring waits it out exactly (retry-after plus buffer for secondary limits, until
        # reset for an exhausted window). Hence no sleeps or backoff math. A loop inside
        # _execute_request would be wrong: it would retry while still holding the acquisition,
        # without re-consulting the governor. Concurrent retries also serialize behind the same
        # shared pause instead of stampeding, which is what GitHub's secondary-limit guidance asks
        # for. RateLimitWaitAbandoned raised while (re-)acquiring propagates untouched from here: it
        # is the caller-configured killswitch, and counting it as an attempt would defeat it.
        for attempt in range(self._max_rate_limit_retries + 1):
            async with self._rate_limiter:
                try:
                    return await self._execute_request(method, endpoint, effective_timeout, **kwargs)
                except httpx.HTTPStatusError as exc:
                    # A rate-limit 403/429 is safe to retry for every endpoint, including
                    # non-idempotent POSTs, precisely because GitHub rejected it without performing
                    # the action. (Transport errors are never retried, and are not caught here: after
                    # one we cannot know whether the action executed.) Give up on the last attempt or
                    # on a non-rate-limit status, which waiting cannot fix.
                    if attempt == self._max_rate_limit_retries or not self._is_rate_limit_response(exc.response):
                        raise
        raise RuntimeError("unreachable: the retry loop always returns or raises")  # pragma: no cover

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

    async def list_workflow_jobs(
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

    async def create_check_run(
        self,
        owner: str,
        repo: str,
        name: str,
        head_sha: str,
        status: Literal["queued", "in_progress", "completed"],
        details_url: str | None = None,
        output: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> GitHubResponse[CheckRun]:
        """
        Calls the GitHub API to create a check run on a commit.

        GitHub API Documentation:
        https://docs.github.com/en/rest/checks/runs#create-a-check-run

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            name: Display name of the check.
            head_sha: SHA of the commit the check is attached to.
            status: Initial status of the check.
            details_url: Optional URL the check title links to.
            output: Optional structured output (title, summary, ...).
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[CheckRun]: The validated check run data and headers.
        """
        payload: dict[str, Any] = {"name": name, "head_sha": head_sha, "status": status}
        if details_url is not None:
            payload["details_url"] = details_url
        if output is not None:
            payload["output"] = output
        response = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/check-runs",
            timeout=timeout,
            json=payload,
        )
        return self._parse_response(response, CheckRun)

    async def update_check_run(
        self,
        owner: str,
        repo: str,
        check_run_id: int,
        status: Literal["queued", "in_progress", "completed"] | None = None,
        conclusion: CheckRunConclusion | None = None,
        details_url: str | None = None,
        output: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> GitHubResponse[CheckRun]:
        """
        Calls the GitHub API to update an existing check run.

        GitHub API Documentation:
        https://docs.github.com/en/rest/checks/runs#update-a-check-run

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.
            check_run_id: Numeric ID of the check run to update.
            status: New status (``"queued"`` | ``"in_progress"`` | ``"completed"``).
            conclusion: Final conclusion. Required when ``status="completed"``.
            details_url: Optional URL the check title links to.
            output: Optional structured output (title, summary, ...).
            timeout: Optional timeout for this specific request. Defaults to the client's default_timeout.

        Returns:
            GitHubResponse[CheckRun]: The validated check run data and headers.
        """
        if status == "completed" and conclusion is None:
            raise ValueError("A conclusion is required when a check run status is 'completed'.")
        payload: dict[str, Any] = {}
        if status is not None:
            payload["status"] = status
        if conclusion is not None:
            payload["conclusion"] = conclusion
        if details_url is not None:
            payload["details_url"] = details_url
        if output is not None:
            payload["output"] = output
        response = await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/check-runs/{check_run_id}",
            timeout=timeout,
            json=payload,
        )
        return self._parse_response(response, CheckRun)

    async def _resolve_artifact_redirect(
        self,
        archive_download_url: str,
        timeout: float | None = None,
    ) -> str:
        """Authenticated GET; return the unauthenticated signed URL from the 302 Location header."""
        try:
            redirect_response = await self._request(
                "GET", archive_download_url, timeout=timeout, follow_redirects=False
            )
        except httpx.HTTPStatusError as exc:
            # httpx.raise_for_status() treats the expected 302 as an error since it isn't a 2xx;
            # recover the response from the exception so the redirect can still be inspected below.
            # The retry layer in _request is deliberately transparent here: a 302 is not a rate-limit
            # response by _is_rate_limit_response, so it is never retried and surfaces on the first
            # attempt exactly as before.
            redirect_response = exc.response
        if redirect_response.status_code != 302:
            redirect_response.raise_for_status()
            raise httpx.HTTPError(
                f"Expected 302 redirect from {archive_download_url}, got {redirect_response.status_code}"
            )
        location = redirect_response.headers.get("location")
        if not location:
            raise httpx.HTTPError(f"Missing Location header on redirect from {archive_download_url}")
        return location

    async def _download_and_extract_zip(
        self,
        signed_url: str,
        dest_path: Path,
        timeout: float | None = None,
    ) -> None:
        """Anonymous fetch (no bearer token to S3) + zip-slip-validated extractall."""
        effective_timeout = self._effective_timeout(timeout)
        async with httpx.AsyncClient(timeout=effective_timeout) as anonymous_client:
            download_response = await anonymous_client.get(signed_url)
            download_response.raise_for_status()

        dest_path.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(download_response.content)) as zf:
            dest_root = dest_path.resolve()
            for info in zf.infolist():
                name = info.filename
                if name.startswith("/") or ".." in Path(name).parts:
                    raise ValueError(f"Zip-slip detected: {name}")
                target = (dest_path / name).resolve()
                if target != dest_root and dest_root not in target.parents:
                    raise ValueError(f"Zip-slip detected: {name}")
            zf.extractall(dest_path)

    async def download_artifact(
        self,
        archive_download_url: str,
        dest_path: Path,
        timeout: float | None = None,
    ) -> None:
        """
        Downloads and extracts a workflow run artifact zip into ``dest_path``.

        GitHub API Documentation:
        https://docs.github.com/en/rest/actions/artifacts#download-an-artifact

        The GitHub API responds to the artifact endpoint with a 302 redirect to a
        short-lived signed URL on a third-party host (typically S3). This method
        fetches the redirect with the authenticated client, then follows the
        ``Location`` header with a fresh **unauthenticated** client so the GitHub
        bearer token is not leaked to the redirect target. Each zip member is
        validated against ``dest_path`` before extraction (zip-slip protection).

        This performs a single attempt with no retries; any failure propagates to the
        caller.

        Args:
            archive_download_url: The artifact's ``archive_download_url`` (absolute or relative to the API base).
            dest_path: Directory where the zip contents will be extracted. Created if missing.
            timeout: Optional timeout for both HTTP requests.
        """
        location = await self._resolve_artifact_redirect(archive_download_url, timeout)
        await self._download_and_extract_zip(location, dest_path, timeout)


# ---------------------------------------------------------------------------
# Async context manager
# ---------------------------------------------------------------------------


@asynccontextmanager
async def async_github_client(
    token: str,
    *,
    rate_limiter: InstrumentedAsyncLimiter | None = None,
    default_timeout: float = 30.0,
    max_rate_limit_retries: int = 2,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncIterator[AsyncGitHubClient]:
    """
    Async context manager that creates an AsyncGitHubClient and ensures it is closed on exit.

    Rate-limit protection is on by default; the governor paces requests and supplies the backoff for
    retries. Header-confirmed rate-limit responses (403/429) are retried, transport errors and
    non-rate-limit statuses are not, and RateLimitWaitAbandoned propagates to the caller when the
    governor is configured with a wait budget. The default protection logs through the
    ``ddev.utils.github_async.defaults`` logger.

    Args:
        token: GitHub personal access token or app token.
        rate_limiter: Overrides the default rate limiter; None uses the built-in default. This
            selects which limiter to use, it does not enable or disable protection (protection is
            always on).
        default_timeout: Default per-request HTTP timeout in seconds. Bounds individual HTTP
            requests only, not governor waits.
        max_rate_limit_retries: Extra attempts for a header-confirmed rate-limit response.
        transport: Optional custom HTTPX transport (useful for testing with MockTransport).

    Yields:
        AsyncGitHubClient: A ready-to-use async GitHub client.
    """
    client = AsyncGitHubClient(
        token=token,
        rate_limiter=rate_limiter,
        default_timeout=default_timeout,
        max_rate_limit_retries=max_rate_limit_retries,
        transport=transport,
    )
    try:
        yield client
    finally:
        await client.aclose()
