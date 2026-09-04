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
from pathlib import Path
from typing import Any

from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchJobResult, TestBatch
from ddev.cli.ci.tests.status import conclusion_to_status
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import WorkflowJob, WorkflowRun

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
    Runs one ``test-batch.yaml`` workflow for a ``TestBatch``: dispatches the run,
    opens a check run, polls until the workflow completes, downloads its artifacts,
    and emits a ``BatchFinished``.
    """

    def __init__(self, name: str, client: AsyncGitHubClient, options: TestRunnerOptions):
        super().__init__(name)
        self._client = client
        self._options = options
        self._runs_in_flight: dict[str, int] = {}
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: TestBatch):
        inputs = self._build_inputs(message)
        log_extra: dict[str, Any] = {"batch_id": message.batch_id}

        dispatch = await self._client.create_workflow_dispatch(
            self._options.owner,
            self._options.repo,
            self._options.workflow_id,
            ref=self._options.ref,
            inputs=inputs,
            return_run_details=True,
        )
        run_id = dispatch.data.workflow_run_id
        log_extra["run_id"] = run_id
        self._runs_in_flight[message.batch_id] = run_id
        self._logger.info("Dispatched batch", extra=log_extra)

        run = await self._client.get_workflow_run(self._options.owner, self._options.repo, run_id)
        workflow_url = run.data.html_url
        log_extra["workflow_url"] = workflow_url

        if run.data.status != "completed":
            run = await self._poll_until_complete(run_id, log_extra)
        else:
            self._logger.info("Workflow completed", extra=log_extra)

        # Popped only once the run is known to be over: while it is in flight it is what
        # `cancel_dispatched_runs` has to reap.
        self._runs_in_flight.pop(message.batch_id, None)

        raw = run.data.conclusion
        if raw is None:
            self._logger.warning("Workflow completed with null conclusion", extra=log_extra)

        artifact_dirs = await self._download_artifacts(run_id, log_extra)
        self._logger.info("Artifacts downloaded", extra=log_extra)

        jobs = await self._list_jobs(run_id, log_extra)
        batch_jobs = BatchJobResult.correlate(message.job_list, jobs, artifact_dirs)

        self.submit_message(
            BatchFinished(
                id=message.id,
                batch_id=message.batch_id,
                status=conclusion_to_status(raw),
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

    async def _poll_until_complete(self, run_id: int, log_extra: dict[str, Any]) -> GitHubResponse[WorkflowRun]:
        while True:
            await asyncio.sleep(self._options.poll_interval_seconds)
            run = await self._client.get_workflow_run(self._options.owner, self._options.repo, run_id)
            if run.data.status == "completed":
                self._logger.info("Workflow completed", extra=log_extra)
                return run

    async def _list_jobs(self, run_id: int, log_extra: dict[str, Any]) -> list[WorkflowJob]:
        """Fetch the workflow run's jobs; on failure log a warning and return an empty list."""
        jobs: list[WorkflowJob] = []
        try:
            async for page in self._client.list_workflow_jobs(self._options.owner, self._options.repo, run_id):
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
        base_path = self._options.artifacts_base_path
        artifact_dirs: dict[str, Path] = {}
        failures: list[tuple[int, str]] = []
        try:
            async for page in self._client.list_workflow_run_artifacts(self._options.owner, self._options.repo, run_id):
                for artifact in page.data.artifacts:
                    if artifact.expired:
                        self._logger.info(
                            "Skipping expired artifact %s (%s)",
                            artifact.id,
                            artifact.name,
                            extra=log_extra,
                        )
                        continue
                    if not artifact.archive_download_url:
                        self._logger.info(
                            "Skipping artifact %s (%s) without download URL",
                            artifact.id,
                            artifact.name,
                            extra=log_extra,
                        )
                        continue
                    target = base_path / artifact.name
                    try:
                        await self._client.download_artifact(artifact.archive_download_url, target)
                        artifact_dirs[artifact.name] = target
                        self._logger.info("Downloaded artifact %s -> %s", artifact.id, target, extra=log_extra)
                    except Exception as exc:
                        self._logger.warning(
                            "Failed to download artifact %s (%s): %s",
                            artifact.id,
                            artifact.name,
                            exc,
                            extra=log_extra,
                        )
                        failures.append((artifact.id, artifact.name))
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
