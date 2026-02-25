# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async GitHub API client with 1:1 endpoint mapping."""
from __future__ import annotations

import asyncio
from time import time
from typing import Any

import httpx


class GitHubAsyncClient:
    """Async GitHub API client with direct endpoint mapping."""

    API_VERSION = '2022-11-28'
    BASE_URL = 'https://api.github.com'

    def __init__(self, token: str, timeout: float = 30.0):
        """
        Initialize the async GitHub client.

        Args:
            token: GitHub personal access token
            timeout: Request timeout in seconds
        """
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

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make an async HTTP request with rate limit handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: URL path (relative to base_url)
            params: Query parameters
            json: JSON body

        Returns:
            httpx.Response object
        """
        await self._ensure_client()

        response = await self._client.request(method, url, params=params, json=json)

        # Handle GitHub rate limiting
        if response.status_code == 403 and response.headers.get('X-RateLimit-Remaining') == '0':
            reset_time = float(response.headers.get('X-RateLimit-Reset', 0))
            wait_time = reset_time - time() + 1
            await asyncio.sleep(wait_time)
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
    ) -> dict[str, Any]:
        """
        List workflow runs.

        https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-repository

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Optional workflow ID or filename
            **kwargs: Additional query parameters (status, branch, event, per_page, etc.)

        Returns:
            Dict with 'workflow_runs' list
        """
        if workflow_id:
            url = f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs'
        else:
            url = f'/repos/{owner}/{repo}/actions/runs'

        response = await self._request('GET', url, params=kwargs)
        return response.json()

    async def get_workflow_run(self, owner: str, repo: str, run_id: int) -> dict[str, Any]:
        """
        Get a workflow run.

        https://docs.github.com/en/rest/actions/workflow-runs#get-a-workflow-run
        """
        response = await self._request('GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}')
        return response.json()

    async def cancel_workflow_run(self, owner: str, repo: str, run_id: int) -> None:
        """
        Cancel a workflow run.

        https://docs.github.com/en/rest/actions/workflow-runs#cancel-a-workflow-run
        """
        await self._request('POST', f'/repos/{owner}/{repo}/actions/runs/{run_id}/cancel')

    async def list_workflow_run_jobs(
        self, owner: str, repo: str, run_id: int, **kwargs: Any
    ) -> dict[str, Any]:
        """
        List jobs for a workflow run.

        https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID
            **kwargs: Additional query parameters (filter, per_page, page)

        Returns:
            Dict with 'jobs' list
        """
        response = await self._request('GET', f'/repos/{owner}/{repo}/actions/runs/{run_id}/jobs', params=kwargs)
        return response.json()

    # Workflows API - https://docs.github.com/en/rest/actions/workflows

    async def create_workflow_dispatch(
        self, owner: str, repo: str, workflow_id: str | int, ref: str, inputs: dict[str, Any] | None = None
    ) -> None:
        """
        Trigger a workflow dispatch event.

        https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event

        Args:
            owner: Repository owner
            repo: Repository name
            workflow_id: Workflow ID or filename (e.g., 'test.yml')
            ref: Git ref (branch or tag name)
            inputs: Optional workflow inputs
        """
        json_data: dict[str, Any] = {'ref': ref}
        if inputs:
            json_data['inputs'] = inputs

        await self._request('POST', f'/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches', json=json_data)
