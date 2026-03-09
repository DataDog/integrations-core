# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async GitHub API client with 1:1 endpoint mapping."""

from __future__ import annotations

import asyncio
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ConfigDict

from ddev.config.file import ConfigFileWithOverrides

T = TypeVar('T')


class RateLimitInfo(BaseModel):
    """GitHub API throttling information from response headers."""

    model_config = ConfigDict(extra="ignore")

    retry_after: int | None = None


class GitHubResponse(BaseModel, Generic[T]):
    """Response wrapper containing data and throttling information."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    data: T
    rate_limit: RateLimitInfo


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

    def _extract_rate_limit(self, headers: httpx.Headers) -> RateLimitInfo:
        """Extract throttling information from response headers."""
        return RateLimitInfo(
            retry_after=int(headers['Retry-After']) if 'Retry-After' in headers else None,
        )

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make an async HTTP request with secondary rate limit (throttling) handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL path (relative to base_url)
            params: Query parameters
            json: JSON body

        Returns:
            httpx.Response object
        """
        await self._ensure_client()
        assert self._client is not None  # Set by _ensure_client()

        response = await self._client.request(method, url, params=params, json=json)

        # Handle secondary rate limiting (throttling) via Retry-After header
        if response.status_code in (403, 429) and 'Retry-After' in response.headers:
            retry_after = int(response.headers['Retry-After'])
            await asyncio.sleep(retry_after)
            # Retry after waiting
            response = await self._client.request(method, url, params=params, json=json)

        response.raise_for_status()
        return response

    # Workflow Runs API - https://docs.github.com/en/rest/actions/workflow-runs

    async def list_workflow_runs(
        self,
        owner: str,
        repo: str,
        workflow_id: str | int | None = None,
        **kwargs: Any,
    ) -> GitHubResponse[dict[str, Any]]:
        """
        List workflow runs.

        https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Optional workflow ID or filename
            **kwargs: Additional query parameters (status, branch, event, per_page, etc.)

        Returns:
            GitHubResponse with dict containing 'workflow_runs' list and throttling info
        """
        if workflow_id:
            url = f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs'
        else:
            url = f'/repos/{owner}/{repo}/actions/runs'

        response = await self._request('GET', url, params=kwargs)
        return GitHubResponse(data=response.json(), rate_limit=self._extract_rate_limit(response.headers))

    async def get_workflow_run(self, owner: str, repo: str, run_id: int) -> GitHubResponse[dict[str, Any]]:
        """
        Get a workflow run.

        https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run

        Returns:
            GitHubResponse with workflow run data and throttling info
        """
        response = await self._request('GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}')
        return GitHubResponse(data=response.json(), rate_limit=self._extract_rate_limit(response.headers))

    async def cancel_workflow_run(self, owner: str, repo: str, run_id: int) -> GitHubResponse[None]:
        """
        Cancel a workflow run.

        https://docs.github.com/en/rest/actions/workflow-runs#cancel-a-workflow-run

        Returns:
            GitHubResponse with None data and throttling info
        """
        response = await self._request('POST', f'/repos/{owner}/{repo}/actions/runs/{run_id}/cancel')
        return GitHubResponse(data=None, rate_limit=self._extract_rate_limit(response.headers))

    async def list_workflow_run_jobs(
        self, owner: str, repo: str, run_id: int, **kwargs: Any
    ) -> GitHubResponse[dict[str, Any]]:
        """
        List jobs for a workflow run.

        https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID
            **kwargs: Additional query parameters (filter, per_page, page)

        Returns:
            GitHubResponse with dict containing 'jobs' list and throttling info
        """
        response = await self._request('GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}/jobs', params=kwargs)
        return GitHubResponse(data=response.json(), rate_limit=self._extract_rate_limit(response.headers))

    # Workflows API - https://docs.github.com/en/rest/actions/workflows

    async def create_workflow_dispatch(
        self, owner: str, repo: str, workflow_id: str | int, ref: str, inputs: dict[str, Any] | None = None
    ) -> GitHubResponse[None]:
        """
        Trigger a workflow dispatch event.

        https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow ID or filename (e.g., 'test.yml')
            ref: Git ref (branch or tag name)
            inputs: Optional workflow inputs

        Returns:
            GitHubResponse with None data and throttling info
        """
        json_data: dict[str, Any] = {'ref': ref}
        if inputs:
            json_data['inputs'] = inputs

        response = await self._request(
            'POST', f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches', json=json_data
        )
        return GitHubResponse(data=None, rate_limit=self._extract_rate_limit(response.headers))
