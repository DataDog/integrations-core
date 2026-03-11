# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Async GitHub API client with 1:1 endpoint mapping."""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from ddev.config.file import ConfigFileWithOverrides


class PaginationInfo(BaseModel):
    """GitHub API pagination information from Link header."""

    model_config = ConfigDict(extra="ignore")

    next_url: str | None = None
    prev_url: str | None = None
    first_url: str | None = None
    last_url: str | None = None


class GitHubResponse[T](BaseModel):
    """Response wrapper containing data, headers, and pagination information."""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    data: T
    headers: dict[str, str]
    pagination: PaginationInfo


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

    def _extract_pagination(self, headers: httpx.Headers) -> PaginationInfo:
        """Extract pagination information from Link header."""
        link_header = headers.get('Link')
        if not link_header:
            return PaginationInfo()

        links = {}
        # Parse Link header: <url>; rel="next", <url>; rel="last"
        for link in link_header.split(','):
            parts = link.strip().split(';')
            if len(parts) != 2:
                continue

            url = parts[0].strip().strip('<>')
            rel = parts[1].strip()

            # Extract rel value (e.g., rel="next" -> next)
            if 'rel=' in rel:
                rel_value = rel.split('=')[1].strip().strip('"')
                links[f'{rel_value}_url'] = url

        return PaginationInfo(**links)

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """
        Make an async HTTP request .

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
            GitHubResponse with typed data, headers dict, and pagination info
        """
        response = await self._request(method, url, params=params, json=json_body)

        # Parse response data - handle both JSON responses and empty responses
        try:
            data = response.json()
        except Exception:
            data = None

        return GitHubResponse(
            data=data,
            headers=dict(response.headers),
            pagination=self._extract_pagination(response.headers),
        )

    async def request_all_pages[T](
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> GitHubResponse[list[T]]:
        """
        Fetch all pages automatically for paginated endpoints.

        Args:
            method: HTTP method (typically GET)
            url: URL path (relative to base_url or absolute GitHub API URL)
            params: Query parameters
            json_body: JSON request body

        Returns:
            GitHubResponse with all pages merged into a single list
        """
        all_data: list[T] = []
        current_url: str | None = url
        last_headers: dict[str, str] = {}
        last_pagination = PaginationInfo()

        while current_url:
            response = await self.request(method, current_url, params=params, json_body=json_body)
            last_headers = response.headers
            last_pagination = response.pagination

            # Extract list data from response
            # GitHub typically returns paginated data in arrays or in a wrapper with 'items' or specific keys
            if isinstance(response.data, list):
                all_data.extend(response.data)
            elif isinstance(response.data, dict):
                # Try common pagination patterns
                for key in ['items', 'workflows', 'workflow_runs', 'jobs', 'repositories', 'issues', 'pull_requests']:
                    if key in response.data and isinstance(response.data[key], list):
                        all_data.extend(response.data[key])
                        break
                else:
                    # If no known list key found, treat the whole dict as a single item
                    all_data.append(response.data)

            # Move to next page
            current_url = response.pagination.next_url
            # Only use params on first request, subsequent requests use the full next_url
            params = None

        return GitHubResponse(
            data=all_data,
            headers=last_headers,
            pagination=last_pagination,
        )

    # Workflows API - https://docs.github.com/en/rest/actions/workflows

    async def list_workflows(self, owner: str, repo: str, **kwargs: Any) -> GitHubResponse[dict[str, Any]]:
        """
        List workflows for a repository.

        https://docs.github.com/en/rest/actions/workflows#list-repository-workflows

        Args:
            owner: Repository owner
            repo: Repository name
            **kwargs: Additional query parameters (per_page, page)

        Returns:
            GitHubResponse with dict containing 'workflows' list and headers
        """
        return await self.request('GET', f'/repos/{owner}/{repo}/actions/workflows', params=kwargs)
