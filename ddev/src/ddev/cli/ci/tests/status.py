# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Internal status vocabulary for the ci/tests task pipeline.

GitHub's workflow-run/-job conclusions are a wide set of strings (see the models in
`ddev.utils.github_async.models`). `Status` is the narrow vocabulary the batch and PR-comment
layers use internally, and `conclusion_to_status` is the single place that collapses a GitHub
conclusion into it. The job-state helpers below say where a job is in its life on a runner,
for the metrics that measure queueing and execution.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum, auto

from ddev.utils.github_async.models.workflow import WorkflowJob, WorkflowJobConclusion, WorkflowJobStatus

# Must match `timeout-minutes` of the `test` and `test_fork` jobs in `.github/workflows/test-batch.yml`.
TEST_JOB_TIMEOUT_MINUTES = 120


class Status(StrEnum):
    """Outcome of a batch, job, or test as reported internally.

    `CANCELLED` and `INCONCLUSIVE` count as neither passed nor failed. `INCONCLUSIVE` never comes
    from GitHub: the gatherer assigns it to a job whose final state it could not confirm.
    """

    SUCCESS = auto()
    FAILURE = auto()
    SKIPPED = auto()
    CANCELLED = auto()
    INCONCLUSIVE = auto()


def conclusion_to_status(conclusion: str | None) -> Status:
    """Map a GitHub Actions conclusion to the internal `Status`.

    `None` maps to `Status.FAILURE`: a run that finished without saying how did not succeed.
    Every other non-success, non-skipped conclusion (`timed_out`, `neutral`, ...) is a failure.
    """
    if conclusion == WorkflowJobConclusion.SUCCESS:
        return Status.SUCCESS
    if conclusion == WorkflowJobConclusion.SKIPPED:
        return Status.SKIPPED
    if conclusion == WorkflowJobConclusion.CANCELLED:
        return Status.CANCELLED
    return Status.FAILURE


def is_queued(job: WorkflowJob) -> bool:
    """Whether a job is waiting for a runner. `requested` is GitHub's own bookkeeping, not a wait."""
    return job.status in {WorkflowJobStatus.QUEUED, WorkflowJobStatus.WAITING, WorkflowJobStatus.PENDING}


def has_run(job: WorkflowJob) -> bool:
    """Whether a job completed after running on a runner, so its timestamps measure execution.

    Runner assignment is GitHub's own record of the job starting: skipped jobs and jobs cancelled
    while queued were never picked up, so their timestamps measure nothing.
    """
    return job.status is WorkflowJobStatus.COMPLETED and job.runner_name is not None


def has_started_running(job: WorkflowJob) -> bool:
    """Whether a job is known to have started on a runner, including one that finished between polls."""
    return job.status is WorkflowJobStatus.IN_PROGRESS or has_run(job)


def timed_out(job: WorkflowJob) -> bool:
    """Whether a completed job was stopped by the test jobs' `timeout-minutes`.

    GitHub reports a timeout stop as `cancelled`. The only tell is a job that ran to the limit, so a
    job cancelled while queued never qualifies.
    """
    if job.status is not WorkflowJobStatus.COMPLETED:
        return False
    if job.conclusion is WorkflowJobConclusion.TIMED_OUT:
        return True
    if job.conclusion is not WorkflowJobConclusion.CANCELLED:
        return False
    duration = job.duration_seconds
    return has_run(job) and duration is not None and duration >= TEST_JOB_TIMEOUT_MINUTES * 60


def job_status(job: WorkflowJob) -> Status:
    """A completed job's internal status: a timeout stop is a failure, not a cancellation."""
    if timed_out(job):
        return Status.FAILURE
    return conclusion_to_status(job.conclusion)


def batch_status(conclusion: str | None, jobs: Iterable[WorkflowJob]) -> Status:
    """A finished run's batch status; a run cancelled by a job timeout is a failure."""
    status = conclusion_to_status(conclusion)
    if status is Status.CANCELLED and any(timed_out(job) for job in jobs):
        return Status.FAILURE
    return status
