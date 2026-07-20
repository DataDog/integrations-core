# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the FakeAsyncGitHubClient helper itself."""

from __future__ import annotations

import httpx
import pytest

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import Artifact, ArtifactsList, PullRequest
from tests.helpers.github_async import FakeAsyncGitHubClient


@pytest.fixture
def fake() -> FakeAsyncGitHubClient:
    return FakeAsyncGitHubClient()


async def test_default_response_used_when_no_mock_registered(fake: FakeAsyncGitHubClient) -> None:
    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    assert isinstance(response.data, PullRequest)
    assert response.data.number == 1


def test_unknown_method_without_default_raises(fake: FakeAsyncGitHubClient) -> None:
    with pytest.raises(AssertionError, match='No mock registered'):
        fake._call('not_a_real_method')


async def test_sticky_mock_with_inner_data_is_auto_wrapped(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=42, html_url='https://x/42'))

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert isinstance(response, GitHubResponse)
    assert response.data.number == 42


async def test_sticky_mock_with_full_response_passes_through(fake: FakeAsyncGitHubClient) -> None:
    full = GitHubResponse.model_validate(
        {'data': PullRequest(number=99, html_url='https://x/99'), 'headers': {'x-rate-limit': '5'}}
    )
    fake.mock_response('create_pull_request', full)

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert response is full
    assert response.headers['x-rate-limit'] == '5'


async def test_sticky_mock_partial_match_only_fires_for_matching_call(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=7, html_url='https://x/7'), draft=True)

    # Default fires for non-matching calls.
    default = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=False)
    assert default.data.number == 1

    # Mock fires for matching calls.
    matched = await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=True)
    assert matched.data.number == 7


async def test_most_recent_sticky_mock_wins(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=1, html_url='https://x/1'))
    fake.mock_response('create_pull_request', PullRequest(number=2, html_url='https://x/2'))

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert response.data.number == 2


async def test_exception_response_raises(fake: FakeAsyncGitHubClient) -> None:
    err = httpx.HTTPStatusError('boom', request=httpx.Request('POST', 'https://x'), response=httpx.Response(422))
    fake.mock_response('create_pull_request', err)

    with pytest.raises(httpx.HTTPStatusError):
        await fake.create_pull_request('o', 'r', 'T', 'h', 'b')


async def test_one_shot_consumed_then_falls_through_to_sticky(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=10, html_url='https://x/10'), once=True)
    fake.mock_response('create_pull_request', PullRequest(number=99, html_url='https://x/99'))  # sticky

    first = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    second = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    third = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    assert first.data.number == 10  # one-shot
    assert second.data.number == 99  # sticky
    assert third.data.number == 99  # sticky


async def test_multiple_one_shots_fire_in_registration_order(fake: FakeAsyncGitHubClient) -> None:
    """The retry pattern: first call errors, second succeeds."""
    err = httpx.HTTPStatusError('try again', request=httpx.Request('POST', 'https://x'), response=httpx.Response(500))
    fake.mock_response('create_pull_request', err, once=True)
    fake.mock_response('create_pull_request', PullRequest(number=5, html_url='https://x/5'), once=True)

    with pytest.raises(httpx.HTTPStatusError):
        await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    response = await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    assert response.data.number == 5


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


async def test_assert_all_responses_consumed_passes_when_empty(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=5, html_url='https://x/5'), once=True)
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    fake.assert_all_responses_consumed()  # must not raise


async def test_assert_all_responses_consumed_fails_with_pending(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('create_pull_request', PullRequest(number=1, html_url='https://x/1'), once=True)
    fake.mock_response('create_pull_request', PullRequest(number=2, html_url='https://x/2'), once=True)

    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    with pytest.raises(AssertionError, match='not consumed'):
        fake.assert_all_responses_consumed()


async def test_assert_called_once_with_passes_on_single_exact_match(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    fake.assert_called_once_with(
        'create_pull_request',
        owner='o',
        repo='r',
        title='T',
        head='h',
        base='b',
        body='',
        draft=False,
        timeout=None,
    )


async def test_assert_called_once_with_fails_when_called_twice(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    with pytest.raises(AssertionError, match=r'Expected exactly one call to .* got 2'):
        fake.assert_called_once_with(
            'create_pull_request',
            owner='o',
            repo='r',
            title='T',
            head='h',
            base='b',
            body='',
            draft=False,
            timeout=None,
        )


async def test_assert_called_once_with_fails_on_wrong_kwargs(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=False)

    with pytest.raises(AssertionError, match=r'Expected one call to .* with .* got kwargs'):
        fake.assert_called_once_with(
            'create_pull_request',
            owner='o',
            repo='r',
            title='T',
            head='h',
            base='b',
            body='',
            draft=True,
            timeout=None,
        )


async def test_last_call_returns_most_recent(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T1', 'h', 'b')
    await fake.create_pull_request('o', 'r', 'T2', 'h', 'b')

    last = fake.last_call('create_pull_request')

    assert last.method == 'create_pull_request'
    assert last.kwargs['title'] == 'T2'


def test_last_call_raises_when_no_calls_recorded(fake: FakeAsyncGitHubClient) -> None:
    with pytest.raises(AssertionError, match='No calls to'):
        fake.last_call('create_pull_request')


async def test_assert_called_with_passes_on_exact_match(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')
    await fake.create_pull_request('o', 'r', 'OTHER', 'h', 'b')

    fake.assert_called_with(
        'create_pull_request',
        owner='o',
        repo='r',
        title='T',
        head='h',
        base='b',
        body='',
        draft=False,
        timeout=None,
    )


async def test_assert_called_with_fails_when_no_match(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    with pytest.raises(AssertionError, match='No call to'):
        fake.assert_called_with(
            'create_pull_request',
            owner='o',
            repo='r',
            title='WRONG',
            head='h',
            base='b',
            body='',
            draft=False,
            timeout=None,
        )


async def test_assert_not_called_passes_when_method_unused(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    fake.assert_not_called('add_labels_to_issue')


async def test_assert_not_called_fails_when_method_was_called(fake: FakeAsyncGitHubClient) -> None:
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b')

    with pytest.raises(AssertionError, match='Expected no calls'):
        fake.assert_not_called('create_pull_request')


async def test_calls_are_recorded_regardless_of_response(fake: FakeAsyncGitHubClient) -> None:
    err = httpx.HTTPStatusError('boom', request=httpx.Request('POST', 'https://x'), response=httpx.Response(500))
    fake.mock_response('create_pull_request', err, once=True)
    fake.mock_response('create_pull_request', PullRequest(number=5, html_url='https://x/5'))

    with pytest.raises(httpx.HTTPStatusError):
        await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=True)
    await fake.create_pull_request('o', 'r', 'T', 'h', 'b', draft=False)

    assert len(fake.calls_to('create_pull_request')) == 2


# ---------------------------------------------------------------------------
# list_workflow_run_artifacts (async generator) and download_artifact (no return)
# ---------------------------------------------------------------------------


async def test_list_workflow_run_artifacts_yields_a_single_page(fake: FakeAsyncGitHubClient) -> None:
    page = ArtifactsList(total_count=1, artifacts=[Artifact(id=1, name='a', expired=False)])
    fake.mock_response('list_workflow_run_artifacts', page)

    pages = [p async for p in fake.list_workflow_run_artifacts('o', 'r', 123)]

    assert len(pages) == 1
    assert isinstance(pages[0], GitHubResponse)
    assert pages[0].data.artifacts[0].id == 1
    assert fake.calls_to('list_workflow_run_artifacts')[0].kwargs['run_id'] == 123


async def test_list_workflow_run_artifacts_yields_multiple_pages(fake: FakeAsyncGitHubClient) -> None:
    page1 = ArtifactsList(total_count=2, artifacts=[Artifact(id=1, name='a', expired=False)])
    page2 = ArtifactsList(total_count=2, artifacts=[Artifact(id=2, name='b', expired=False)])
    fake.mock_response('list_workflow_run_artifacts', [page1, page2])

    ids = [p.data.artifacts[0].id async for p in fake.list_workflow_run_artifacts('o', 'r', 123)]

    assert ids == [1, 2]


async def test_list_workflow_run_artifacts_raises_registered_exception(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('list_workflow_run_artifacts', RuntimeError('boom-list'))

    with pytest.raises(RuntimeError, match='boom-list'):
        [p async for p in fake.list_workflow_run_artifacts('o', 'r', 123)]


async def test_download_artifact_returns_none_and_records_call(fake: FakeAsyncGitHubClient) -> None:
    result = await fake.download_artifact('https://x/1/zip', '/tmp/dest')

    assert result is None
    call = fake.calls_to('download_artifact')[0]
    assert call.kwargs['archive_download_url'] == 'https://x/1/zip'
    assert call.kwargs['dest_path'] == '/tmp/dest'


async def test_download_artifact_raises_for_matching_url(fake: FakeAsyncGitHubClient) -> None:
    fake.mock_response('download_artifact', RuntimeError('boom-download'), archive_download_url='https://x/2/zip')

    await fake.download_artifact('https://x/1/zip', '/tmp/dest')  # non-matching: default no-op
    with pytest.raises(RuntimeError, match='boom-download'):
        await fake.download_artifact('https://x/2/zip', '/tmp/dest')
