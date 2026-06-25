# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
import re
import shutil
from pathlib import Path

from ddev.cli.ci.tests.common import conclusion_to_status
from ddev.cli.ci.tests.messages import (
    BatchFinished,
    BatchJob,
    UpdatePRComment,
    WorkflowResult,
    WorkflowStatus,
)
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.junit import parse_junit_dir

# Expected layout of the extracted ``test-result.zip`` tree (defined by ``test-batch.yaml``):
#   {artifacts_path}/
#     {job_name}/                     one directory per test target, named after BatchJob.name
#       coverage.xml                  Cobertura coverage report
#       test-{unit|e2e}-{env}.xml     pytest JUnit report(s)
# Per-job conclusions and failed step come from the jobs forwarded on the message
# (BatchFinished.workflow_jobs); jobs absent from that list fall back to the batch-level status.
COVERAGE_GLOB = "coverage*.xml"
JUNIT_GLOB = "test-*.xml"


class TaskTestGatherer(AsyncProcessor[BatchFinished]):
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
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: BatchFinished) -> None:
        artifacts_path = Path(message.artifacts_path)
        jobs_by_name = {job.name: job for job in message.job_list}
        job_statuses = self._read_job_statuses(message)

        default_status = (message.status, "timed out" if message.timed_out else None)
        results: list[WorkflowResult] = []
        for job_name, batch_job in jobs_by_name.items():
            conclusion, failed_step = job_statuses.get(job_name, default_status)
            job_dir = self._locate_job_dir(artifacts_path, job_name)
            failed_tests: list[str] = []
            if job_dir is not None:
                failed_tests = [test.identifier for test in parse_junit_dir(job_dir)]
                self._organize_artifacts(job_dir, batch_job)
            else:
                self._logger.info("No artifact directory found for job %s", job_name, extra={"run_id": message.run_id})
            results.append(
                WorkflowResult(
                    integration=batch_job.target,
                    environment=batch_job.environment,
                    platform=batch_job.platform,
                    status=conclusion_to_status(conclusion),
                    failed_step=failed_step,
                    failed_tests=failed_tests,
                )
            )

        status = self._build_workflow_status(message, results)
        async with self._lock:
            self._results_by_run[message.run_id] = results
            self._status_by_run[message.run_id] = status
            self._received_batches += 1
            is_final = self._received_batches >= self._expected_batches

        if is_final:
            self.submit_message(self.build_done_message(message.id))
            self._logger.info("Final batch received, UpdatePRComment emitted", extra={"run_id": message.run_id})

    def build_done_message(self, message_id: str) -> UpdatePRComment:
        """Build the final ``done=True`` update from all accumulated results.

        Submitted by the gatherer once the final expected batch has been received.
        """
        return UpdatePRComment(id=message_id, done=True, workflows=list(self._status_by_run.values()))

    @staticmethod
    def _read_job_statuses(message: BatchFinished) -> dict[str, tuple[str | None, str | None]]:
        """Map job name -> (conclusion, failed_step) from the jobs forwarded on the message."""
        statuses: dict[str, tuple[str | None, str | None]] = {}
        for job in message.workflow_jobs or []:
            failed_step = next((step.name for step in job.steps if step.conclusion == "failure"), None)
            statuses[job.name] = (job.conclusion, failed_step)
        return statuses

    @staticmethod
    def _locate_job_dir(artifacts_path: Path, job_name: str) -> Path | None:
        """Find the artifact directory for a job: an exact name match, else one whose name
        contains the job name as a whole, delimiter-bounded token (so ``j1`` never matches ``j12``)."""
        if not artifacts_path.exists():
            return None
        exact = artifacts_path / job_name
        if exact.is_dir():
            return exact
        token = re.compile(rf"(?<![A-Za-z0-9]){re.escape(job_name)}(?![A-Za-z0-9])")
        for child in sorted(artifacts_path.iterdir()):
            if child.is_dir() and token.search(child.name):
                return child
        return None

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
        success_count = sum(1 for result in results if result.status == "success")
        failed_count = sum(1 for result in results if result.status == "failure")
        failed_checks = [result for result in results if result.status == "failure"]
        return WorkflowStatus(
            url=message.workflow_url,
            id=message.run_id,
            success_count=success_count,
            failed_count=failed_count,
            failed_checks=failed_checks,
        )
