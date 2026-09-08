# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import logging
import shutil
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ddev.cli.ci.tests.messages import (
    BatchFinished,
    BatchJob,
    BatchJobResult,
    JobResult,
    UpdatePRComment,
    WorkflowStatus,
)
from ddev.cli.ci.tests.progress import (
    BatchProgress,
    DispatcherProgress,
    ExecutionState,
    JobAttemptProgress,
    JobProgress,
    ProgressError,
)
from ddev.cli.ci.tests.status import Status, conclusion_to_status
from ddev.event_bus.orchestrator import SyncProcessor
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.junit import parse_junit_dir

if TYPE_CHECKING:
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.utils.junit import JUnitReport

# Expected layout of the extracted ``test-result.zip`` tree (defined by ``test-batch.yaml``):
#   {artifacts_path}/
#     {artifact_name}/                one directory per job (its BatchJobResult.artifact_name_path)
#       coverage.xml                  Cobertura coverage report
#       test-{unit|e2e}-{env}.xml     pytest JUnit report(s)
# Each job's spec, workflow-job result, and artifact directory come pre-correlated on the message
# (BatchFinished.batch_jobs). A timed-out batch fails every job; otherwise each job's status is its own
# workflow-job conclusion, and a job with no correlated workflow job is a runner bug and raises.
COVERAGE_GLOB = "coverage*.xml"
JUNIT_GLOB = "test-*.xml"
# Every later update borrows the id of the ``BatchFinished`` that caused it. Revision ``0`` has no
# cause, so it carries its own.
INITIAL_UPDATE_MESSAGE_ID = "dispatcher-initial"


class TaskTestGatherer(SyncProcessor[BatchFinished]):
    """Builds each batch's results from the artifacts the runner downloaded, organizes the coverage
    and JUnit files, and publishes a ``DispatcherProgress`` snapshot per finished batch.

    Registries are keyed by ``batch_id``: it is stable across workflow attempts, ``run_id`` is not.
    """

    def __init__(self, name: str, output_base_path: Path, batches: list[TestBatch]) -> None:
        super().__init__(name)
        self._output_base_path = output_base_path
        self._revision = 0
        self._status_by_batch: dict[str, WorkflowStatus] = {}
        self._results_by_batch: dict[str, list[JobResult]] = {}
        # The whole plan, in planning order, so each snapshot covers batches that have not run yet.
        self._progress_by_batch: dict[str, BatchProgress] = {
            batch.batch_id: self._planned_batch(batch) for batch in batches
        }
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def process_message(self, message: BatchFinished) -> None:
        log_extra = {"batch_id": message.batch_id, "run_id": message.run_id}
        if not message.batch_jobs:
            # Still terminal and still worth a revision, or it renders as planned forever.
            self._logger.warning("BatchFinished carried no jobs; nothing to gather", extra=log_extra)

        # Rejected before gathering: gathering writes into the shared output tree, where a batch that
        # is not in the plan could overwrite the files another batch publishes.
        with self._lock:
            if not self._accepts(message.batch_id, log_extra):
                return

        gathered: list[tuple[JobResult, JobAttemptProgress]] = []
        for batch_job_result in message.batch_jobs:
            # Checked per job because a repository-wide batch has hundreds, and this runs in a thread
            # the bus cannot interrupt. Abandoned rather than partly registered: the batch stays
            # planned, so the run reports what it is, unfinished.
            if self.stopping:
                self._logger.warning(
                    "Gathering abandoned after %s of %s jobs: the bus is shutting down",
                    len(gathered),
                    len(message.batch_jobs),
                    extra=log_extra,
                )
                return
            gathered.append(self._gather_job(batch_job_result, message))

        results = [result for result, _ in gathered]
        status = self._build_workflow_status(message, results)

        # Register, bump the revision, and emit under one lock, so two batches finishing at once
        # cannot build a comment from half-updated state.
        with self._lock:
            # The per-job check cannot see a flip during the last job or while the status was built,
            # and this block is the publish gate: registering now would contradict a cancelled run.
            if self.stopping:
                self._logger.warning("Batch gathered but left unregistered: the bus is shutting down", extra=log_extra)
                return
            # Re-checked: another thread may have gathered this batch while this one parsed.
            if not self._accepts(message.batch_id, log_extra):
                return
            planned = self._progress_by_batch[message.batch_id]
            if results:
                self._results_by_batch[message.batch_id] = results
                self._status_by_batch[message.batch_id] = status
            self._progress_by_batch[message.batch_id] = self._finished_batch_progress(planned, message, gathered)
            self._revision += 1
            revision = self._revision
            done = self._done()
            self.submit_message(self.build_update_message(message.id, revision, done))

        self._logger.info(
            "Batch gathered, UpdatePRComment revision %s emitted (done=%s)",
            revision,
            done,
            extra=log_extra,
        )

    def _accepts(self, batch_id: str, log_extra: dict[str, Any]) -> bool:
        """Whether this batch is in the plan and not already gathered. Hold ``self._lock``."""
        planned = self._progress_by_batch.get(batch_id)
        if planned is None:
            self._logger.warning("BatchFinished for an unplanned batch ignored", extra=log_extra)
            return False
        if planned.state is ExecutionState.FINISHED:
            self._logger.warning("Duplicate BatchFinished ignored", extra=log_extra)
            return False
        return True

    @property
    def progress(self) -> DispatcherProgress:
        """The current aggregate snapshot, for a caller outside the message flow."""
        with self._lock:
            return DispatcherProgress(batches=tuple(self._progress_by_batch.values()), done=self._done())

    def _done(self) -> bool:
        """Whether every batch is terminal. Hold ``self._lock``."""
        return all(batch.state is ExecutionState.FINISHED for batch in self._progress_by_batch.values())

    def build_initial_update(self) -> UpdatePRComment:
        """Revision ``0``: the complete plan, before any batch has been dispatched.

        Returned rather than submitted: a processor can only submit once the bus has attached its
        queue, so the dispatcher entry point publishes this when it starts the bus.
        """
        with self._lock:
            return self.build_update_message(INITIAL_UPDATE_MESSAGE_ID, revision=0, done=False)

    def build_update_message(self, message_id: str, revision: int, done: bool) -> UpdatePRComment:
        """Build an ``UpdatePRComment`` for *revision*. Hold ``self._lock`` when state is live."""
        return UpdatePRComment(
            id=message_id,
            revision=revision,
            progress=DispatcherProgress(batches=tuple(self._progress_by_batch.values()), done=done),
        )

    @staticmethod
    def _planned_batch(batch: TestBatch) -> BatchProgress:
        """A batch as planned: known jobs, no execution, no retry budget until retries land."""
        return BatchProgress(
            batch_id=batch.batch_id,
            run_id=None,
            workflow_url=None,
            state=ExecutionState.PLANNED,
            status=None,
            current_attempt=None,
            max_attempts=1,
            retries_remaining=0,
            retrying_jobs=(),
            jobs_progress=tuple(JobProgress(job=job, attempts=()) for job in batch.job_list),
        )

    def _gather_job(
        self, batch_job_result: BatchJobResult, message: BatchFinished
    ) -> tuple[JobResult, JobAttemptProgress]:
        """Build a job's records from its correlated workflow job and its artifacts on disk.

        ``JobResult`` and ``JobAttemptProgress`` come from one pass, so reports are parsed and
        artifacts organized exactly once per job.
        """
        batch_job = batch_job_result.job
        status, failed_steps = self._job_status(batch_job_result, message)

        error: ProgressError | None = None
        reports: tuple[JUnitReport, ...] = ()
        job_artifacts_path = Path(batch_job_result.artifact_name_path) if batch_job_result.artifact_name_path else None
        if job_artifacts_path is not None:
            reports = tuple(parse_junit_dir(job_artifacts_path))
            self._organize_artifacts(job_artifacts_path, batch_job)
        else:
            error = ProgressError.NO_ARTIFACTS
            self._logger.warning(
                "No artifact directory found for job %s", batch_job.name, extra={"run_id": message.run_id}
            )

        result = JobResult(
            integration=batch_job.target,
            environment=batch_job.environment,
            platform=batch_job.platform,
            status=status,
            failed_steps=failed_steps,
            reports=reports,
        )
        job_id = conclusion = job_url = None
        if (workflow_job := batch_job_result.workflow_job) is not None:
            job_id = workflow_job.id
            conclusion = workflow_job.conclusion
            job_url = workflow_job.html_url

        attempt = JobAttemptProgress(
            # Provisional: the real position is known only when appended to the plan, under the lock.
            attempt=1,
            job_id=job_id,
            status=status,
            conclusion=conclusion,
            failed_steps=tuple(failed_steps),
            job_url=job_url,
            reports=reports,
            error=error,
        )
        return (result, attempt)

    @staticmethod
    def _job_status(batch_job_result: BatchJobResult, message: BatchFinished) -> tuple[Status, list[str]]:
        """Per-job (status, failed_steps). A timed-out batch fails every job; otherwise the job's own
        conclusion decides. A missing workflow job raises: the runner correlates every job before
        emitting, so a miss is a bug.

        ``failed_steps`` holds real step names only, so a timeout (recorded as the batch's ``error``)
        contributes none. All failing steps are collected: on-failure steps mean there can be several.
        """
        if message.timed_out:
            return (Status.FAILURE, [])

        workflow_job = batch_job_result.workflow_job
        if workflow_job is None:
            raise ValueError(f"No workflow job correlated for {batch_job_result.job.name!r}")

        failed_steps = [step.name for step in workflow_job.steps if step.conclusion == WorkflowJobConclusion.FAILURE]
        return (conclusion_to_status(workflow_job.conclusion), failed_steps)

    def _organize_artifacts(self, job_artifacts_path: Path, batch_job: BatchJob) -> None:
        """Copy coverage and JUnit files into the output tree, prefixed by the job's
        target/environment/platform — the same fields that make ``BatchJob.artifact_name`` unique.
        """
        prefix = batch_job.artifact_name()

        coverage_dir = self._output_base_path / "coverage"
        for index, coverage_file in enumerate(sorted(job_artifacts_path.rglob(COVERAGE_GLOB))):
            suffix = "" if index == 0 else f"-{index}"
            self._copy(coverage_file, coverage_dir / f"{prefix}{suffix}.xml")

        test_results_dir = self._output_base_path / "test_results"
        for junit_file in sorted(job_artifacts_path.rglob(JUNIT_GLOB)):
            self._copy(junit_file, test_results_dir / f"{prefix}-{junit_file.stem}.xml")

    def _copy(self, source: Path, destination: Path):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        self._logger.debug("Organized artifact %s -> %s", source, destination)

    def _finished_batch_progress(
        self,
        planned: BatchProgress,
        message: BatchFinished,
        gathered: list[tuple[JobResult, JobAttemptProgress]],
    ) -> BatchProgress:
        """The batch's terminal aggregate: the registered plan with this run's executions appended.

        Built from *planned*, not from the message alone, so a run reporting only a subset — what a
        failed-job rerun does — adds attempts to the jobs it covers and leaves the rest untouched.

        The batch's own status is the workflow's, not a roll-up of these jobs: a workflow also runs
        setup and finalization steps that can fail while every tracked job passes.

        Must be called while holding ``self._lock``.
        """
        attempts = {
            batch_job_result.job.name: attempt
            for batch_job_result, (_, attempt) in zip(message.batch_jobs, gathered, strict=True)
        }

        jobs = []
        for job in planned.jobs_progress:
            attempt = attempts.pop(job.job.name, None)
            if attempt is None:
                jobs.append(job)
                continue
            # Renumbered here because the position in the job's history is only known now.
            numbered = dataclasses.replace(attempt, attempt=len(job.attempts) + 1)
            jobs.append(dataclasses.replace(job, attempts=(*job.attempts, numbered)))
        for name in attempts:
            # Reported but never planned: recorded so it can be investigated, kept out of the totals.
            self._logger.warning(
                "Gathered a job that is not in the batch plan", extra={"batch_id": message.batch_id, "job": name}
            )

        attempts_run = max((len(job.attempts) for job in jobs), default=0)
        return BatchProgress(
            batch_id=message.batch_id,
            run_id=message.run_id,
            workflow_url=message.workflow_url,
            state=ExecutionState.FINISHED,
            status=message.status,
            # The batch ran, so it is on at least its first attempt.
            current_attempt=max(attempts_run, 1),
            max_attempts=1,
            retries_remaining=0,
            retrying_jobs=(),
            jobs_progress=tuple(jobs),
            error=self._batch_error(message, jobs),
        )

    @staticmethod
    def _batch_error(message: BatchFinished, jobs: list[JobProgress]) -> ProgressError | None:
        if message.timed_out:
            return ProgressError.TIMED_OUT
        if not any(job.latest is not None for job in jobs):
            return ProgressError.NO_JOB_RESULTS
        return None

    @staticmethod
    def _build_workflow_status(message: BatchFinished, results: list[JobResult]) -> WorkflowStatus:
        success_count = sum(1 for result in results if result.status == Status.SUCCESS)
        failed_count = sum(1 for result in results if result.status == Status.FAILURE)
        skipped_count = sum(1 for result in results if result.status == Status.SKIPPED)
        return WorkflowStatus(
            batch_id=message.batch_id,
            url=message.workflow_url,
            id=message.run_id,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results,
        )
