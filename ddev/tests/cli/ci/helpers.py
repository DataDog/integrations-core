# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""GitHub payloads shared by Dispatcher CLI and component tests."""

import base64
import gzip
import json
from typing import Any

from ddev.cli.ci.tests.messages import BatchJob
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequestSimple, WorkflowJob, WorkflowJobsList
from tests.helpers.github_async import FakeAsyncGitHubClient

PR_NUMBER = 4242
HEAD_SHA = 'head-sha-aaa'


def decode_job_list(encoded: str) -> list[dict[str, Any]]:
    return json.loads(gzip.decompress(base64.b64decode(encoded)).decode())


def listed_pull_request(
    number: int = PR_NUMBER,
    head_sha: str = HEAD_SHA,
    base_branch: str = 'a-target-branch',
    state: str = 'open',
    head_repo: str | None = 'DataDog/integrations-core',
    head_branch: str = 'hs/a-branch',
) -> PullRequestSimple:
    """List endpoints omit diff totals, so they cannot stand in for the full form."""
    return PullRequestSimple(
        number=number,
        html_url=f'https://github.com/DataDog/integrations-core/pull/{number}',
        state=state,
        head={
            'ref': head_branch,
            'sha': head_sha,
            'repo': {'full_name': head_repo} if head_repo is not None else None,
        },
        base={'ref': base_branch, 'sha': 'base-sha-bbb'},
    )


def pulls_page(*pulls: PullRequestSimple) -> GitHubResponse[list[PullRequestSimple]]:
    return GitHubResponse[list[PullRequestSimple]].model_validate({'data': list(pulls), 'headers': {}})


def mock_job_result(fake: FakeAsyncGitHubClient, job: BatchJob, conclusion: str) -> None:
    fake.mock_response(
        "list_workflow_jobs",
        WorkflowJobsList(
            total_count=1,
            jobs=[WorkflowJob(id=1, run_id=123, name=job.name, status="completed", conclusion=conclusion)],
        ),
    )
