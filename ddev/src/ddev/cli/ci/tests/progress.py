# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Aggregate state the gatherer owns and the PR updater renders.

``DispatcherProgress`` -> ``BatchProgress`` -> ``JobProgress`` -> ``JobAttemptProgress``: batches,
their planned jobs, and each job's executions in attempt order.

``conclusion`` is the one GitHub value kept, as its enum, because it distinguishes outcomes
(cancelled, timed out, action required) that ``Status`` collapses.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.status import Status
from ddev.utils.junit import TestStatus

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ddev.cli.ci.tests.messages import BatchJob
    from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
    from ddev.utils.junit import JUnitReport, JUnitTestCase


class ProgressError(StrEnum):
    """Why a batch or execution is unavailable, as a closed set to branch on rather than prose."""

    TIMED_OUT = auto()
    NO_JOB_RESULTS = auto()
    NO_ARTIFACTS = auto()


class ExecutionState(Enum):
    """Where an execution is in its lifecycle, orthogonal to its outcome (``Status``).

    ``RUNNING`` and ``RETRYING`` become reachable with the retry work.
    """

    PLANNED = "planned"
    RUNNING = "running"
    RETRYING = "retrying"
    FINISHED = "finished"


@dataclass(frozen=True)
class JobAttemptProgress:
    """One observed execution of one planned job.

    An attempt exists only because the job ran, so ``status`` is always known: an undetermined job
    has no attempt. ``attempt`` is its 1-based position in the job's history. ``job_id``,
    ``conclusion`` and ``job_url`` are ``None`` when GitHub never reported the job.
    """

    attempt: int
    job_id: int | None
    status: Status
    conclusion: WorkflowJobConclusion | None
    failed_steps: tuple[str, ...]
    job_url: str | None
    reports: tuple[JUnitReport, ...]
    error: ProgressError | None = None

    @property
    def failed_tests(self) -> list[JUnitTestCase]:
        """Every failed/errored test case across this execution's reports."""
        return [
            case
            for report in self.reports
            for suite in report.test_suites
            for case in suite.test_cases
            if case.status in (TestStatus.FAILED, TestStatus.ERROR)
        ]


@dataclass(frozen=True)
class JobProgress:
    """One logical planned job throughout execution.

    ``attempts`` can be sparse: a job that already succeeded does not run again in a failed-job rerun.
    """

    job: BatchJob
    attempts: tuple[JobAttemptProgress, ...]

    @property
    def latest(self) -> JobAttemptProgress | None:
        """The most recent execution: the only attempt that counts toward totals."""
        return self.attempts[-1] if self.attempts else None

    @property
    def retry_count(self) -> int:
        """Executions minus one. Not ``run_attempt - 1``: histories can be sparse."""
        return max(0, len(self.attempts) - 1)


@dataclass(frozen=True)
class BatchProgress:
    """One logical batch, from planning through its terminal outcome.

    ``status`` is the workflow's own, not a roll-up of ``jobs_progress``: a workflow can fail in a
    step no tracked job covers. It stays ``None`` until ``FINISHED``.
    """

    batch_id: str
    run_id: int | None
    workflow_url: str | None
    state: ExecutionState
    status: Status | None
    current_attempt: int | None
    max_attempts: int
    retries_remaining: int
    retrying_jobs: tuple[BatchJob, ...]
    jobs_progress: tuple[JobProgress, ...]
    error: ProgressError | None = None


@dataclass(frozen=True)
class DispatcherProgress:
    """The complete point-in-time aggregate across all batches.

    Carries all state known at its revision, so the PR updater renders the newest snapshot and
    discards the rest. The counters derive from ``JobProgress.latest`` only, so a job retried to
    success counts once.
    """

    batches: tuple[BatchProgress, ...]
    done: bool

    @property
    def passed(self) -> int:
        return self._count(Status.SUCCESS)

    @property
    def failed(self) -> int:
        return self._count(Status.FAILURE)

    @property
    def skipped(self) -> int:
        return self._count(Status.SKIPPED)

    @property
    def complete(self) -> int:
        """Planned jobs that have run."""
        return sum(1 for job in self._jobs_progress if job.latest is not None)

    @property
    def total(self) -> int:
        """Every planned job, run or not."""
        return sum(1 for _ in self._jobs_progress)

    @property
    def _jobs_progress(self) -> Iterator[JobProgress]:
        return (job for batch in self.batches for job in batch.jobs_progress)

    def _count(self, status: Status) -> int:
        return sum(1 for job in self._jobs_progress if job.latest is not None and job.latest.status == status)
