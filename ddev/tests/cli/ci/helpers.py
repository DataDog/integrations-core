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
from ddev.utils.github_async.models import PullRequestSimple, PullRequestState, WorkflowJobConclusion
from tests.helpers.github_async import (
    FakeAsyncGitHubClient,
    make_pull_request_ref,
    make_pull_request_repo,
    make_pull_request_simple,
    make_response,
    make_workflow_job,
    make_workflow_jobs_list,
)

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
    return make_pull_request_simple(
        number=number,
        state=PullRequestState(state),
        head=make_pull_request_ref(
            ref=head_branch,
            sha=head_sha,
            repo=None if head_repo is None else make_pull_request_repo(full_name=head_repo),
        ),
        base=make_pull_request_ref(ref=base_branch, sha='base-sha-bbb', repo=None),
    )


def pulls_page(*pulls: PullRequestSimple) -> GitHubResponse[list[PullRequestSimple]]:
    return make_response(list(pulls))


def mock_job_result(fake: FakeAsyncGitHubClient, job: BatchJob, conclusion: str) -> None:
    fake.mock_response(
        "list_workflow_jobs",
        make_workflow_jobs_list([make_workflow_job(name=job.name, conclusion=WorkflowJobConclusion(conclusion))]),
    )
