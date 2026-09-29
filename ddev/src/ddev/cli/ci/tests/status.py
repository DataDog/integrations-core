# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Internal status vocabulary for the ci/tests task pipeline.

GitHub's workflow-run/-job conclusions are a wide set of strings (see the models in
``ddev.utils.github_async.models``). ``Status`` is the narrow, binary vocabulary the batch
and PR-comment layers use internally, and ``conclusion_to_status`` is the single place that
collapses a GitHub conclusion into it. The job-state helpers below say where a job is in its
life on a runner, for the metrics that measure queueing and execution.
"""

from __future__ import annotations

from enum import StrEnum, auto

from ddev.utils.github_async.models.workflow import WorkflowJob, WorkflowJobConclusion, WorkflowJobStatus


class Status(StrEnum):
    """Binary outcome of a batch, job, or test as reported internally."""

    SUCCESS = auto()
    FAILURE = auto()
    SKIPPED = auto()


def conclusion_to_status(conclusion: str | None) -> Status:
    """Map a GitHub Actions conclusion to the internal :class:`Status`.

    ``None`` maps to ``Status.FAILURE``: a run that finished without saying how did not succeed.
    """
    if conclusion == WorkflowJobConclusion.SUCCESS:
        return Status.SUCCESS
    if conclusion == WorkflowJobConclusion.SKIPPED:
        return Status.SKIPPED
    return Status.FAILURE


def is_queued(job: WorkflowJob) -> bool:
    """Whether a job is waiting for a runner. `requested` is GitHub's own bookkeeping, not a wait."""
    return job.status in {WorkflowJobStatus.QUEUED, WorkflowJobStatus.WAITING, WorkflowJobStatus.PENDING}


def has_finished_running(job: WorkflowJob) -> bool:
    """Whether a job completed after running on a runner.

    Skipped and cancelled jobs may never have started, so their timestamps measure neither how long
    a job runs nor how long it waited for a runner.
    """
    return job.status is WorkflowJobStatus.COMPLETED and job.conclusion in {
        WorkflowJobConclusion.SUCCESS,
        WorkflowJobConclusion.FAILURE,
        WorkflowJobConclusion.TIMED_OUT,
    }


def has_started_running(job: WorkflowJob) -> bool:
    """Whether a job is known to have started on a runner, including one that finished between polls."""
    return job.status is WorkflowJobStatus.IN_PROGRESS or has_finished_running(job)
