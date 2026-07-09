# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path

from ddev.cli.ci.tests.messages import (
    BatchFinished,
    BatchJob,
    BatchJobResult,
    UpdatePRComment,
    WorkflowResult,
    WorkflowStatus,
)
from ddev.cli.ci.tests.status import Status, conclusion_to_status
from ddev.event_bus.orchestrator import SyncProcessor
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.junit import parse_junit_dir

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
    ``WorkflowResult`` records, and organizes coverage/JUnit files for later publishing.

    It accumulates the results of each batch and, once all expected batches have finished,
    emits a single ``UpdatePRComment`` (``done=True``) with the aggregate state. It does not
    post to GitHub and does not update the PR before the final batch is in — the PR-comment
    consumer is separate.

    This task makes no GitHub API calls — it works exclusively from the artifacts the runner
    already downloaded to ``BatchFinished.artifacts_path``.
    """

    def __init__(self, name: str, output_base_path: Path, expected_batches: int) -> None:
        super().__init__(name)
        self._output_base_path = output_base_path
        self._expected_batches = expected_batches
        self._received_batches = 0
        self._status_by_run: dict[int, WorkflowStatus] = {}
        self._results_by_run: dict[int, list[WorkflowResult]] = {}
        self._lock = threading.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    def process_message(self, message: BatchFinished) -> None:
        if not message.batch_jobs:
            self._logger.warning(
                "BatchFinished carried no jobs; nothing to gather", extra={"run_id": message.run_id}
            )
            return

        results = [self._job_result(batch_job_result, message) for batch_job_result in message.batch_jobs]

        status = self._build_workflow_status(message, results)
        with self._lock:
            self._results_by_run[message.run_id] = results
            self._status_by_run[message.run_id] = status
            self._received_batches += 1
            is_final = self._received_batches >= self._expected_batches

        # TODO: if an expected batch never yields a BatchFinished (e.g. a runner crashes), the count
        # never completes and no final update fires. A future orchestrator on_finalize should call
        # build_done_message as a backstop.
        if is_final:
            self.submit_message(self.build_done_message(message.id))
            self._logger.info("Final batch received, UpdatePRComment emitted", extra={"run_id": message.run_id})

    def build_done_message(self, message_id: str) -> UpdatePRComment:
        """Build the final ``done=True`` update from all accumulated results.

        Submitted by the gatherer once the final expected batch has been received.
        """
        return UpdatePRComment(id=message_id, done=True, workflows=list(self._status_by_run.values()))

    def _job_result(self, batch_job_result: BatchJobResult, message: BatchFinished) -> WorkflowResult:
        """Build a job's ``WorkflowResult`` from its correlated workflow job and artifacts on disk."""
        batch_job = batch_job_result.job
        status, failed_step = self._job_status(batch_job_result, message)

        failed_tests: list[str] = []
        job_dir = Path(batch_job_result.artifact_name_path) if batch_job_result.artifact_name_path else None
        if job_dir is not None:
            failed_tests = [test.identifier for test in parse_junit_dir(job_dir)]
            self._organize_artifacts(job_dir, batch_job)
        else:
            self._logger.info(
                "No artifact directory found for job %s", batch_job.name, extra={"run_id": message.run_id}
            )

        return WorkflowResult(
            integration=batch_job.target,
            environment=batch_job.environment,
            platform=batch_job.platform,
            status=status,
            failed_step=failed_step,
            failed_tests=failed_tests,
        )

    @staticmethod
    def _job_status(batch_job_result: BatchJobResult, message: BatchFinished) -> tuple[Status, str | None]:
        """Per-job (status, failed_step). Deterministic: timed-out batches fail every job; otherwise the
        job's own workflow-job conclusion decides. A missing workflow job is unexpected and raises — the
        runner correlates every job before emitting, so a miss is a bug, not a state to paper over.
        """
        if message.timed_out:
            return (Status.FAILURE, "timed out")

        workflow_job = batch_job_result.workflow_job
        if workflow_job is None:
            raise ValueError(f"No workflow job correlated for {batch_job_result.job.name!r}")

        failed_step = next(
            (step.name for step in workflow_job.steps if step.conclusion == WorkflowJobConclusion.FAILURE), None
        )
        return (conclusion_to_status(workflow_job.conclusion), failed_step)

    def _organize_artifacts(self, job_dir: Path, batch_job: BatchJob) -> None:
        """Copy coverage and JUnit files into the organized output tree with unique names."""
        prefix = f"{batch_job.target}-{batch_job.environment}-{batch_job.platform}-{batch_job.runner}"

        coverage_dir = self._output_base_path / "coverage"
        for index, coverage_file in enumerate(sorted(job_dir.rglob(COVERAGE_GLOB))):
            suffix = "" if index == 0 else f"-{index}"
            self._copy(coverage_file, coverage_dir / f"{prefix}{suffix}.xml")

        test_results_dir = self._output_base_path / "test_results"
        for junit_file in sorted(job_dir.rglob(JUNIT_GLOB)):
            self._copy(junit_file, test_results_dir / f"{prefix}-{junit_file.stem}.xml")

    def _copy(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        self._logger.debug("Organized artifact %s -> %s", source, destination)

    @staticmethod
    def _build_workflow_status(message: BatchFinished, results: list[WorkflowResult]) -> WorkflowStatus:
        success_count = sum(1 for result in results if result.status == Status.SUCCESS)
        failed_count = sum(1 for result in results if result.status == Status.FAILURE)
        failed_checks = [result for result in results if result.status == Status.FAILURE]
        return WorkflowStatus(
            url=message.workflow_url,
            id=message.run_id,
            success_count=success_count,
            failed_count=failed_count,
            failed_checks=failed_checks,
        )
