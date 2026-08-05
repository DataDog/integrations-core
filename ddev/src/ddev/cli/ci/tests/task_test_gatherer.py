# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import logging
import shutil
import threading
from pathlib import Path
from typing import TYPE_CHECKING

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
from ddev.cli.ci.tests.status import Status, batch_status, conclusion_to_status
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


class TaskTestGatherer(SyncProcessor[BatchFinished]):
    """
    Reads ``BatchFinished`` messages, analyzes the downloaded artifacts on disk, builds per-job
    ``JobResult`` records, and organizes coverage/JUnit files for later publishing.

    It is constructed with the complete batch plan, keeps an in-memory registry of every job's full
    result across all batches and, on each finished batch, emits an ``UpdatePRComment`` carrying a
    monotonically increasing ``revision`` and the whole accumulated state — as a ``DispatcherProgress``
    snapshot covering every planned batch, including those still to run. ``done`` is derived from that
    snapshot: it is set once no planned batch is left unfinished. It does not post to GitHub —
    rendering the comment (and rejecting stale revisions) is a separate consumer's job.

    Every registry is keyed by ``batch_id``, the batch's logical identity, which stays stable across
    workflow attempts while ``run_id`` and the message id do not.

    This task makes no GitHub API calls — it works exclusively from the artifacts the runner
    already downloaded to ``BatchFinished.artifacts_path``.
    """

    def __init__(self, name: str, output_base_path: Path, batches: list[TestBatch]) -> None:
        super().__init__(name)
        self._output_base_path = output_base_path
        self._revision = 0
        self._status_by_batch: dict[str, WorkflowStatus] = {}
        self._results_by_batch: dict[str, list[JobResult]] = {}
        # The whole plan, in planning order: every batch is present from the start so each snapshot
        # covers batches that have not run yet, not only the ones already gathered.
        self._progress_by_batch: dict[str, BatchProgress] = {
            batch.batch_id: self._planned_batch(batch) for batch in batches
        }
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def process_message(self, message: BatchFinished) -> None:
        log_extra = {"batch_id": message.batch_id, "run_id": message.run_id}
        if not message.batch_jobs:
            # Still terminal, and still worth a revision: the batch has stopped and the comment must
            # say so, otherwise it renders as planned forever and ``done`` is never reached.
            self._logger.warning("BatchFinished carried no jobs; nothing to gather", extra=log_extra)

        # Parse and organize artifacts outside the lock — these touch only this batch's own files.
        gathered = [self._gather_job(batch_job_result, message) for batch_job_result in message.batch_jobs]
        results = [result for result, _ in gathered]
        status = self._build_workflow_status(message, results)

        # Register the batch, bump the revision, and emit the update all under the lock so two batches
        # finishing at once cannot build a comment from half-updated shared state.
        with self._lock:
            planned = self._progress_by_batch.get(message.batch_id)
            if planned is None:
                self._logger.warning("BatchFinished for an unplanned batch ignored", extra=log_extra)
                return
            # The aggregate is the single record of what has been gathered, so a batch already in a
            # terminal state is a duplicate. Ignoring it keeps it from inflating the revision — the
            # check is authoritative only inside the lock. (Retry semantics come with the retry work.)
            if planned.state is ExecutionState.FINISHED:
                self._logger.warning("Duplicate BatchFinished ignored", extra=log_extra)
                return
            if results:
                # The flat view counts job outcomes, so a run that reported none has no entry there;
                # the aggregate is where a batch that finished empty is recorded as failed.
                self._results_by_batch[message.batch_id] = results
                self._status_by_batch[message.batch_id] = status
            self._progress_by_batch[message.batch_id] = self._finished_batch_progress(planned, message, gathered)
            self._revision += 1
            revision = self._revision
            done = all(batch.state is ExecutionState.FINISHED for batch in self._progress_by_batch.values())
            self.submit_message(self.build_update_message(message.id, revision, done))

        self._logger.info(
            "Batch gathered, UpdatePRComment revision %s emitted (done=%s)",
            revision,
            done,
            extra=log_extra,
        )

    def build_initial_update(self, message_id: str) -> UpdatePRComment:
        """Revision ``0``: the complete plan, before any batch has been dispatched.

        Returned rather than submitted, because a processor can only submit once the event bus has
        attached its queue. The dispatcher entry point publishes it when it starts the bus, so the
        PR updater receives the plan on the same channel as every later revision.
        """
        with self._lock:
            return self.build_update_message(message_id, revision=0, done=False)

    def build_update_message(self, message_id: str, revision: int, done: bool) -> UpdatePRComment:
        """Build an ``UpdatePRComment`` for *revision* from all accumulated results.

        Must be called while holding ``self._lock`` when reading live shared state.
        """
        return UpdatePRComment(
            id=message_id,
            revision=revision,
            done=done,
            workflows=list(self._status_by_batch.values()),
            progress=DispatcherProgress(batches=tuple(self._progress_by_batch.values()), done=done),
        )

    @staticmethod
    def _planned_batch(batch: TestBatch) -> BatchProgress:
        """A batch as planned: known jobs, no execution yet, and no retry budget until retries land."""
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
            jobs=tuple(JobProgress(job=job, attempts=()) for job in batch.job_list),
        )

    def _gather_job(
        self, batch_job_result: BatchJobResult, message: BatchFinished
    ) -> tuple[JobResult, JobAttemptProgress]:
        """Build a job's records from its correlated workflow job and its artifacts on disk.

        Both the flat ``JobResult`` and the aggregate's ``JobAttemptProgress`` come from this single
        pass, so reports are parsed and artifacts organized exactly once per job.
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
        workflow_job = batch_job_result.workflow_job
        attempt = JobAttemptProgress(
            # Provisional: the job's real position in its history is only known once the attempt is
            # appended to the registered plan, under the lock.
            attempt=1,
            job_id=None if workflow_job is None else workflow_job.id,
            status=status,
            conclusion=None if workflow_job is None else workflow_job.conclusion,
            failed_steps=tuple(failed_steps),
            job_url=None if workflow_job is None else workflow_job.html_url,
            reports=reports,
            error=error,
        )
        return (result, attempt)

    @staticmethod
    def _job_status(batch_job_result: BatchJobResult, message: BatchFinished) -> tuple[Status, list[str]]:
        """Per-job (status, failed_steps). Deterministic: timed-out batches fail every job; otherwise the
        job's own workflow-job conclusion decides. A missing workflow job is unexpected and raises — the
        runner correlates every job before emitting, so a miss is a bug, not a state to paper over.

        ``failed_steps`` holds real step names only. A timed-out batch has none — the timeout is not a
        step, and is recorded as the batch's ``error`` instead. All steps concluding in failure are
        collected: a workflow can run on-failure steps, so more than one step may fail for a job.
        """
        if message.timed_out:
            return (Status.FAILURE, [])

        workflow_job = batch_job_result.workflow_job
        if workflow_job is None:
            raise ValueError(f"No workflow job correlated for {batch_job_result.job.name!r}")

        failed_steps = [step.name for step in workflow_job.steps if step.conclusion == WorkflowJobConclusion.FAILURE]
        return (conclusion_to_status(workflow_job.conclusion), failed_steps)

    def _organize_artifacts(self, job_artifacts_path: Path, batch_job: BatchJob) -> None:
        """Copy coverage and JUnit files into the organized output tree with unique names.

        The prefix is the job's target/environment/platform — the same fields as
        ``BatchJob.artifact_name`` and the uniqueness key for a job within a batch.
        """
        prefix = f"{batch_job.target}-{batch_job.environment}-{batch_job.platform}"

        coverage_dir = self._output_base_path / "coverage"
        for index, coverage_file in enumerate(sorted(job_artifacts_path.rglob(COVERAGE_GLOB))):
            suffix = "" if index == 0 else f"-{index}"
            self._copy(coverage_file, coverage_dir / f"{prefix}{suffix}.xml")

        test_results_dir = self._output_base_path / "test_results"
        for junit_file in sorted(job_artifacts_path.rglob(JUNIT_GLOB)):
            self._copy(junit_file, test_results_dir / f"{prefix}-{junit_file.stem}.xml")

    def _copy(self, source: Path, destination: Path) -> None:
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

        Built from *planned* rather than from the message alone, so the batch keeps every job it was
        planned with. A run that reports only a subset — which is what a failed-job rerun does — adds
        attempts to the jobs it covers and leaves the rest as they were, instead of dropping them.

        Must be called while holding ``self._lock``: it reads a registered ``BatchProgress``.
        """
        reported_jobs = {batch_job_result.job.name: batch_job_result.job for batch_job_result in message.batch_jobs}
        attempts = {
            batch_job_result.job.name: attempt
            for batch_job_result, (_, attempt) in zip(message.batch_jobs, gathered, strict=True)
        }

        jobs = []
        for job in planned.jobs:
            attempt = attempts.pop(job.job.name, None)
            if attempt is None:
                jobs.append(job)
                continue
            # The attempt number is the execution's position in this job's own history.
            numbered = dataclasses.replace(attempt, attempt=len(job.attempts) + 1)
            jobs.append(dataclasses.replace(job, attempts=(*job.attempts, numbered)))
        for name, attempt in attempts.items():
            # A job the plan never mentioned is a runner bug, but dropping its result would hide it.
            self._logger.warning(
                "Gathered a job that is not in the batch plan", extra={"batch_id": message.batch_id, "job": name}
            )
            jobs.append(JobProgress(job=reported_jobs[name], attempts=(attempt,)))

        statuses = [job.latest.status for job in jobs if job.latest is not None]
        attempts_run = max((len(job.attempts) for job in jobs), default=0)

        return BatchProgress(
            batch_id=message.batch_id,
            run_id=message.run_id,
            workflow_url=message.workflow_url,
            state=ExecutionState.FINISHED,
            # A batch that ran but reported nothing has no job status to collapse, and failed.
            status=batch_status(statuses) if statuses else Status.FAILURE,
            # The batch ran, so it is on at least its first attempt even if no job reported one.
            current_attempt=max(attempts_run, 1),
            max_attempts=1,
            retries_remaining=0,
            retrying_jobs=(),
            jobs=tuple(jobs),
            error=self._batch_error(message, statuses),
        )

    @staticmethod
    def _batch_error(message: BatchFinished, statuses: list[Status]) -> ProgressError | None:
        if message.timed_out:
            return ProgressError.TIMED_OUT
        if not statuses:
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
