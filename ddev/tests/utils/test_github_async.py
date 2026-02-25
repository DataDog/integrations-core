# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from time import time

import httpx
import pytest

from ddev.utils.github_async import GitHubAsyncClient


class TestGitHubAsyncClient:
    """Tests for the async GitHub client."""

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test that the client can be used as an async context manager."""
        async with GitHubAsyncClient(token='test_token') as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_list_workflow_runs(self, respx_mock):
        """Test listing workflow runs."""
        owner, repo = 'DataDog', 'integrations-core'

        respx_mock.get(
            f'https://api.github.com/repos/{owner}/{repo}/actions/runs',
            params={'status': 'completed', 'per_page': 10},
        ).mock(return_value=httpx.Response(200, json={
            'total_count': 1,
            'workflow_runs': [
                {
                    'id': 123456,
                    'name': 'Test Workflow',
                    'status': 'completed',
                    'conclusion': 'success',
                }
            ]
        }))

        async with GitHubAsyncClient(token='test_token') as client:
            result = await client.list_workflow_runs(owner, repo, status='completed', per_page=10)

            assert result['total_count'] == 1
            assert len(result['workflow_runs']) == 1
            assert result['workflow_runs'][0]['id'] == 123456

    @pytest.mark.asyncio
    async def test_get_workflow_run(self, respx_mock):
        """Test getting a specific workflow run."""
        owner, repo, run_id = 'DataDog', 'integrations-core', 123456

        respx_mock.get(
            f'https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}'
        ).mock(return_value=httpx.Response(200, json={
            'id': run_id,
            'name': 'Test Workflow',
            'status': 'completed',
            'conclusion': 'success',
        }))

        async with GitHubAsyncClient(token='test_token') as client:
            result = await client.get_workflow_run(owner, repo, run_id)

            assert result['id'] == run_id
            assert result['status'] == 'completed'

    @pytest.mark.asyncio
    async def test_cancel_workflow_run(self, respx_mock):
        """Test canceling a workflow run."""
        owner, repo, run_id = 'DataDog', 'integrations-core', 123456

        respx_mock.post(
            f'https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/cancel'
        ).mock(return_value=httpx.Response(202))

        async with GitHubAsyncClient(token='test_token') as client:
            # Should not raise
            await client.cancel_workflow_run(owner, repo, run_id)

    @pytest.mark.asyncio
    async def test_list_workflow_run_jobs(self, respx_mock):
        """Test listing jobs for a workflow run."""
        owner, repo, run_id = 'DataDog', 'integrations-core', 123456

        respx_mock.get(
            f'https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs'
        ).mock(return_value=httpx.Response(200, json={
            'total_count': 2,
            'jobs': [
                {'id': 1, 'name': 'Job 1', 'status': 'completed'},
                {'id': 2, 'name': 'Job 2', 'status': 'in_progress'},
            ]
        }))

        async with GitHubAsyncClient(token='test_token') as client:
            result = await client.list_workflow_run_jobs(owner, repo, run_id)

            assert result['total_count'] == 2
            assert len(result['jobs']) == 2

    @pytest.mark.asyncio
    async def test_create_workflow_dispatch(self, respx_mock):
        """Test triggering a workflow dispatch."""
        owner, repo, workflow_id = 'DataDog', 'integrations-core', 'test.yml'

        respx_mock.post(
            f'https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches'
        ).mock(return_value=httpx.Response(204))

        async with GitHubAsyncClient(token='test_token') as client:
            # Should not raise
            await client.create_workflow_dispatch(
                owner, repo, workflow_id, ref='main', inputs={'test': 'value'}
            )

    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, respx_mock):
        """Test that rate limiting is handled properly."""
        owner, repo = 'DataDog', 'integrations-core'

        # First request hits rate limit
        respx_mock.get(
            f'https://api.github.com/repos/{owner}/{repo}/actions/runs'
        ).mock(
            side_effect=[
                httpx.Response(
                    403,
                    headers={
                        'X-RateLimit-Remaining': '0',
                        'X-RateLimit-Reset': str(int(time() + 0.1)),  # Reset in 0.1s
                    }
                ),
                httpx.Response(200, json={'total_count': 0, 'workflow_runs': []}),
            ]
        )

        async with GitHubAsyncClient(token='test_token') as client:
            result = await client.list_workflow_runs(owner, repo)
            assert result['total_count'] == 0
