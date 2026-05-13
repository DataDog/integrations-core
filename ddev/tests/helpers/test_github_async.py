# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the FakeAsyncGitHubClient helper itself."""

from __future__ import annotations

import httpx
import pytest

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequest
from tests.helpers.github_async import FakeAsyncGitHubClient


@pytest.fixture
def fake() -> FakeAsyncGitHubClient:
    return FakeAsyncGitHubClient()


@pytest.mark.asyncio
async def test_default_response_used_when_no_mock_registered(fake: FakeAsyncGitHubClient) -> None:
    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    assert isinstance(response.data, PullRequest)
    assert response.data.number == 1


@pytest.mark.asyncio
async def test_unknown_method_without_default_raises(fake: FakeAsyncGitHubClient) -> None:
    fake._default_response_factories.pop('add_labels_to_issue')
    with pytest.raises(AssertionError, match='No mock registered'):
        await fake.add_labels_to_issue('o', 'r', 1, ['bug'])


@pytest.mark.asyncio
async def test_sticky_mock_with_inner_data_is_auto_wrapped(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=42, html_url='https://x/42'))

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert isinstance(response, GitHubResponse)
    assert response.data.number == 42


@pytest.mark.asyncio
async def test_sticky_mock_with_full_response_passes_through(fake: FakeAsyncGitHubClient) -> None:
    full = GitHubResponse.model_validate(
        {'data': PullRequest(number=99, html_url='https://x/99'), 'headers': {'x-rate-limit': '5'}}
    )
    fake.mock_response('create_pull_request', full)

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert response is full
    assert response.headers['x-rate-limit'] == '5'


@pytest.mark.asyncio
async def test_sticky_mock_partial_match_only_fires_for_matching_call(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=7, html_url='https://x/7'), draft=True)

    # Default fires for non-matching calls.
    default = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=False)
    assert default.data.number == 1

    # Mock fires for matching calls.
    matched = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=True)
    assert matched.data.number == 7


@pytest.mark.asyncio
async def test_most_recent_sticky_mock_wins(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=1, html_url='https://x/1'))
    fake.mock_response('create_pull_request', PullRequest(number=2, html_url='https://x/2'))

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert response.data.number == 2


@pytest.mark.asyncio
async def test_exception_response_raises(fake: FakeAsyncGitHubClient) -> None:
    err = httpx.HTTPStatusError('boom', request=httpx.Request('POST', 'https://x'), response=httpx.Response(422))
    fake.mock_response('create_pull_request', err)

    with pytest.raises(httpx.HTTPStatusError):
        await fake.create_pull_request('o', 'r', 'T', 'h', 'b')


@pytest.mark.asyncio
async def test_one_shot_consumed_then_falls_through_to_sticky(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=10, html_url='https://x/10'), once=True)
    fake.mock_response('create_pull_request', PullRequest(number=99, html_url='https://x/99'))  # sticky

    first = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    second = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    third = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert first.data.number == 10  # one-shot
    assert second.data.number == 99  # sticky
    assert third.data.number == 99  # sticky


@pytest.mark.asyncio
async def test_multiple_one_shots_fire_in_registration_order(fake: FakeAsyncGitHubClient) -> None:
    """The retry pattern: first call errors, second succeeds."""
    err = httpx.HTTPStatusError('try again', request=httpx.Request('POST', 'https://x'), response=httpx.Response(500))
    fake.mock_response('create_pull_request', err, once=True)
    fake.mock_response('create_pull_request', PullRequest(number=5, html_url='https://x/5'), once=True)

    with pytest.raises(httpx.HTTPStatusError):
        await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    assert response.data.number == 5


@pytest.mark.asyncio
async def test_one_shot_with_match_kwargs_only_consumed_when_match(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response(
        'create_pull_request',
        PullRequest(number=7, html_url='https://x/7'),
        once=True,
        draft=True,
    )

    # Non-matching call ignores the one-shot, hits built-in default.
    non_match = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=False)
    assert non_match.data.number == 1

    # Matching call consumes the one-shot.
    match = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=True)
    assert match.data.number == 7

    # Second matching call: one-shot is gone, falls through to default.
    next_match = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=True)
    assert next_match.data.number == 1


@pytest.mark.asyncio
async def test_assert_all_responses_consumed_passes_when_empty(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=5, html_url='https://x/5'), once=True)
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    fake.assert_all_responses_consumed()  # must not raise


@pytest.mark.asyncio
async def test_assert_all_responses_consumed_fails_with_pending(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=1, html_url='https://x/1'), once=True)
    fake.mock_response('create_pull_request', PullRequest(number=2, html_url='https://x/2'), once=True)

    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    with pytest.raises(AssertionError, match='not consumed'):
        fake.assert_all_responses_consumed()


@pytest.mark.asyncio
async def test_calls_are_recorded_regardless_of_response(fake: FakeAsyncGitHubClient) -> None:
    err = httpx.HTTPStatusError('boom', request=httpx.Request('POST', 'https://x'), response=httpx.Response(500))
    fake.mock_response('create_pull_request', err, once=True)
    fake.mock_response('create_pull_request', PullRequest(number=5, html_url='https://x/5'))

    with pytest.raises(httpx.HTTPStatusError):
        await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=True)
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=False)

    assert len(fake.calls_to('create_pull_request')) == 2
