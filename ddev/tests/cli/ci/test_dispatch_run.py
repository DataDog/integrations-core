# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ddev.cli.ci.dispatch_run import PullRequestResolver, head_is_fork
from ddev.cli.ci.tests.changes import ChangeResolutionError
from ddev.utils.github_async.models import PullRequestRef
from tests.cli.ci.helpers import HEAD_SHA, listed_pull_request, pulls_page

if TYPE_CHECKING:
    from tests.helpers.github_async import FakeAsyncGitHubClient


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('head_repo', 'DataDog/other-fork'),
        ('head_repo', None),
        ('head_ref', 'another-branch'),
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
        head_ref='hs/a-branch',
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
        head_ref='hs/a-branch',
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
    head = PullRequestRef(
        ref='a-branch', sha=HEAD_SHA, repo={'full_name': head_repo} if head_repo is not None else None
    )

    assert head_is_fork(head, owner='DataDog', repo='integrations-core') is expected
