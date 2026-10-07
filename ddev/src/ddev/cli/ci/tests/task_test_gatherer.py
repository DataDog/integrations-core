# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import dataclasses
import shutil
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.dispatcher_attributes import job_fields
from ddev.cli.ci.tests.execution_metrics import (
    MetricsHelper,
    Operation,
    ResultMetric,
    report_result,
    result_metric,
)
from ddev.cli.ci.tests.messages import (
    BatchFinished,
    BatchJob,
    BatchJobResult,
    BatchProgressUpdate,
    JobResult,
    UpdatePRComment,
)
from ddev.cli.ci.tests.progress import (
    BatchProgress,
    DispatcherProgress,
    ExecutionState,
    JobAttemptProgress,
    JobProgress,
    ProgressError,
)
from ddev.cli.ci.tests.status import Status, job_status, timed_out
from ddev.event_bus.orchestrator import SyncProcessor
from ddev.monitoring import ComponentMonitor
from ddev.utils.github_async.models.workflow import WorkflowJobStatus
from ddev.utils.junit import TestStatus, parse_junit_dir

if TYPE_CHECKING:
    from ddev.cli.ci.tests.messages import TestBatch
    from ddev.utils.github_async.models import WorkflowJob
    from ddev.utils.junit import JUnitReport

# Expected layout of the extracted `test-result.zip` tree (defined by `test-batch.yaml`):
#   {artifacts_path}/
#     {artifact_name}/                one directory per job (its BatchJobResult.artifact_name_path)
#       coverage.xml                  Cobertura coverage report
#       test-{unit|e2e}-{env}.xml     pytest JUnit report(s)
# Each job's spec, workflow-job result, and artifact directory come pre-correlated on the message
# (BatchFinished.batch_jobs). Each job's status is its own workflow-job conclusion. A job whose
# final state was never confirmed (no workflow job, or one last seen before it completed) is
# resolved from the run's conclusion and the job's artifacts: the final jobs listing can lag or
# fail after the run itself has finished.
COVERAGE_GLOB = "coverage*.xml"
JUNIT_GLOB = "test-*.xml"
# Every later update borrows the id of the message that changed progress. Revision `0` has no
# cause, so it carries its own.
INITIAL_UPDATE_MESSAGE_ID = "dispatcher-initial"


def _has_failed_tests(reports: tuple[JUnitReport, ...]) -> bool:
    """Whether any of the job's parsed reports holds a failed or errored test case."""
    return any(
        case.status in (TestStatus.FAILED, TestStatus.ERROR)
        for report in reports
        for suite in report.test_suites
        for case in suite.test_cases
    )


def _job_result(result: JobResult, attempt: JobAttemptProgress) -> ResultMetric:
    """A finished attempt's metric result: a timeout is split from its failure status."""
    return result_metric(result.status, timed_out=attempt.timed_out)


def _batch_result(message: BatchFinished, gathered: list[tuple[JobResult, JobAttemptProgress]]) -> ResultMetric:
    """A cancelled batch is cancelled whatever its finished jobs did. Otherwise a job failure outranks
    a job timeout, which outranks the workflow's own status.
    """
    if message.status is Status.CANCELLED:
        return ResultMetric.CANCELLED
    results = [_job_result(result, attempt) for result, attempt in gathered]
    if ResultMetric.FAILED in results:
        return ResultMetric.FAILED
    if ResultMetric.TIMED_OUT in results:
        return ResultMetric.TIMED_OUT
    return result_metric(message.status)


class TaskTestGatherer(SyncProcessor[BatchFinished | BatchProgressUpdate]):
    """Publishes changed execution snapshots and enriches them with gathered coverage and JUnit results.

    Registries are keyed by `batch_id`: it is stable across workflow attempts, `run_id` is not.
    """

    def __init__(
        self,
        name: str,
        output_base_path: Path,
        batches: list[TestBatch],
        *,
        monitor: ComponentMonitor,
    ) -> None:
        super().__init__(name)
        self._output_base_path = output_base_path
        self._revision = 0
        self._sequences: dict[str, int] = {}
        # The whole plan, in planning order, so each snapshot covers batches that have not run yet.
        self._progress_by_batch: dict[str, BatchProgress] = {
            batch.batch_id: self._planned_batch(batch) for batch in batches
        }
        # Outcome counters already emitted, under `self._lock`. One per planned job, so each job's
        # outcomes add up to its `jobs.count`.
        self._reported_batches: set[str] = set()
        self._reported_jobs: dict[str, set[str]] = {}
        self._lock = threading.Lock()
        self._logger = monitor.logger
        self.monitor = monitor
        self._metrics = MetricsHelper(monitor.metrics)

    def process_message(self, message: BatchFinished | BatchProgressUpdate) -> None:
        if isinstance(message, BatchProgressUpdate):
            self._observe_progress(message)
            return

        if not message.batch_jobs:
            # Still terminal and still worth a revision, or it renders as planned forever.
            self._logger.warning("Batch %s finished with no jobs to gather", message.batch_id)

        # Rejected before gathering: gathering writes into the shared output tree, where a batch that
        # is not in the plan could overwrite the files another batch publishes.
        with self._lock:
            if not self._accepts(message.batch_id):
                return

        self._logger.info(
            "Gathering results for batch %s (jobs=%s)",
            message.batch_id,
            len(message.batch_jobs),
            batch_job_count=len(message.batch_jobs),
        )
        try:
            gathered = self._gather_results(message)
            published = gathered is not None and self._publish_results(message, gathered)
        except Exception:
            self._metrics.record_operation(Operation.GATHER_BATCH_RESULTS, failed=True)
            self._metrics.log_failed_operation(
                Operation.GATHER_BATCH_RESULTS,
                self._logger,
                "Failed to gather results for batch %s",
                message.batch_id,
                exc_info=True,
            )
            raise
        if published:
            self._metrics.record_operation(Operation.GATHER_BATCH_RESULTS, failed=False)

    def _gather_results(
        self,
        message: BatchFinished,
    ) -> list[tuple[JobResult, JobAttemptProgress]] | None:
        gathered: list[tuple[JobResult, JobAttemptProgress]] = []
        for batch_job_result in message.batch_jobs:
            # Cancellation cannot interrupt this thread; leave the batch unfinished instead.
            if self.stopping:
                self._logger.warning(
                    "Gathering abandoned after %s of %s jobs: the bus is shutting down",
                    len(gathered),
                    len(message.batch_jobs),
                )
                return None
            gathered.append(self._gather_job(batch_job_result, message))
        return gathered

    def _publish_results(
        self,
        message: BatchFinished,
        gathered: list[tuple[JobResult, JobAttemptProgress]],
    ) -> bool:
        """Commit gathered results; return whether the batch was actually registered."""
        with self._lock:
            # Cancellation or another collector may have won while these results were parsed.
            if self.stopping:
                self._logger.warning("Batch gathered but left unregistered: the bus is shutting down")
                return False
            if not self._accepts(message.batch_id):
                return False
            planned = self._progress_by_batch[message.batch_id]
            finished = self._finished_batch_progress(planned, message, gathered)
            self._progress_by_batch[message.batch_id] = finished
            update = self._publish_update(message.id)
            self._report_final_result(message, gathered)

        self._logger.info(
            "Batch %s results gathered: report revision %s (done=%s)",
            message.batch_id,
            update.revision,
            update.progress.done,
        )
        return True

    def _report_final_result(
        self, message: BatchFinished, gathered: list[tuple[JobResult, JobAttemptProgress]]
    ) -> None:
        """Count the batch's and its jobs' outcomes. A job already counted at observation is skipped.

        Hold `self._lock`.
        """
        for batch_job_result, (result, attempt) in zip(message.batch_jobs, gathered, strict=True):
            self._report_job_once(message.batch_id, batch_job_result.job, _job_result(result, attempt))
        report_result(self.monitor.metrics, 'batches', _batch_result(message, gathered))
        self._reported_batches.add(message.batch_id)

    def _report_job_once(self, batch_id: str, job: BatchJob, result: ResultMetric) -> None:
        """Count a planned job's outcome once, whichever account reaches it first. Hold `self._lock`."""
        reported = self._reported_jobs.setdefault(batch_id, set())
        if job.name in reported:
            return
        report_result(self.monitor.metrics, 'jobs', result, **job_fields(job))
        reported.add(job.name)

    def _observe_progress(self, message: BatchProgressUpdate) -> None:
        with self._lock:
            if self.stopping or not self._accepts(message.batch_id):
                return
            current = self._progress_by_batch[message.batch_id]
            if not self._accept_progress(current, message):
                return

            previous = self._snapshot()
            self._progress_by_batch[message.batch_id] = self._updated_batch_progress(current, message)
            self._report_observed_results(message.batch_id)
            # Repeated polls should not trigger identical PR comment updates.
            if self._snapshot() != previous:
                self._publish_update(message.id)

    def _report_observed_results(self, batch_id: str) -> None:
        """Count each job at the first observation showing it finished. Hold `self._lock`."""
        for job in self._progress_by_batch[batch_id].jobs_progress:
            latest = job.latest
            if latest is None or latest.state is not ExecutionState.FINISHED or latest.status is None:
                continue
            self._report_job_once(batch_id, job.job, result_metric(latest.status, timed_out=latest.timed_out))

    def _accept_progress(self, current: BatchProgress, message: BatchProgressUpdate) -> bool:
        """Called with the gatherer lock held."""
        # Otherwise the report could show one workflow run's results under another run's link.
        if current.run_id is not None and current.run_id != message.run_id:
            return False

        # Messages can be processed out of order, so an older update must not replace a newer one.
        if message.sequence <= self._sequences.get(message.batch_id, -1):
            return False

        # Remember this message even if its state goes backward, so older updates cannot be applied later.
        self._sequences[message.batch_id] = message.sequence

        # The workflow has finished, but the batch must keep showing collection until its results are ready.
        if current.state is ExecutionState.ARTIFACT_DOWNLOAD and message.state is not current.state:
            return False

        # Once a batch has started, a queued update must not make it look like it is waiting to start.
        return not (current.state is ExecutionState.RUNNING and message.state is ExecutionState.QUEUED)

    def _updated_batch_progress(self, current: BatchProgress, message: BatchProgressUpdate) -> BatchProgress:
        observed = {job.name: job for job in message.jobs}
        jobs = []
        # Count only the planned tests, not the workflow's setup or reporting jobs.
        for job in current.jobs_progress:
            workflow_job = observed.get(job.job.name)
            jobs.append(self._observe_job(job, workflow_job) if workflow_job is not None else job)
        return dataclasses.replace(
            current,
            run_id=message.run_id,
            workflow_url=message.workflow_url,
            state=message.state,
            status=message.status if message.status is not None else current.status,
            current_attempt=max((job.latest.attempt for job in jobs if job.latest is not None), default=1),
            jobs_progress=tuple(jobs),
        )

    def _observe_job(self, job: JobProgress, workflow_job: WorkflowJob) -> JobProgress:
        if workflow_job.status is WorkflowJobStatus.COMPLETED:
            state = ExecutionState.FINISHED
        elif workflow_job.status is WorkflowJobStatus.IN_PROGRESS:
            state = ExecutionState.RUNNING
        else:
            state = ExecutionState.QUEUED
        latest = job.latest
        # Reruns get new job IDs, so a job with a new ID is allowed to start from queued again.
        if latest is not None and latest.job_id == workflow_job.id:
            if latest.state is ExecutionState.FINISHED and state is not ExecutionState.FINISHED:
                return job
            if latest.state is ExecutionState.RUNNING and state is ExecutionState.QUEUED:
                return job
        finished = state is ExecutionState.FINISHED
        status = job_status(workflow_job) if finished else None
        attempt = JobAttemptProgress(
            attempt=1,
            job_id=workflow_job.id,
            state=state,
            status=status,
            conclusion=workflow_job.conclusion if finished else None,
            failed_steps=tuple(step.name for step in workflow_job.steps if finished and step.conclusion == "failure"),
            job_url=workflow_job.html_url,
            reports=None,
            timed_out=timed_out(workflow_job),
        )
        return self._record_attempt(job, attempt, same_run=True)

    def _publish_update(self, message_id: str) -> UpdatePRComment:
        """Advance the revision and publish its snapshot under the aggregate lock."""
        self._revision += 1
        update = self.build_update_message(message_id, self._revision, self._done())
        self.submit_message(update)
        return update

    @staticmethod
    def _record_attempt(job: JobProgress, attempt: JobAttemptProgress, *, same_run: bool) -> JobProgress:
        latest = job.latest
        # Collecting results belongs to the same job attempt, even if a timeout left us without its job ID.
        if latest is not None and same_run and (attempt.job_id is None or latest.job_id == attempt.job_id):
            # If this update has no collected results yet, keep any reports and errors we already have.
            updated = dataclasses.replace(
                attempt,
                attempt=latest.attempt,
                job_id=attempt.job_id if attempt.job_id is not None else latest.job_id,
                job_url=attempt.job_url if attempt.job_url is not None else latest.job_url,
                reports=attempt.reports if attempt.reports is not None else latest.reports,
                error=attempt.error if attempt.reports is not None else latest.error,
            )
            return dataclasses.replace(job, attempts=(*job.attempts[:-1], updated))
        numbered = dataclasses.replace(attempt, attempt=len(job.attempts) + 1)
        return dataclasses.replace(job, attempts=(*job.attempts, numbered))

    def _accepts(self, batch_id: str) -> bool:
        """Whether this batch is in the plan and not already gathered. Hold `self._lock`."""
        planned = self._progress_by_batch.get(batch_id)
        if planned is None:
            self._logger.warning("Update for an unplanned batch ignored")
            return False
        if planned.state is ExecutionState.FINISHED:
            self._logger.debug("Update for a gathered batch ignored")
            return False
        return True

    @property
    def progress(self) -> DispatcherProgress:
        """The current aggregate snapshot, for a caller outside the message flow."""
        with self._lock:
            return self._snapshot()

    def report_unfinished(self, dispatched: Iterable[TestBatch], *, cancelled: bool) -> None:
        """Account for dispatched work that has no outcome yet, without raising into shutdown.

        A cancelled shutdown counts it as cancelled; any other flags its jobs incomplete. The caller
        passes the dispatched batches because a shutdown race can drop the dispatch's progress update.
        """
        try:
            with self._lock:
                metrics = self.monitor.metrics
                for batch in dispatched:
                    reported = self._reported_jobs.get(batch.batch_id, set())
                    if cancelled:
                        if batch.batch_id not in self._reported_batches:
                            report_result(metrics, 'batches', ResultMetric.CANCELLED)
                        for job in batch.job_list:
                            self._report_job_once(batch.batch_id, job, ResultMetric.CANCELLED)
                    else:
                        for job in batch.job_list:
                            metrics.count('jobs.incomplete', int(job.name not in reported), **job_fields(job))
        except Exception:
            self._logger.exception("Failed to report unfinished work")

    def _snapshot(self, done: bool | None = None) -> DispatcherProgress:
        """Build the reconciled aggregate while holding the lock, deriving *done* unless supplied."""
        return DispatcherProgress(
            batches=tuple(self._progress_by_batch.values()),
            done=self._done() if done is None else done,
        ).reconciled()

    def _done(self) -> bool:
        """Whether every batch is terminal. Hold `self._lock`."""
        return all(batch.state is ExecutionState.FINISHED for batch in self._progress_by_batch.values())

    def build_initial_update(self) -> UpdatePRComment:
        """Revision `0`: the complete plan, before any batch has been dispatched.

        Returned rather than submitted: a processor can only submit once the bus has attached its
        queue, so the dispatcher entry point publishes this when it starts the bus.
        """
        with self._lock:
            return self.build_update_message(INITIAL_UPDATE_MESSAGE_ID, revision=0, done=False)

    def build_update_message(self, message_id: str, revision: int, done: bool) -> UpdatePRComment:
        """Build an `UpdatePRComment` for *revision*. Hold `self._lock` when state is live."""
        return UpdatePRComment(
            id=message_id,
            revision=revision,
            progress=self._snapshot(done),
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

        `JobResult` and `JobAttemptProgress` come from one pass, so reports are parsed and
        artifacts organized exactly once per job.
        """
        batch_job = batch_job_result.job
        reports, error = self._gather_reports(batch_job_result)
        status, failed_steps = self._job_status(batch_job_result, message, reports)

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
            # The execution's position is resolved under the aggregate lock.
            attempt=1,
            job_id=job_id,
            status=status,
            conclusion=conclusion,
            failed_steps=tuple(failed_steps),
            job_url=job_url,
            reports=reports,
            error=error,
            timed_out=workflow_job is not None and timed_out(workflow_job),
        )
        return (result, attempt)

    def _gather_reports(self, batch_job_result: BatchJobResult) -> tuple[tuple[JUnitReport, ...], ProgressError | None]:
        if not batch_job_result.artifact_name_path:
            self._logger.warning("No artifact directory found for job", job=batch_job_result.job.name)
            return (), ProgressError.NO_ARTIFACTS
        path = Path(batch_job_result.artifact_name_path)
        reports = tuple(parse_junit_dir(path))
        self._organize_artifacts(path, batch_job_result.job)
        return reports, None

    def _job_status(
        self, batch_job_result: BatchJobResult, message: BatchFinished, reports: tuple[JUnitReport, ...]
    ) -> tuple[Status, list[str]]:
        """Per-job (status, failed_steps).

        A job whose workflow job completed reports its own conclusion. `_unconfirmed_job_status`
        decides any other job: its workflow job is missing or was last seen before it completed,
        because the final jobs listing can lag or fail after the run has finished.

        `failed_steps` holds real step names only. All failing steps are collected: on-failure steps
        mean there can be several.
        """
        workflow_job = batch_job_result.workflow_job
        if workflow_job is not None and workflow_job.status is WorkflowJobStatus.COMPLETED:
            failed_steps = [step.name for step in workflow_job.steps if step.conclusion == "failure"]
            return (job_status(workflow_job), failed_steps)

        return (self._unconfirmed_job_status(batch_job_result, message, reports), [])

    def _unconfirmed_job_status(
        self, batch_job_result: BatchJobResult, message: BatchFinished, reports: tuple[JUnitReport, ...]
    ) -> Status:
        """Decide the status of a job whose final state was never confirmed, once the run is over.

        GitHub concludes a run `success` only when no job failed, so a successful run clears an
        unconfirmed job. Otherwise the artifacts are the remaining evidence: failed or errored
        tests mean the job failed, and anything else is inconclusive, because the job may have failed
        outside its tests (e.g. in setup) or never produced reports. A cancelled run is checked
        first: whatever it left unfinished is discarded, failing reports included.
        """
        if message.status is Status.SUCCESS:
            status, reason = Status.SUCCESS, "the workflow run succeeded"
        elif message.status is Status.CANCELLED:
            status, reason = Status.CANCELLED, "the workflow run was cancelled"
        elif _has_failed_tests(reports):
            status, reason = Status.FAILURE, "its artifacts hold failed tests"
        else:
            status, reason = Status.INCONCLUSIVE, "the run did not succeed and no test failed"
        # Inferred, not observed: no listing ever showed this attempt's own finish.
        self._logger.warning(
            "Job %s has no confirmed final state: reported as %s (%s)",
            batch_job_result.job.name,
            status.value,
            reason,
            **job_fields(batch_job_result.job),
            job_status=status.value,
        )
        return status

    def _organize_artifacts(self, job_artifacts_path: Path, batch_job: BatchJob) -> None:
        """Copy coverage and JUnit files into the output tree, prefixed by the job's
        target/environment/platform, the same fields that make `BatchJob.artifact_name` unique.
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
        """Merge collected results into this run's observed executions.

        A different run adds attempts only to the jobs it covers, preserving sparse rerun histories.

        The batch's own status is the workflow's, not a roll-up of these jobs: a workflow also runs
        setup and finalization steps that can fail while every tracked job passes.

        Must be called while holding `self._lock`.
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
            jobs.append(self._record_attempt(job, attempt, same_run=planned.run_id == message.run_id))
        for name in attempts:
            # Reported but never planned: recorded so it can be investigated, kept out of the totals.
            self._logger.warning("Gathered a job that is not in the batch plan", job=name)

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
        # Seeing a job finish does not mean we have collected its results.
        if not any(job.latest is not None and job.latest.reports is not None for job in jobs):
            return ProgressError.NO_JOB_RESULTS
        return None
