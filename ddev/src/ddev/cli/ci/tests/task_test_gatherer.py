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


class TaskTestGatherer(SyncProcessor[BatchFinished]):
    """
    Reads ``BatchFinished`` messages, analyzes the downloaded artifacts on disk, builds per-job
    ``JobResult`` records, and organizes coverage/JUnit files for later publishing.

    It is constructed with the complete batch plan, keeps an in-memory registry of every job's full
    result across all batches and, on each finished batch, emits an ``UpdatePRComment`` carrying a
    monotonically increasing ``revision`` and the whole accumulated state — as a ``DispatcherProgress``
    snapshot covering every planned batch, including those still to run. ``done`` is set once the final
    expected batch has been received. It does not post to GitHub — rendering the comment (and rejecting
    stale revisions) is a separate consumer's job.

    This task makes no GitHub API calls — it works exclusively from the artifacts the runner
    already downloaded to ``BatchFinished.artifacts_path``.
    """

    def __init__(self, name: str, output_base_path: Path, batches: list[TestBatch]) -> None:
        super().__init__(name)
        self._output_base_path = output_base_path
        self._expected_batches = len(batches)
        self._received_batches = 0
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
            self._logger.warning("BatchFinished carried no jobs; nothing to gather", extra=log_extra)
            # No revision is emitted, but the batch is terminal: it must not keep rendering as planned.
            with self._lock:
                self._finish_without_jobs(message)
            return

        # Parse and organize artifacts outside the lock — these touch only this batch's own files.
        gathered = [self._gather_job(batch_job_result, message) for batch_job_result in message.batch_jobs]
        results = [result for result, _ in gathered]
        status = self._build_workflow_status(message, results)
        progress = self._finished_batch_progress(message, gathered)

        # Register the batch, bump the revision, and emit the update all under the lock so two batches
        # finishing at once cannot build a comment from half-updated shared state.
        with self._lock:
            if message.batch_id not in self._progress_by_batch:
                self._logger.warning("BatchFinished for an unplanned batch ignored", extra=log_extra)
                return
            # Keyed by batch id (stable across retries; run_id changes on a re-run). A duplicate is
            # ignored so it can't re-count the batch and inflate the revision — this check is
            # authoritative only inside the lock. (Retry-replace semantics come with the retry work.)
            if message.id in self._results_by_batch:
                self._logger.warning("Duplicate BatchFinished ignored", extra=log_extra)
                return
            self._results_by_batch[message.id] = results
            self._status_by_batch[message.id] = status
            self._progress_by_batch[message.batch_id] = progress
            self._received_batches += 1
            revision = self._received_batches
            done = revision >= self._expected_batches
            self.submit_message(self.build_update_message(message.id, revision, done))

        self._logger.info(
            "Batch gathered, UpdatePRComment revision %s emitted (done=%s)",
            revision,
            done,
            extra=log_extra,
        )

    def build_initial_update(self) -> UpdatePRComment:
        """Revision ``0``: the complete plan, before any batch has been dispatched.

        Follows the same event-bus path as every later revision, so the PR updater needs no separate
        startup call.
        """
        with self._lock:
            return self.build_update_message("initial", revision=0, done=False)

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

        error: str | None = None
        reports: tuple[JUnitReport, ...] = ()
        job_artifacts_path = Path(batch_job_result.artifact_name_path) if batch_job_result.artifact_name_path else None
        if job_artifacts_path is not None:
            reports = tuple(parse_junit_dir(job_artifacts_path))
            self._organize_artifacts(job_artifacts_path, batch_job)
        else:
            error = f"No artifact directory found for job {batch_job.name!r}"
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
            # One attempt per job until the retry work lands; the runner reports no attempt number yet.
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

        All steps concluding in failure are collected: a workflow can run on-failure steps, so more than
        one step may fail for a single job.
        """
        if message.timed_out:
            return (Status.FAILURE, ["timed out"])

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

    def _finish_without_jobs(self, message: BatchFinished) -> None:
        """Mark a batch that reported no job results terminal, with the reason recorded.

        Must be called while holding ``self._lock``. No revision is emitted: nothing was gathered.
        """
        planned = self._progress_by_batch.get(message.batch_id)
        if planned is None:
            return
        self._progress_by_batch[message.batch_id] = dataclasses.replace(
            planned,
            run_id=message.run_id,
            workflow_url=message.workflow_url,
            state=ExecutionState.FINISHED,
            status=Status.FAILURE,
            current_attempt=1,
            error="Batch reported no job results",
        )

    def _finished_batch_progress(
        self, message: BatchFinished, gathered: list[tuple[JobResult, JobAttemptProgress]]
    ) -> BatchProgress:
        """The batch's terminal aggregate, built from the executions reported on the message.

        The batch label follows the same precedence as ``WorkflowStatus.status``: failed if any job
        failed, else passed if any job passed, else skipped.
        """
        jobs = tuple(
            JobProgress(job=batch_job_result.job, attempts=(attempt,))
            for batch_job_result, (_, attempt) in zip(message.batch_jobs, gathered, strict=True)
        )
        statuses = {job.latest.status for job in jobs if job.latest is not None}
        if Status.FAILURE in statuses:
            status = Status.FAILURE
        elif Status.SUCCESS in statuses:
            status = Status.SUCCESS
        else:
            status = Status.SKIPPED

        return BatchProgress(
            batch_id=message.batch_id,
            run_id=message.run_id,
            workflow_url=message.workflow_url,
            state=ExecutionState.FINISHED,
            status=status,
            current_attempt=1,
            max_attempts=1,
            retries_remaining=0,
            retrying_jobs=(),
            jobs=jobs,
            error="Batch timed out" if message.timed_out else None,
        )

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
