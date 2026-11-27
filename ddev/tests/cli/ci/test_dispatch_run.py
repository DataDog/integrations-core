# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import pytest

from ddev.cli.ci.dispatch_run import (
    PullRequestResolver,
    ResolvedRun,
    changes_for_run,
    head_is_fork,
    resolution_github_client,
)
from ddev.cli.ci.tests.changes import ChangeResolutionError
from ddev.utils.git import GitCommit
from tests.cli.ci.helpers import HEAD_SHA, listed_pull_request, pulls_page
from tests.helpers.github_async import make_pull_request_ref, make_pull_request_repo
from tests.helpers.monitoring import make_monitor

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from tests.helpers.github_async import FakeAsyncGitHubClient


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('head_repo', 'DataDog/other-fork'),
        ('head_repo', None),
        ('head_branch', 'another-branch'),
        ('head_sha', 'a-newer-sha'),
        ('state', 'closed'),
    ],
    ids=['different-repository', 'deleted-repository', 'different-branch', 'stale-sha', 'closed'],
)
async def test_head_lookup_excludes_nonmatching_pull_requests(
    fake_async_github: FakeAsyncGitHubClient, field: str, value: str | None
):
    fake_async_github.mock_response('list_pull_requests', pulls_page(listed_pull_request(**{field: value})))

    resolver = PullRequestResolver(
        owner='DataDog',
        repo='integrations-core',
        head_repo='DataDog/integrations-core',
        head_branch='hs/a-branch',
        head_sha=HEAD_SHA,
    )

    assert await resolver.resolve(fake_async_github) is None


async def test_head_lookup_refuses_incomplete_results(fake_async_github: FakeAsyncGitHubClient):
    response = pulls_page(listed_pull_request())
    response.headers['link'] = '<https://api.github.com/repos/DataDog/integrations-core/pulls?page=2>; rel="next"'
    fake_async_github.mock_response('list_pull_requests', response)

    resolver = PullRequestResolver(
        owner='DataDog',
        repo='integrations-core',
        head_repo='DataDog/integrations-core',
        head_branch='hs/a-branch',
        head_sha=HEAD_SHA,
    )

    with pytest.raises(ChangeResolutionError, match='more than one page'):
        await resolver.resolve(fake_async_github)


@pytest.mark.parametrize(
    ('head_repo', 'expected'),
    [
        pytest.param('DataDog/integrations-core', False, id='same-repository'),
        pytest.param('datadog/Integrations-Core', False, id='same-repository-other-casing'),
        pytest.param('attacker/integrations-core', True, id='fork'),
        pytest.param('DataDog/integrations-core-evil', True, id='name-that-only-starts-the-same'),
        pytest.param(None, True, id='deleted-head-repository'),
    ],
)
def test_head_is_fork(head_repo: str | None, expected: bool):
    """A fork must not receive same-repository credentials."""
    head = make_pull_request_ref(
        ref='a-branch',
        sha=HEAD_SHA,
        repo=None if head_repo is None else make_pull_request_repo(full_name=head_repo),
    )

    assert head_is_fork(head, owner='DataDog', repo='integrations-core') is expected


def commit_run(**fields) -> ResolvedRun:
    return ResolvedRun(
        **{
            'repository': 'DataDog/integrations-core',
            'checkout_sha': 'a-sha',
            'head_sha': 'a-sha',
            'head_branch': 'master',
            'all_targets': False,
            **fields,
        }
    )


@pytest.mark.parametrize(
    ('fields', 'expected'),
    [
        pytest.param({'pr_number': 7, 'context': 'pr'}, 'pr-7', id='pull-request'),
        pytest.param({}, 'master-a-sha', id='master-push'),
        pytest.param({'context': 'nightly'}, 'nightly-a-sha', id='nightly'),
    ],
)
def test_concurrency_key_separates_runs_on_one_commit_by_context(fields: dict, expected: str):
    """A nightly run and a master push on the same commit must not cancel each other's batches."""
    assert commit_run(**fields).concurrency_key == expected


@pytest.mark.parametrize(
    'fields',
    [pytest.param({'targets': ('ntp',)}, id='targets'), pytest.param({'all_targets': True}, id='all')],
)
def test_a_run_that_names_its_scope_skips_the_comparison(mocker: MockerFixture, fields: dict):
    """Explicit targets are not limited to what the commit changed, so there is nothing to diff."""
    app = mocker.MagicMock()
    app.repo.git.latest_commit.return_value = GitCommit('a-sha')
    compare = mocker.patch('ddev.cli.ci.tests.changes.changes_in_commit')

    assert changes_for_run(app, run=commit_run(**fields)) is None
    compare.assert_not_called()


def test_exclusions_alone_still_compare_the_commit(mocker: MockerFixture):
    app = mocker.MagicMock()
    app.repo.git.latest_commit.return_value = GitCommit('a-sha')
    compare = mocker.patch('ddev.cli.ci.tests.changes.changes_in_commit', return_value=[])

    assert changes_for_run(app, run=commit_run(exclude_targets=('ddev',))) == []
    compare.assert_called_once()


def test_the_resolution_client_is_instrumented_from_its_monitor(mocker: MockerFixture):
    """An uninstrumented session spends the same GitHub quota the governor thinks it manages."""
    opened: list[dict] = []

    @asynccontextmanager
    async def record(**kwargs):
        opened.append(kwargs)
        yield mocker.MagicMock()

    mocker.patch('ddev.utils.github_async.async_github_client', record)

    factory = resolution_github_client('a-token', monitor=make_monitor('resolution'))

    async def open_once():
        async with factory():
            pass

    asyncio.run(open_once())

    [kwargs] = opened
    assert kwargs['token'] == 'a-token'
    assert all(kwargs[name] is not None for name in ('logger', 'observer', 'rate_limiter'))


def test_every_resolution_session_shares_one_rate_limiter(mocker: MockerFixture):
    """A limiter per session would let the resolvers overspend the quota it exists to bound."""
    opened: list[dict] = []

    @asynccontextmanager
    async def record(**kwargs):
        opened.append(kwargs)
        yield mocker.MagicMock()

    mocker.patch('ddev.utils.github_async.async_github_client', record)
    factory = resolution_github_client('a-token', monitor=make_monitor('resolution'))

    async def open_twice():
        async with factory():
            pass
        async with factory():
            pass

    asyncio.run(open_twice())

    first, second = opened
    assert first['rate_limiter'] is second['rate_limiter']
