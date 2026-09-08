# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Pull request list responses shared by Dispatcher CLI and resolution tests."""

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequestSimple

PR_NUMBER = 4242
HEAD_SHA = 'head-sha-aaa'


def listed_pull_request(
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_ref: str = 'a-target-branch',
    state: str = 'open',
    head_repo: str | None = 'DataDog/integrations-core',
    head_ref: str = 'hs/a-branch',
) -> PullRequestSimple:
    """List endpoints omit diff totals, so they cannot stand in for the full form."""
    return PullRequestSimple(
        number=number,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{number}',
        state=state,
        head={
            'ref': head_ref,
            'sha': head_sha,
            'repo': {'full_name': head_repo} if head_repo is not None else None,
        },
        base={'ref': base_ref, 'sha': 'base-sha-bbb'},
    )


def pulls_page(*pulls: PullRequestSimple) -> GitHubResponse[list[PullRequestSimple]]:
    return GitHubResponse[list[PullRequestSimple]].model_validate({'data': list(pulls), 'headers': {}})
