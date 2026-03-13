# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import httpx
import pytest

from ddev.utils.github_async import AsyncGitHubClient


class TestAsyncGitHubClient:
    """Tests for the async GitHub client."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test that the client can be used as an async context manager."""
        async with AsyncGitHubClient(token='test_token') as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_generic_request(self, respx_mock):
        """Test generic request method."""
        owner, repo = 'DataDog', 'integrations-core'

        respx_mock.get(
            f'https://api.github.com/repos/{owner}/{repo}/issues',
            params={'state': 'open'},
        ).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {'id': 1, 'title': 'Issue 1'},
                    {'id': 2, 'title': 'Issue 2'},
                ],
                headers={'x-ratelimit-remaining': '4999'},
            )
        )

        async with AsyncGitHubClient(token='test_token') as client:
            result = await client.request('GET', f'/repos/{owner}/{repo}/issues', params={'state': 'open'})

            assert isinstance(result.data, list)
            assert len(result.data) == 2
            assert result.data[0]['id'] == 1
            assert result.headers['x-ratelimit-remaining'] == '4999'

    @pytest.mark.asyncio
    async def test_pagination(self, respx_mock):
        """Test pagination extraction from Link header."""
        owner, repo = 'DataDog', 'integrations-core'

        link_header = (
            '<https://api.github.com/repos/DataDog/integrations-core/issues?page=2>; rel="next", '
            '<https://api.github.com/repos/DataDog/integrations-core/issues?page=5>; rel="last"'
        )
        respx_mock.get(f'https://api.github.com/repos/{owner}/{repo}/issues').mock(
            return_value=httpx.Response(
                200,
                json=[{'id': 1}],
                headers={'Link': link_header},
            )
        )

        async with AsyncGitHubClient(token='test_token') as client:
            result = await client.request('GET', f'/repos/{owner}/{repo}/issues')

            assert result.pagination.next_url == 'https://api.github.com/repos/DataDog/integrations-core/issues?page=2'
            assert result.pagination.last_url == 'https://api.github.com/repos/DataDog/integrations-core/issues?page=5'
