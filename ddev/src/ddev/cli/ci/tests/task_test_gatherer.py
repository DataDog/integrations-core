# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

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
from ddev.cli.ci.tests.status import Status, conclusion_to_status
from ddev.event_bus.orchestrator import SyncProcessor
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.junit import parse_junit_dir

if TYPE_CHECKING:
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

    It keeps an in-memory registry of every job's full result across all batches and, on each finished
    batch, emits an ``UpdatePRComment`` carrying a monotonically increasing ``revision`` and the whole
    accumulated state. ``done`` is set once the final expected batch has been received. It does not post
    to GitHub — rendering the comment (and rejecting stale revisions) is a separate consumer's job.

    This task makes no GitHub API calls — it works exclusively from the artifacts the runner
    already downloaded to ``BatchFinished.artifacts_path``.
    """

    def __init__(self, name: str, output_base_path: Path, expected_batches: int) -> None:
        super().__init__(name)
        self._output_base_path = output_base_path
        self._expected_batches = expected_batches
        self._received_batches = 0
        self._status_by_batch: dict[str, WorkflowStatus] = {}
        self._results_by_batch: dict[str, list[JobResult]] = {}
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def process_message(self, message: BatchFinished) -> None:
        if not message.batch_jobs:
            self._logger.warning("BatchFinished carried no jobs; nothing to gather", extra={"run_id": message.run_id})
            return

        # Parse and organize artifacts outside the lock — these touch only this batch's own files.
        results = [self._job_result(batch_job_result, message) for batch_job_result in message.batch_jobs]
        status = self._build_workflow_status(message, results)

        # Register the batch, bump the revision, and emit the update all under the lock so two batches
        # finishing at once cannot build a comment from half-updated shared state.
        with self._lock:
            # Keyed by batch id (stable across retries; run_id changes on a re-run). A duplicate is
            # ignored so it can't re-count the batch and inflate the revision — this check is
            # authoritative only inside the lock. (Retry-replace semantics come with the retry work.)
            if message.id in self._results_by_batch:
                self._logger.warning(
                    "Duplicate BatchFinished ignored", extra={"batch_id": message.id, "run_id": message.run_id}
                )
                return
            self._results_by_batch[message.id] = results
            self._status_by_batch[message.id] = status
            self._received_batches += 1
            revision = self._received_batches
            done = revision >= self._expected_batches
            self.submit_message(self.build_update_message(message.id, revision, done))

        self._logger.info(
            "Batch gathered, UpdatePRComment revision %s emitted (done=%s)",
            revision,
            done,
            extra={"run_id": message.run_id},
        )

    def build_update_message(self, message_id: str, revision: int, done: bool) -> UpdatePRComment:
        """Build an ``UpdatePRComment`` for *revision* from all accumulated results.

        Must be called while holding ``self._lock`` when reading live shared state.
        """
        return UpdatePRComment(
            id=message_id, revision=revision, done=done, workflows=list(self._status_by_batch.values())
        )

    def _job_result(self, batch_job_result: BatchJobResult, message: BatchFinished) -> JobResult:
        """Build a job's ``JobResult`` from its correlated workflow job and artifacts on disk."""
        batch_job = batch_job_result.job
        status, failed_steps = self._job_status(batch_job_result, message)

        reports: tuple[JUnitReport, ...] = ()
        job_artifacts_path = Path(batch_job_result.artifact_name_path) if batch_job_result.artifact_name_path else None
        if job_artifacts_path is not None:
            reports = tuple(parse_junit_dir(job_artifacts_path))
            self._organize_artifacts(job_artifacts_path, batch_job)
        else:
            self._logger.warning(
                "No artifact directory found for job %s", batch_job.name, extra={"run_id": message.run_id}
            )

        return JobResult(
            integration=batch_job.target,
            environment=batch_job.environment,
            platform=batch_job.platform,
            status=status,
            failed_steps=failed_steps,
            reports=reports,
        )

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

    @staticmethod
    def _build_workflow_status(message: BatchFinished, results: list[JobResult]) -> WorkflowStatus:
        success_count = sum(1 for result in results if result.status == Status.SUCCESS)
        failed_count = sum(1 for result in results if result.status == Status.FAILURE)
        skipped_count = sum(1 for result in results if result.status == Status.SKIPPED)
        return WorkflowStatus(
            batch_id=message.id,
            url=message.workflow_url,
            id=message.run_id,
            success_count=success_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            results=results,
        )
