# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import base64
import dataclasses
import gzip
import json
import logging
from dataclasses import dataclass
from itertools import count
from pathlib import Path
from typing import Any

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchJobResult, BatchProgressUpdate, TestBatch
from ddev.cli.ci.tests.progress import ExecutionState
from ddev.cli.ci.tests.status import conclusion_to_status
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.monitoring import ComponentMonitor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import Artifact, WorkflowJob, WorkflowRun
from ddev.utils.github_async.models.workflow import WorkflowJobStatus

# A cancelled job has roughly ten seconds before it is killed, and there may be several runs to stop.
# The retry policy bounds the ladder, not a socket, so a GitHub that accepts the connection and then
# goes quiet would hold this for the client's default and take every other cancellation with it.
CANCEL_REQUEST_TIMEOUT = 3.0

# GitHub rejects a workflow dispatch whose whole `inputs` object exceeds this.
# https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
WORKFLOW_INPUTS_LIMIT = 65535


class JobListTooLargeError(Exception):
    """Raised when a batch's inputs exceed what a workflow dispatch accepts.

    Dispatching anyway fails the request, so the batch never runs and its jobs are never reported.
    """

    def __init__(self, batch_id: str, size: int):
        super().__init__(
            f"Batch {batch_id} needs {size} characters of workflow inputs, over GitHub's "
            f"{WORKFLOW_INPUTS_LIMIT}. Lower `max_jobs_per_batch` so the plan splits further."
        )
        self.batch_id = batch_id
        self.size = size


def encode_job_list(jobs: list[dict[str, Any]]) -> str:
    """Encode a batch's jobs for a workflow input, as gzip then base64.

    A repository-wide batch is several times the 65,535-character input limit as plain JSON, and
    compresses by around 17x. `mtime=0` keeps the result a function of the jobs alone, so the same
    plan always encodes to the same string.
    """
    raw = json.dumps(jobs, separators=(",", ":")).encode()
    return base64.b64encode(gzip.compress(raw, mtime=0)).decode()


@dataclass(frozen=True)
class TestRunnerOptions:
    """Configuration for a ``TaskTestRunner``."""

    owner: str
    repo: str
    workflow_id: str | int
    ref: str
    base_sha: str
    checkout_sha: str
    artifacts_base_path: Path
    branch: str = ''
    is_fork: bool = False
    poll_interval_seconds: float = 30.0
    pytest_args: str = ''


class TaskTestRunner(AsyncProcessor[TestBatch]):
    """
    Dispatches and reports execution progress, then downloads artifacts and emits ``BatchFinished``.
    """

    def __init__(
        self,
        name: str,
        client: AsyncGitHubClient,
        options: TestRunnerOptions,
        *,
        artifact_client: AsyncGitHubClient,
        monitor: ComponentMonitor | None = None,
    ):
        super().__init__(name)
        self._client = client
        self._artifact_client = artifact_client
        self._options = options
        self._runs_in_flight: dict[str, int] = {}
        self._logger = logging.getLogger(f"{__name__}.{name}")
        self.monitor = monitor

    async def process_message(self, message: TestBatch):
        log_extra: dict[str, Any] = {"batch_id": message.batch_id}
        run_id = await self._dispatch_batch(message, log_extra)
        run, jobs = await self._poll_until_complete(message, run_id, log_extra)
        await self._collect_results(message, run_id, run.data, jobs, log_extra)

    async def _dispatch_batch(self, message: TestBatch, log_extra: dict[str, Any]) -> int:
        dispatch = await self._client.create_workflow_dispatch(
            self._options.owner,
            self._options.repo,
            self._options.workflow_id,
            ref=self._options.ref,
            inputs=self._build_inputs(message),
            return_run_details=True,
        )
        run_id = dispatch.data.workflow_run_id
        log_extra["run_id"] = run_id
        self._runs_in_flight[message.batch_id] = run_id
        self._logger.info("Dispatched batch", extra=log_extra)
        self.submit_message(
            BatchProgressUpdate(
                id=f"{message.id}-progress-0",
                batch_id=message.batch_id,
                run_id=run_id,
                workflow_url=dispatch.data.html_url,
                state=ExecutionState.QUEUED,
                sequence=0,
            )
        )
        return run_id

    async def _collect_results(
        self,
        message: TestBatch,
        run_id: int,
        run: WorkflowRun,
        jobs: list[WorkflowJob],
        log_extra: dict[str, Any],
    ) -> None:
        conclusion = run.conclusion
        workflow_url = run.html_url
        if conclusion is None:
            self._logger.warning("Workflow completed with null conclusion", extra=log_extra)
        artifact_dirs = await self._download_artifacts(run_id, log_extra)
        self._logger.info("Artifacts downloaded", extra=log_extra)
        jobs = await self._reconcile_final_jobs(run_id, jobs, log_extra)
        batch_jobs = BatchJobResult.correlate(message.job_list, jobs, artifact_dirs)
        self.submit_message(
            BatchFinished(
                id=message.id,
                batch_id=message.batch_id,
                status=conclusion_to_status(conclusion),
                run_id=run_id,
                workflow_url=workflow_url,
                artifacts_path=str(self._options.artifacts_base_path),
                batch_jobs=batch_jobs,
            )
        )
        self._logger.info("BatchFinished emitted", extra=log_extra)

    async def cancel_dispatched_runs(self) -> None:
        """Cancel the runs this runner dispatched that have not finished.

        The batch workflow's concurrency group already cancels a superseded revision's batches. This
        covers what the group cannot see: a cancellation or a closed pull request with no follow-up
        push, a plan that shrank, and the minutes between this process being killed and the next
        batches being dispatched. Concurrent, because whatever budget the caller has is shared by
        all of them.
        """
        if not self._runs_in_flight:
            return

        self._logger.info("Cancelling %s dispatched run(s)", len(self._runs_in_flight))
        await asyncio.gather(
            *(self._cancel_run(batch_id, run_id) for batch_id, run_id in tuple(self._runs_in_flight.items()))
        )

    async def _cancel_run(self, batch_id: str, run_id: int) -> None:
        """Cancel one run, reporting rather than raising: one that will not cancel must not stop the rest."""
        log_extra = {"batch_id": batch_id, "run_id": run_id}
        try:
            await self._client.cancel_workflow_run(
                self._options.owner, self._options.repo, run_id, timeout=CANCEL_REQUEST_TIMEOUT
            )
        except Exception:
            self._logger.exception("Failed to cancel dispatched run", extra=log_extra)
        else:
            self._runs_in_flight.pop(batch_id, None)
            self._logger.info("Dispatched run cancelled", extra=log_extra)

    async def _poll_until_complete(
        self, message: TestBatch, run_id: int, log_extra: dict[str, Any]
    ) -> tuple[GitHubResponse[WorkflowRun], list[WorkflowJob]]:
        sequences = count(1)
        known_jobs: dict[str, WorkflowJob] = {}
        while True:
            run = await self._client.get_workflow_run(self._options.owner, self._options.repo, run_id)
            completed = run.data.is_completed
            # Shutdown must not try to cancel a completed run while its artifacts are still being collected.
            if completed:
                self._runs_in_flight.pop(message.batch_id, None)
            log_extra["workflow_url"] = run.data.html_url

            # Report workflow progress first. The jobs request may be delayed by the API rate limit.
            progress = self._publish_workflow_progress(message, run_id, run.data, known_jobs, next(sequences))
            await self._refresh_jobs(run_id, known_jobs, log_extra)
            self._publish_job_progress(message.id, progress, known_jobs, next(sequences))

            if completed:
                self._logger.info("Workflow completed", extra=log_extra)
                return run, list(known_jobs.values())
            await asyncio.sleep(self._options.poll_interval_seconds)

    def _publish_workflow_progress(
        self,
        message: TestBatch,
        run_id: int,
        run: WorkflowRun,
        known_jobs: dict[str, WorkflowJob],
        sequence: int,
    ) -> BatchProgressUpdate:
        if run.is_completed:
            state = ExecutionState.ARTIFACT_DOWNLOAD
        elif run.status == "in_progress":
            state = ExecutionState.RUNNING
        else:
            state = ExecutionState.QUEUED
        progress = BatchProgressUpdate(
            id=f"{message.id}-progress-{sequence}",
            batch_id=message.batch_id,
            run_id=run_id,
            workflow_url=run.html_url,
            state=state,
            status=conclusion_to_status(run.conclusion) if run.is_completed else None,
            sequence=sequence,
            jobs=tuple(known_jobs.values()),
        )
        self.submit_message(progress)
        return progress

    async def _refresh_jobs(self, run_id: int, known_jobs: dict[str, WorkflowJob], log_extra: dict[str, Any]) -> None:
        # A failed or incomplete listing must not remove jobs we already know about.
        for job in await self._list_jobs(run_id, log_extra):
            previous = known_jobs.get(job.name)
            # A rerun has a new job ID. An older state for the same job must not erase its completed result.
            if (
                previous is not None
                and previous.id == job.id
                and previous.status is WorkflowJobStatus.COMPLETED
                and job.status is not WorkflowJobStatus.COMPLETED
            ):
                continue
            known_jobs[job.name] = job

    def _publish_job_progress(
        self,
        message_id: str,
        progress: BatchProgressUpdate,
        known_jobs: dict[str, WorkflowJob],
        sequence: int,
    ) -> None:
        self.submit_message(
            dataclasses.replace(
                progress,
                id=f"{message_id}-progress-{sequence}",
                sequence=sequence,
                jobs=tuple(known_jobs.values()),
            )
        )

    async def _reconcile_final_jobs(
        self, run_id: int, observed_jobs: list[WorkflowJob], log_extra: dict[str, Any]
    ) -> list[WorkflowJob]:
        known_jobs = {job.name: job for job in observed_jobs}
        # The jobs response may lag behind the workflow status. Refresh it after downloading artifacts.
        await self._refresh_jobs(run_id, known_jobs, log_extra)
        # An unfinished job has no result yet. Do not mistake that for a test failure.
        return [job for job in known_jobs.values() if job.status is WorkflowJobStatus.COMPLETED]

    async def _list_jobs(self, run_id: int, log_extra: dict[str, Any]) -> list[WorkflowJob]:
        """Fetch the run's jobs. If a later page fails, keep the jobs already fetched."""
        jobs: list[WorkflowJob] = []
        try:
            async for page in self._client.list_workflow_jobs(
                self._options.owner, self._options.repo, run_id, per_page=100
            ):
                jobs.extend(page.data.jobs)
        except Exception:
            self._logger.warning("Failed to list workflow jobs", extra=log_extra, exc_info=True)
        return jobs

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        inputs = {
            "batch_id": message.batch_id,
            "checkout_sha": self._options.checkout_sha,
            # The batch is dispatched at the default branch, so its own context describes master.
            # These two say which commit the results belong to, for CI Visibility and the check run.
            "head_sha": self._options.base_sha,
            "branch": self._options.branch,
            # The batch withholds every credential when this is true, so it is sent on every dispatch
            # rather than only when set: an absent input would default the workflow to trusting it.
            "is_fork": str(self._options.is_fork).lower(),
            "integrations": json.dumps(message.integrations),
            "job_list": encode_job_list([self._job_input(job) for job in message.job_list]),
        }
        # GitHub rejects inputs the workflow does not declare, so unset means absent, not empty.
        if self._options.pytest_args:
            inputs["pytest_args"] = self._options.pytest_args
        size = sum(len(value) for value in inputs.values())
        if size > WORKFLOW_INPUTS_LIMIT:
            raise JobListTooLargeError(message.batch_id, size)

        return inputs

    @staticmethod
    def _job_input(job: BatchJob) -> dict[str, Any]:
        """Serialize a job for the workflow, carrying the artifact name so all its files upload under
        a single folder/zip named after it (matched later via ``BatchJob.artifact_name``)."""
        return {**dataclasses.asdict(job), "artifact_name": job.artifact_name()}

    async def _download_artifacts(self, run_id: int, log_extra: dict[str, Any]) -> dict[str, Path]:
        """Download the run's artifacts and return an artifact-name -> path map.

        The map keys on the GitHub artifact name (the contract a ``BatchJob`` reproduces via
        ``artifact_name``), letting the producer resolve each job's directory deterministically.
        """
        artifact_dirs: dict[str, Path] = {}
        failures: list[tuple[int, str]] = []
        try:
            async for page in self._artifact_client.list_workflow_run_artifacts(
                self._options.owner, self._options.repo, run_id, per_page=100
            ):
                for artifact in page.data.artifacts:
                    url = self._artifact_download_url(artifact, log_extra)
                    if url is None:
                        continue
                    target = await self._download_artifact(artifact, url, log_extra)
                    if target is None:
                        failures.append((artifact.id, artifact.name))
                    else:
                        artifact_dirs[artifact.name] = target
        except Exception:
            self._logger.warning("Failed to list workflow run artifacts", extra=log_extra, exc_info=True)
        if failures:
            self._logger.warning(
                "Artifact download had %s failures: %s",
                len(failures),
                failures,
                extra=log_extra,
            )
        return artifact_dirs

    def _artifact_download_url(self, artifact: Artifact, log_extra: dict[str, Any]) -> str | None:
        if artifact.expired:
            self._logger.info("Skipping expired artifact %s (%s)", artifact.id, artifact.name, extra=log_extra)
            return None
        if not artifact.archive_download_url:
            self._logger.info(
                "Skipping artifact %s (%s) without download URL", artifact.id, artifact.name, extra=log_extra
            )
            return None
        return artifact.archive_download_url

    async def _download_artifact(self, artifact: Artifact, url: str, log_extra: dict[str, Any]) -> Path | None:
        target = self._options.artifacts_base_path / artifact.name
        try:
            await self._artifact_client.download_artifact(url, target)
            self._logger.info("Downloaded artifact %s -> %s", artifact.id, target, extra=log_extra)
            return target
        except Exception as exc:
            self._logger.warning(
                "Failed to download artifact %s (%s): %s", artifact.id, artifact.name, exc, extra=log_extra
            )
            return None
