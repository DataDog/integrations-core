# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Factories for the async GitHub client's API models, for tests of code that uses the client.

Every `make_<model>` builds the model through its constructor, so validation runs, and gives every
field a realistic default, so a test passes only what it cares about. The raw payloads in
`tests/utils/github_async/payloads.py` remain the source of the client suite's own wire-level tests.

Where one field's default depends on another, that default is `UNSET` and derived from the field it
depends on; an explicit value, including `None`, always wins over the derivation.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum, auto

from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import (
    Artifact,
    ArtifactsList,
    CheckRun,
    CheckRunConclusion,
    CheckRunStatus,
    CommitInfo,
    ContentType,
    FileCommit,
    FileContent,
    GitHubUser,
    GitObject,
    GitReference,
    IssueComment,
    JobStep,
    JobStepStatus,
    Label,
    PullRequest,
    PullRequestFile,
    PullRequestFileStatus,
    PullRequestRef,
    PullRequestRepo,
    PullRequestReviewComment,
    PullRequestSimple,
    PullRequestState,
    WorkflowDispatchResult,
    WorkflowJob,
    WorkflowJobConclusion,
    WorkflowJobsList,
    WorkflowJobStatus,
    WorkflowRun,
)


class Unset(Enum):
    """Marker for a factory default that is derived from another argument."""

    TOKEN = auto()


UNSET = Unset.TOKEN

# Default timing of both a job and a completed run, so a test asserting the default duration
# references the constant instead of repeating the literals.
DEFAULT_STARTED_AT = '2026-01-01T10:00:00Z'
DEFAULT_COMPLETED_AT = '2026-01-01T10:01:30Z'
DEFAULT_DURATION_SECONDS = 90.0


def make_response[T](data: T, headers: dict[str, str] | None = None) -> GitHubResponse[T]:
    return GitHubResponse(data=data, headers=headers if headers is not None else {})


def make_github_user(
    *,
    id: int | None = 1,
    login: str | None = 'octocat',
    html_url: str | None | Unset = UNSET,
    type: str | None = 'User',
) -> GitHubUser:
    if html_url is UNSET:
        html_url = f'https://github.com/{login}'
    return GitHubUser(id=id, login=login, html_url=html_url, type=type)


def make_label(
    *,
    id: int = 1,
    name: str = 'test-label',
    color: str | None = None,
    description: str | None = None,
) -> Label:
    return Label(id=id, name=name, color=color, description=description)


def make_issue_comment(
    *,
    id: int = 1,
    body: str = '',
    user: GitHubUser | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    html_url: str | None | Unset = UNSET,
) -> IssueComment:
    if html_url is UNSET:
        html_url = f'https://github.com/DataDog/integrations-core/issues/1#issuecomment-{id}'
    return IssueComment(id=id, body=body, user=user, created_at=created_at, updated_at=updated_at, html_url=html_url)


def make_pull_request_review_comment(
    *,
    id: int = 1,
    body: str = '',
    path: str = 'file.py',
    commit_id: str = 'abc123',
    html_url: str | None = None,
    created_at: str | None = None,
    updated_at: str | None = None,
    user: GitHubUser | None = None,
) -> PullRequestReviewComment:
    return PullRequestReviewComment(
        id=id,
        body=body,
        path=path,
        commit_id=commit_id,
        html_url=html_url,
        created_at=created_at,
        updated_at=updated_at,
        user=user,
    )


def make_git_object(
    *,
    type: str = 'commit',
    sha: str = 'a' * 40,
    url: str | Unset = UNSET,
) -> GitObject:
    if url is UNSET:
        url = f'https://api.github.com/repos/DataDog/integrations-core/git/commits/{sha}'
    return GitObject(type=type, sha=sha, url=url)


def make_git_reference(
    *,
    ref: str = 'refs/heads/main',
    node_id: str = 'REF_kwDO',
    url: str | Unset = UNSET,
    object: GitObject | None = None,
) -> GitReference:
    if url is UNSET:
        url = f'https://api.github.com/repos/DataDog/integrations-core/git/ref/{ref}'
    return GitReference(ref=ref, node_id=node_id, url=url, object=object if object is not None else make_git_object())


def make_file_content(
    *,
    type: ContentType = ContentType.FILE,
    encoding: str = 'base64',
    size: int = 3,
    name: str = 'release.json',
    path: str = 'release.json',
    content: str = 'e30K',
    sha: str = 'b' * 40,
) -> FileContent:
    return FileContent(type=type, encoding=encoding, size=size, name=name, path=path, content=content, sha=sha)


def make_commit_info(
    *,
    sha: str | None = 'c' * 40,
    html_url: str | None | Unset = UNSET,
) -> CommitInfo:
    if html_url is UNSET:
        html_url = f'https://github.com/DataDog/integrations-core/commit/{sha}' if sha is not None else None
    return CommitInfo(sha=sha, html_url=html_url)


def make_file_commit(*, commit: CommitInfo | None = None) -> FileCommit:
    return FileCommit(commit=commit if commit is not None else make_commit_info())


def make_check_run(
    *,
    id: int = 999,
    name: str = 'check',
    status: CheckRunStatus = CheckRunStatus.COMPLETED,
    conclusion: CheckRunConclusion | None | Unset = UNSET,
    html_url: str | None = None,
    head_sha: str = 'a' * 40,
) -> CheckRun:
    if conclusion is UNSET:
        conclusion = CheckRunConclusion.SUCCESS if status is CheckRunStatus.COMPLETED else None
    return CheckRun(id=id, name=name, status=status, conclusion=conclusion, html_url=html_url, head_sha=head_sha)


def make_pull_request_repo(*, full_name: str = 'DataDog/integrations-core') -> PullRequestRepo:
    return PullRequestRepo(full_name=full_name)


def make_pull_request_ref(
    *,
    ref: str = 'a-branch',
    sha: str = 'a' * 40,
    label: str | None = None,
    repo: PullRequestRepo | None | Unset = UNSET,
) -> PullRequestRef:
    if repo is UNSET:
        repo = make_pull_request_repo()
    return PullRequestRef(ref=ref, sha=sha, label=label, repo=repo)


def make_pull_request_file(
    *,
    filename: str = 'changed.py',
    status: PullRequestFileStatus = PullRequestFileStatus.MODIFIED,
    previous_filename: str | None = None,
) -> PullRequestFile:
    return PullRequestFile(filename=filename, status=status, previous_filename=previous_filename)


def make_pull_request_simple(
    *,
    number: int = 1,
    id: int | None = None,
    node_id: str | None = None,
    url: str | None | Unset = UNSET,
    html_url: str | Unset = UNSET,
    diff_url: str | None | Unset = UNSET,
    patch_url: str | None | Unset = UNSET,
    state: PullRequestState | None = PullRequestState.OPEN,
    draft: bool = False,
    locked: bool = False,
    merge_commit_sha: str | None = None,
    title: str | None = None,
    body: str | None = None,
    user: GitHubUser | None = None,
    assignees: Sequence[GitHubUser] = (),
    requested_reviewers: Sequence[GitHubUser] = (),
    labels: Sequence[Label] = (),
    created_at: str | None = None,
    updated_at: str | None = None,
    closed_at: str | None = None,
    merged_at: str | None = None,
    head: PullRequestRef | None = None,
    base: PullRequestRef | None = None,
) -> PullRequestSimple:
    if url is UNSET:
        url = f'https://api.github.com/repos/DataDog/integrations-core/pulls/{number}'
    if html_url is UNSET:
        html_url = f'https://github.com/DataDog/integrations-core/pull/{number}'
    if diff_url is UNSET:
        diff_url = f'https://github.com/DataDog/integrations-core/pull/{number}.diff'
    if patch_url is UNSET:
        patch_url = f'https://github.com/DataDog/integrations-core/pull/{number}.patch'
    return PullRequestSimple(
        number=number,
        id=id,
        node_id=node_id,
        url=url,
        html_url=html_url,
        diff_url=diff_url,
        patch_url=patch_url,
        state=state,
        draft=draft,
        locked=locked,
        merge_commit_sha=merge_commit_sha,
        title=title,
        body=body,
        user=user,
        assignees=list(assignees),
        requested_reviewers=list(requested_reviewers),
        labels=list(labels),
        created_at=created_at,
        updated_at=updated_at,
        closed_at=closed_at,
        merged_at=merged_at,
        head=head,
        base=base,
    )


def make_pull_request(
    *,
    number: int = 1,
    id: int | None = None,
    node_id: str | None = None,
    url: str | None | Unset = UNSET,
    html_url: str | Unset = UNSET,
    diff_url: str | None | Unset = UNSET,
    patch_url: str | None | Unset = UNSET,
    state: PullRequestState | None = PullRequestState.OPEN,
    draft: bool = False,
    locked: bool = False,
    merge_commit_sha: str | None = None,
    title: str | None = None,
    body: str | None = None,
    user: GitHubUser | None = None,
    assignees: Sequence[GitHubUser] = (),
    requested_reviewers: Sequence[GitHubUser] = (),
    labels: Sequence[Label] = (),
    created_at: str | None = None,
    updated_at: str | None = None,
    closed_at: str | None = None,
    merged_at: str | None = None,
    head: PullRequestRef | None = None,
    base: PullRequestRef | None = None,
    changed_files: int = 1,
    merged: bool | None = None,
) -> PullRequest:
    simple = make_pull_request_simple(
        number=number,
        id=id,
        node_id=node_id,
        url=url,
        html_url=html_url,
        diff_url=diff_url,
        patch_url=patch_url,
        state=state,
        draft=draft,
        locked=locked,
        merge_commit_sha=merge_commit_sha,
        title=title,
        body=body,
        user=user,
        assignees=assignees,
        requested_reviewers=requested_reviewers,
        labels=labels,
        created_at=created_at,
        updated_at=updated_at,
        closed_at=closed_at,
        merged_at=merged_at,
        head=head,
        base=base,
    )
    return PullRequest(**dict(simple), changed_files=changed_files, merged=merged)


def make_workflow_dispatch_result(
    *,
    workflow_run_id: int = 123,
    run_url: str | Unset = UNSET,
    html_url: str | Unset = UNSET,
) -> WorkflowDispatchResult:
    if run_url is UNSET:
        run_url = f'https://api.github.com/repos/DataDog/integrations-core/actions/runs/{workflow_run_id}'
    if html_url is UNSET:
        html_url = f'https://github.com/DataDog/integrations-core/actions/runs/{workflow_run_id}'
    return WorkflowDispatchResult(workflow_run_id=workflow_run_id, run_url=run_url, html_url=html_url)


def make_workflow_run(
    *,
    id: int = 123,
    name: str | None = 'test-batch',
    status: str | None = 'completed',
    conclusion: str | None | Unset = UNSET,
    html_url: str | Unset = UNSET,
    created_at: str | None = None,
    updated_at: str | None = DEFAULT_COMPLETED_AT,
    run_started_at: str | None = DEFAULT_STARTED_AT,
) -> WorkflowRun:
    if conclusion is UNSET:
        conclusion = 'success' if status == 'completed' else None
    if html_url is UNSET:
        html_url = f'https://github.com/DataDog/integrations-core/actions/runs/{id}'
    return WorkflowRun(
        id=id,
        name=name,
        status=status,
        conclusion=conclusion,
        html_url=html_url,
        created_at=created_at,
        updated_at=updated_at,
        run_started_at=run_started_at,
    )


def make_job_step(
    *,
    name: str = 'Run tests',
    status: JobStepStatus = JobStepStatus.COMPLETED,
    conclusion: str | None | Unset = UNSET,
    number: int | None = 1,
) -> JobStep:
    if conclusion is UNSET:
        conclusion = 'success' if status is JobStepStatus.COMPLETED else None
    return JobStep(name=name, status=status, conclusion=conclusion, number=number)


def make_workflow_job(
    *,
    id: int = 1,
    run_id: int = 123,
    name: str = 'test-job',
    status: WorkflowJobStatus = WorkflowJobStatus.COMPLETED,
    conclusion: WorkflowJobConclusion | None | Unset = UNSET,
    html_url: str | None | Unset = UNSET,
    started_at: str = DEFAULT_STARTED_AT,
    completed_at: str | None | Unset = UNSET,
    steps: Sequence[JobStep] = (),
) -> WorkflowJob:
    if conclusion is UNSET:
        conclusion = WorkflowJobConclusion.SUCCESS if status is WorkflowJobStatus.COMPLETED else None
    if html_url is UNSET:
        html_url = f'https://github.com/DataDog/integrations-core/actions/runs/{run_id}/job/{id}'
    if completed_at is UNSET:
        completed_at = DEFAULT_COMPLETED_AT if status is WorkflowJobStatus.COMPLETED else None
    return WorkflowJob(
        id=id,
        run_id=run_id,
        name=name,
        status=status,
        conclusion=conclusion,
        html_url=html_url,
        started_at=started_at,
        completed_at=completed_at,
        steps=list(steps),
    )


def make_artifacts_list(
    artifacts: Sequence[Artifact] = (),
    *,
    total_count: int | None = None,
) -> ArtifactsList:
    return ArtifactsList(
        total_count=len(artifacts) if total_count is None else total_count,
        artifacts=list(artifacts),
    )


def make_workflow_jobs_list(
    jobs: Sequence[WorkflowJob] = (),
    *,
    total_count: int | None = None,
) -> WorkflowJobsList:
    return WorkflowJobsList(
        total_count=len(jobs) if total_count is None else total_count,
        jobs=list(jobs),
    )


def make_artifact(
    *,
    id: int = 1,
    name: str | Unset = UNSET,
    size_in_bytes: int | None = 100,
    url: str | None | Unset = UNSET,
    archive_download_url: str | None | Unset = UNSET,
    expired: bool = False,
) -> Artifact:
    if name is UNSET:
        name = f'artifact-{id}'
    if url is UNSET:
        url = f'https://api.github.com/artifact/{id}'
    if archive_download_url is UNSET:
        archive_download_url = f'https://api.github.com/artifact/{id}/zip'
    return Artifact(
        id=id,
        name=name,
        size_in_bytes=size_in_bytes,
        url=url,
        archive_download_url=archive_download_url,
        expired=expired,
    )
