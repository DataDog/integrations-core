# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Aggregate state the gatherer owns and the PR updater renders.

The hierarchy is ``DispatcherProgress`` -> ``BatchProgress`` -> ``JobProgress`` ->
``JobAttemptProgress``: the dispatcher snapshot contains batches, each batch contains its planned
jobs, and each job contains its executions in attempt order.

These objects are the only domain language the PR updater consumes. They deliberately contain no
GitHub API models: the runner turns API responses into execution facts, the gatherer normalizes them
into the objects below, and the renderer works from a complete immutable snapshot. ``conclusion`` is
the one GitHub value retained — as its ``WorkflowJobConclusion`` enum, never a bare string — because
it distinguishes outcomes (cancelled, timed out, action required) that ``Status`` collapses.

``BatchJob`` (in ``messages``) is the authoritative planned-job representation, so there is no
separate planned-job type here. Although it is not frozen, every component treats each instance as
immutable after planning.
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
    """Why a batch or execution is unavailable, as a closed set the renderer can branch on.

    A free-form message would force the PR updater to match on prose. The subject is already on the
    object carrying the error, so the member alone says everything: ``NO_ARTIFACTS`` on a job
    attempt means that job's artifacts, ``TIMED_OUT`` on a batch means that batch.
    """

    TIMED_OUT = auto()
    NO_JOB_RESULTS = auto()
    NO_ARTIFACTS = auto()


class ExecutionState(Enum):
    """Where an execution is in its lifecycle.

    Orthogonal to :class:`~ddev.cli.ci.tests.status.Status`, which is the normalized outcome: a
    batch that is not ``FINISHED`` has no final status. ``RUNNING`` and ``RETRYING`` become
    reachable with the retry work (``BatchAttemptFinished``); until then a batch is ``PLANNED``
    until its ``BatchFinished`` arrives.
    """

    PLANNED = "planned"
    RUNNING = "running"
    RETRYING = "retrying"
    FINISHED = "finished"


@dataclass(frozen=True)
class JobAttemptProgress:
    """One observed execution of one planned job.

    An attempt exists only because the job ran, so ``status`` is always known — a job whose outcome
    is undetermined has no attempt, not an attempt with an empty status. ``attempt`` is its 1-based
    position in the job's history; ``failed_steps`` holds every failing step name, since a job can
    fail more than one step; ``reports`` holds the complete parsed JUnit reports; ``error`` records
    what was unavailable, such as artifacts that never showed up.

    ``job_id``, ``conclusion`` and ``job_url`` come from the correlated workflow job and are ``None``
    only when GitHub never reported one, which today means the batch timed out.
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
        """Every failed/errored test case across this execution's reports, flattened for rendering."""
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

    ``attempts`` is the retained history in attempt order. It can be sparse, because a job that
    already succeeded does not run again in a failed-job rerun.
    """

    job: BatchJob
    attempts: tuple[JobAttemptProgress, ...]

    @property
    def latest(self) -> JobAttemptProgress | None:
        """The most recent execution — the only attempt that counts toward final totals."""
        return self.attempts[-1] if self.attempts else None

    @property
    def retry_count(self) -> int:
        """Executions minus one. Not ``run_attempt - 1``: histories can be sparse."""
        return max(0, len(self.attempts) - 1)


@dataclass(frozen=True)
class BatchProgress:
    """One logical batch, from planning through its terminal outcome.

    ``batch_id`` is Dispatcher's stable logical identity, unrelated to any message id. ``run_id`` and
    ``workflow_url`` are filled once GitHub has a run for the batch. ``status`` stays ``None`` until
    ``state`` is ``FINISHED``. ``jobs`` always covers every planned job, including those with no
    observed attempt yet.
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
    jobs: tuple[JobProgress, ...]
    error: ProgressError | None = None


@dataclass(frozen=True)
class DispatcherProgress:
    """The complete point-in-time aggregate across all batches.

    Every snapshot carries all state known at its revision — including batches that have not started
    — so the PR updater can render the newest one and discard the rest. ``revision`` is deliberately
    absent: it is message-ordering metadata owned by ``UpdatePRComment``.

    The counters below derive from ``JobProgress.latest`` only, so a job retried to success counts
    once, as passed.
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
        """Planned jobs that have run: an attempt carries an outcome by construction."""
        return sum(1 for job in self._jobs if job.latest is not None)

    @property
    def total(self) -> int:
        """Every planned job across every batch, whether it has run or not."""
        return sum(1 for _ in self._jobs)

    @property
    def _jobs(self) -> Iterator[JobProgress]:
        return (job for batch in self.batches for job in batch.jobs)

    def _count(self, status: Status) -> int:
        return sum(1 for job in self._jobs if job.latest is not None and job.latest.status == status)
