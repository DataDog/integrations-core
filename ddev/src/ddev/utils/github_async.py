# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async GitHub API client with 1:1 endpoint mapping."""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ddev.config.file import ConfigFileWithOverrides

# Common GitHub API pagination keys
PAGINATION_KEYS = frozenset(
    [
        'items',
        'workflows',
        'workflow_runs',
        'jobs',
        'repositories',
        'issues',
        'pull_requests',
        'artifacts',
        'users',
        'commits',
        'releases',
        'tags',
        'branches',
        'checks',
        'annotations',
    ]
)


class PaginationInfo(BaseModel):
    """GitHub API pagination information from Link header."""

    model_config = ConfigDict(extra="ignore")

    next_url: str | None = None
    prev_url: str | None = None
    first_url: str | None = None
    last_url: str | None = None


class GitHubResponse[T](BaseModel):
    """Generic response model for GitHub API responses."""

    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    pagination: PaginationInfo = Field(default_factory=PaginationInfo)

    # Store raw response data for backward compatibility
    _raw_data: T | None = None
    _headers: dict[str, str] = {}

    @property
    def data(self) -> T | None:
        """Access raw response data for backward compatibility."""
        return self._raw_data

    @property
    def headers(self) -> dict[str, str]:
        """Access response headers for backward compatibility."""
        return self._headers

    @classmethod
    def from_response(cls, data: T | None, headers: dict[str, str], pagination: PaginationInfo):
        """Create response from raw data."""
        instance = cls(pagination=pagination)
        instance._raw_data = data
        instance._headers = headers
        return instance


class WorkflowRun(BaseModel):
    """GitHub workflow run response model."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str | None = None
    status: str
    conclusion: str | None = None
    html_url: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class Workflow(BaseModel):
    """GitHub workflow response model."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    path: str
    state: str | None = None


class Artifact(BaseModel):
    """GitHub artifact response model."""

    model_config = ConfigDict(extra="ignore")

    id: int
    name: str
    size_in_bytes: int | None = None
    url: str | None = None
    archive_download_url: str | None = None
    expired: bool = False


class ArtifactsResponse(GitHubResponse[dict[str, Any]]):
    """Response for list artifacts endpoint."""

    total_count: int = 0
    artifacts: list[Artifact] = Field(default_factory=list)


class IssueComment(BaseModel):
    """GitHub issue comment response model."""

    model_config = ConfigDict(extra="ignore")

    id: int
    body: str
    user: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
    html_url: str | None = None


class AsyncGitHubClient:
    """Async GitHub API client with direct endpoint mapping."""

    API_VERSION = '2022-11-28'
    BASE_URL = 'https://api.github.com'

    def __init__(self, token: str | None = None, timeout: float = 30.0):
        """
        Initialize the async GitHub client.

        Args:
            token: GitHub personal access token. If not provided, loads from ddev config.
            timeout: Request timeout in seconds
        """
        if token is None:
            config_file = ConfigFileWithOverrides()
            config_file.load()
            token = config_file.combined_model.github.token

        if not token:
            msg = (
                "GitHub token not found. Please provide a token or set one of: "
                "DD_GITHUB_TOKEN, GH_TOKEN, or GITHUB_TOKEN environment variable"
            )
            raise ValueError(msg)

        self._token = token
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _ensure_client(self):
        """Ensure the async client is initialized."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    'Authorization': f'Bearer {self._token}',
                    'X-GitHub-Api-Version': self.API_VERSION,
                },
                timeout=self._timeout,
            )

    async def close(self):
        """Close the async client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # Compile regex pattern once for efficiency
    _link_pattern = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')

    def _extract_pagination(self, headers: httpx.Headers) -> PaginationInfo:
        """Extract pagination information from Link header."""
        link_header = headers.get('Link')
        if not link_header:
            return PaginationInfo()

        # Use regex to efficiently parse Link header
        links = {f'{rel}_url': url for url, rel in self._link_pattern.findall(link_header)}
        return PaginationInfo(**links)

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Make an async HTTP request."""
        await self._ensure_client()
        assert self._client is not None  # Set by _ensure_client()

        response = await self._client.request(method, url, params=params, json=json)
        response.raise_for_status()
        return response

    async def request[T](
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> GitHubResponse[T]:
        """
        Generic request for any GitHub API endpoint.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE, etc.)
            url: URL path (relative to base_url or absolute GitHub API URL)
            params: Query parameters
            json_body: JSON request body

        Returns:
            GitHubResponse[T] with data accessible via .data property, headers via .headers property
        """
        response = await self._request(method, url, params=params, json=json_body)

        # Handle JSON responses and empty responses
        data = response.json() if response.content else None

        return GitHubResponse[T].from_response(
            data=data,
            headers=dict(response.headers),
            pagination=self._extract_pagination(response.headers),
        )

    async def iter_pages[T](
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> AsyncIterator[GitHubResponse[T]]:
        """
        Async generator that yields each page of a paginated response.

        Args:
            method: HTTP method (typically GET)
            url: URL path (relative to base_url or absolute GitHub API URL)
            params: Query parameters
            json_body: JSON request body

        Yields:
            GitHubResponse[T] for each page
        """
        current_url: str | None = url
        current_params = params
        current_body = json_body

        while current_url:
            response: GitHubResponse[T] = await self.request(
                method, current_url, params=current_params, json_body=current_body
            )
            yield response

            if not response.pagination.next_url:
                break

            # Use full URL from Link header for subsequent requests
            current_url = response.pagination.next_url
            current_params = None
            current_body = None

    async def request_all_pages[T](
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        auto_paginate: bool = True,
    ) -> GitHubResponse[list[T] | dict[str, Any]]:
        """
        Fetch all pages automatically for paginated endpoints.

        Args:
            method: HTTP method (typically GET)
            url: URL path (relative to base_url or absolute GitHub API URL)
            params: Query parameters
            json_body: JSON request body
            auto_paginate: Whether to automatically fetch all pages (default: True)

        Returns:
            GitHubResponse with all pages merged into a single list or dict with paginated items
        """
        if not auto_paginate:
            # Single page request
            return await self.request(method, url, params=params, json_body=json_body)

        all_data: list[Any] = []
        wrapper_key: str | None = None
        last_response: GitHubResponse[T] | None = None
        total_count: int | None = None

        async for response in self.iter_pages(method, url, params=params, json_body=json_body):
            last_response = response

            # Extract list data from response
            if isinstance(response.data, list):
                all_data.extend(response.data)
            elif isinstance(response.data, dict):
                # Look for list data in dict
                list_key = self._find_list_key(response.data)
                if list_key:
                    all_data.extend(response.data[list_key])
                    wrapper_key = list_key
                    # Preserve total_count if present
                    if 'total_count' in response.data:
                        total_count = response.data['total_count']
                else:
                    # No list found, treat as single item
                    all_data.append(response.data)

        # Reconstruct wrapped response if needed
        if wrapper_key and last_response:
            result_data: dict[str, Any] = {wrapper_key: all_data}
            if total_count is not None:
                result_data['total_count'] = total_count
            return GitHubResponse[dict[str, Any]].from_response(
                data=result_data,
                headers=last_response.headers,
                pagination=last_response.pagination,
            )

        return GitHubResponse[list[T]].from_response(
            data=all_data,
            headers=last_response.headers if last_response else {},
            pagination=last_response.pagination if last_response else PaginationInfo(),
        )

    def _find_list_key(self, data: dict[str, Any]) -> str | None:
        """Find the key containing list data in a dict."""
        # Check known pagination keys first for efficiency
        for key in PAGINATION_KEYS:
            if key in data and isinstance(data[key], list):
                return key

        # Fall back to checking any list value
        for key, value in data.items():
            if isinstance(value, list) and value:
                return key

        return None

    async def create_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int,
        ref: str,
        inputs: dict[str, Any] | None = None,
    ) -> GitHubResponse[None]:
        """
        Create a workflow dispatch event.

        https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow ID or workflow file name (e.g., 'main.yml')
            ref: Git reference (branch or tag name)
            inputs: Input parameters defined in the workflow file

        Returns:
            GitHubResponse[None] with None data (204 No Content on success)
        """
        body: dict[str, Any] = {'ref': ref}
        if inputs:
            body['inputs'] = inputs

        return await self.request(
            'POST', f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches', json_body=body
        )

    async def get_workflow_run(self, owner: str, repo: str, run_id: int) -> GitHubResponse[dict[str, Any]]:
        """
        Get a workflow run.

        https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            GitHubResponse with workflow run data including status, conclusion, and other metadata
        """
        return await self.request('GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}')

    async def list_workflow_run_artifacts(
        self, owner: str, repo: str, run_id: int, auto_paginate: bool = False, **kwargs: Any
    ) -> GitHubResponse[dict[str, Any]]:
        """
        List workflow run artifacts.

        https://docs.github.com/en/rest/actions/artifacts#list-workflow-run-artifacts

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID
            auto_paginate: Whether to automatically fetch all pages (default: False)
            **kwargs: Additional query parameters (per_page, page, name)

        Returns:
            GitHubResponse with dict containing 'artifacts' list and total_count (all pages if auto_paginate=True)
        """
        if auto_paginate:
            result = await self.request_all_pages[dict[str, Any]](
                'GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts', params=kwargs, auto_paginate=True
            )
            # The artifacts endpoint always returns dict format
            return result
        return await self.request('GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts', params=kwargs)

    async def create_issue_comment(
        self, owner: str, repo: str, issue_number: int, body: str
    ) -> GitHubResponse[dict[str, Any]]:
        """
        Create a comment on an issue or pull request.

        https://docs.github.com/en/rest/issues/comments#create-an-issue-comment

        Args:
            owner: Repository owner
            repo: Repository name
            issue_number: Issue or pull request number
            body: Comment body text

        Returns:
            GitHubResponse with created comment data
        """
        return await self.request(
            'POST', f'/repos/{owner}/{repo}/issues/{issue_number}/comments', json_body={'body': body}
        )
