# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import base64
import dataclasses
import gzip
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from itertools import count
from pathlib import Path
from time import monotonic
from typing import Any

from pydantic import ValidationError

from ddev.cli.ci.tests.dispatcher_attributes import batch_fields, job_fields, test_tag_mapping
from ddev.cli.ci.tests.execution_metrics import MetricsHelper, Operation
from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchJobResult, BatchProgressUpdate, TestBatch
from ddev.cli.ci.tests.progress import ExecutionState
from ddev.cli.ci.tests.status import conclusion_to_status
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.monitoring import ComponentMonitor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import Artifact, WorkflowJob, WorkflowRun
from ddev.utils.github_async.models.workflow import WorkflowJobStatus
from ddev.utils.github_async.retry import SAFE_RETRY, on_status

# A cancelled job has roughly ten seconds before it is killed, and there may be several runs to stop.
# The retry policy bounds the ladder, not a socket, so a GitHub that accepts the connection and then
# goes quiet would hold this for the client's default and take every other cancellation with it.
CANCEL_REQUEST_TIMEOUT = 3.0

# GitHub rejects a workflow dispatch whose whole `inputs` object exceeds this.
# https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
WORKFLOW_INPUTS_LIMIT = 65535

# Jobs are listed right after the run is dispatched, before GitHub makes the run's jobs listing
# visible, and until then that endpoint answers 404.
JOBS_LISTING_RETRY = SAFE_RETRY.also_on(on_status(404))


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


def _serialize_test_tags(fields: Mapping[str, Any]) -> str:
    tags = test_tag_mapping(fields)
    return ','.join(f'{name}:{_sanitize_test_tag_value(value)}' for name, value in sorted(tags.items()))


def _sanitize_test_tag_value(value: str) -> str:
    return value.replace(',', '_').replace('\n', '_').replace('\r', '_')


def workflow_duration_seconds(run: WorkflowRun) -> float | None:
    """Use gh's completed-run timing convention, omitting unavailable or invalid timestamps.

    https://github.com/cli/cli/blob/trunk/pkg/cmd/run/shared/shared.go
    """
    if run.run_started_at is None or run.updated_at is None:
        return None
    try:
        duration = (datetime.fromisoformat(run.updated_at) - datetime.fromisoformat(run.run_started_at)).total_seconds()
    except (ValueError, TypeError):
        return None
    return duration if duration >= 0 else None


def encode_job_list(jobs: list[dict[str, Any]]) -> str:
    """Encode a batch's jobs for a workflow input, as gzip then base64.

    A repository-wide batch is several times the 65,535-character input limit as plain JSON, and
    compresses by around 17x. `mtime=0` keeps the result a function of the jobs alone, so the same
    plan always encodes to the same string.
    """
    raw = json.dumps(jobs, separators=(",", ":")).encode()
    return base64.b64encode(gzip.compress(raw, mtime=0)).decode()


# Limit the exception summary, not the detailed validation log.
RESPONSE_REASON_LIMIT = 240


@dataclass(frozen=True)
class TestRunnerOptions:
    """Configuration for a `TaskTestRunner`."""

    owner: str
    repo: str
    workflow_id: str | int
    ref: str
    run_fields: Mapping[str, Any]
    concurrency_key: str
    artifacts_base_path: Path
    poll_interval_seconds: float = 30.0
    pytest_args: str = ''
    origin_run_url: str | None = None
    pr_number: int | None = None


class TaskTestRunner(AsyncProcessor[TestBatch]):
    """
    Dispatches and reports execution progress, then downloads artifacts and emits `BatchFinished`.
    """

    def __init__(
        self,
        name: str,
        client: AsyncGitHubClient,
        options: TestRunnerOptions,
        *,
        artifact_client: AsyncGitHubClient,
        monitor: ComponentMonitor,
    ):
        super().__init__(name)
        self._client = client
        self._artifact_client = artifact_client
        self._options = options
        self._runs_in_flight: dict[str, int] = {}
        self._logger = monitor.logger
        self.monitor = monitor
        self._metrics = MetricsHelper(monitor.metrics)

    def _response_failure(
        self, operation: str, batch_id: str, run_id: int | None, error: ValidationError
    ) -> FatalProcessingError:
        """Log every validation error and return a bounded, contextual failure."""
        run = f", run {run_id}" if run_id is not None else ""
        self._logger.error(
            "Invalid GitHub response while %s (batch %s%s):\n%s",
            operation,
            batch_id,
            run,
            error,
        )
        count = error.error_count()
        reason = " ".join(
            (
                f"Invalid GitHub response while {operation} (batch {batch_id}{run}): "
                f"{count} validation error{'s' if count != 1 else ''} in {error.title}. See logs for details."
            ).split()
        )
        if len(reason) > RESPONSE_REASON_LIMIT:
            reason = reason[: RESPONSE_REASON_LIMIT - 3].rstrip() + "..."
        return FatalProcessingError(reason)

    async def process_message(self, message: TestBatch):
        self._logger.info(
            "Dispatching batch %s (integrations=%s, jobs=%s)",
            message.batch_id,
            len(message.integrations),
            message.jobs_count,
        )
        run_id, workflow_url = await self._dispatch_batch(message)
        with self.monitor.scope(run_id=run_id, workflow_url=workflow_url):
            self._logger.info(
                "Batch %s dispatched as workflow run %s",
                message.batch_id,
                run_id,
                workflow_status='queued',
            )
            run, jobs = await self._poll_until_complete(message, run_id)
            await self._collect_results(message, run_id, run.data, jobs)

    async def _dispatch_batch(self, message: TestBatch) -> tuple[int, str]:
        try:
            dispatch = await self._client.create_workflow_dispatch(
                self._options.owner,
                self._options.repo,
                self._options.workflow_id,
                ref=self._options.ref,
                inputs=self._build_inputs(message),
                return_run_details=True,
            )
        except ValidationError as error:
            self._metrics.record_operation(Operation.DISPATCH_BATCH, failed=True)
            raise self._response_failure("dispatching the batch", message.batch_id, None, error) from error
        except Exception:
            self._metrics.record_operation(Operation.DISPATCH_BATCH, failed=True)
            raise
        self._metrics.record_operation(Operation.DISPATCH_BATCH, failed=False)
        run_id = dispatch.data.workflow_run_id
        self._runs_in_flight[message.batch_id] = run_id
        message.run_id = run_id
        self._report_launch(message)
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
        return run_id, dispatch.data.html_url

    async def _collect_results(
        self,
        message: TestBatch,
        run_id: int,
        run: WorkflowRun,
        jobs: list[WorkflowJob],
    ) -> None:
        conclusion = run.conclusion
        workflow_url = run.html_url
        if conclusion is None:
            self._logger.warning("Workflow run %s completed with null conclusion", run_id)
        self._logger.info("Collecting artifacts for workflow run %s", run_id)
        artifact_dirs = await self._download_artifacts(run_id, message.batch_id)
        self._logger.info(
            "Artifacts downloaded for workflow run %s (count=%s)",
            run_id,
            len(artifact_dirs),
            artifact_count=len(artifact_dirs),
        )
        jobs = await self._reconcile_final_jobs(run_id, message.batch_id, jobs)
        batch_jobs = BatchJobResult.correlate(message.job_list, jobs, artifact_dirs)
        status = conclusion_to_status(conclusion)
        self.submit_message(
            BatchFinished(
                id=message.id,
                batch_id=message.batch_id,
                status=status,
                run_id=run_id,
                workflow_url=workflow_url,
                artifacts_path=str(self._options.artifacts_base_path),
                batch_jobs=batch_jobs,
            )
        )
        self._logger.info("Batch %s workflow results ready: %s", message.batch_id, status.value)

    def _report_launch(self, batch: TestBatch) -> None:
        """Count the batch and its jobs only after GitHub accepts its dispatch."""
        metrics = self.monitor.metrics
        metrics.count('batches.count', 1)
        # One sample per launch supports batch-size averages without per-batch tags.
        metrics.distribution('batch.jobs.count', batch.jobs_count)
        for job in batch.job_list:
            metrics.count('jobs.count', 1, **job_fields(job))

    async def cancel_dispatched_runs(self) -> None:
        """Concurrently cancel all tracked unfinished runs."""
        if not self._runs_in_flight:
            return

        self._logger.info("Cancelling %s dispatched run(s)", len(self._runs_in_flight))
        await asyncio.gather(
            *(self._cancel_run(batch_id, run_id) for batch_id, run_id in tuple(self._runs_in_flight.items()))
        )

    async def _cancel_run(self, batch_id: str, run_id: int) -> None:
        """Cancel one run, reporting rather than raising: one that will not cancel must not stop the rest."""
        # Cancellation runs outside message processing, so it carries the batch and run identity itself.
        with self.monitor.scope(batch_id=batch_id, run_id=run_id):
            try:
                await self._client.cancel_workflow_run(
                    self._options.owner, self._options.repo, run_id, timeout=CANCEL_REQUEST_TIMEOUT
                )
            except Exception:
                self._logger.exception("Failed to cancel workflow run %s for batch %s", run_id, batch_id)
            else:
                self._runs_in_flight.pop(batch_id, None)
                self._logger.info("Workflow run %s for batch %s cancelled", run_id, batch_id)

    async def _poll_until_complete(
        self, message: TestBatch, run_id: int
    ) -> tuple[GitHubResponse[WorkflowRun], list[WorkflowJob]]:
        sequences = count(1)
        known_jobs: dict[str, WorkflowJob] = {}
        previous_state: ExecutionState | None = None
        previous_poll: float | None = None
        while True:
            poll_started = monotonic()
            if previous_poll is not None:
                self.monitor.metrics.distribution('requests.polling_interval', poll_started - previous_poll)
            previous_poll = poll_started
            try:
                run = await self._client.get_workflow_run(self._options.owner, self._options.repo, run_id)
            except ValidationError as error:
                self._metrics.record_operation(Operation.FETCH_WORKFLOW, failed=True)
                raise self._response_failure("polling workflow status", message.batch_id, run_id, error) from error
            except Exception:
                self._metrics.record_operation(Operation.FETCH_WORKFLOW, failed=True)
                raise
            self._metrics.record_operation(Operation.FETCH_WORKFLOW, failed=False)
            completed = run.data.is_completed
            # Shutdown must not try to cancel a completed run while its artifacts are still being collected.
            if completed:
                self._runs_in_flight.pop(message.batch_id, None)
                if (duration := workflow_duration_seconds(run.data)) is not None:
                    self.monitor.metrics.distribution('batch.duration', duration)

            # Report workflow progress first. The jobs request may be delayed by the API rate limit.
            progress = self._publish_workflow_progress(message, run_id, run.data, known_jobs, next(sequences))
            if progress.state is not previous_state:
                self._logger.info(
                    "Batch %s state changed to %s",
                    message.batch_id,
                    progress.state.value,
                    batch_state=progress.state.value,
                )
                previous_state = progress.state
            await self._refresh_jobs(run_id, known_jobs, message.batch_id, "listing workflow jobs")
            self._publish_job_progress(message.id, progress, known_jobs, next(sequences))

            if completed:
                self._logger.info(
                    "Workflow run %s completed: %s",
                    run_id,
                    run.data.conclusion or run.data.status,
                    workflow_status=run.data.status,
                    workflow_conclusion=run.data.conclusion,
                )
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

    async def _refresh_jobs(
        self, run_id: int, known_jobs: dict[str, WorkflowJob], batch_id: str, operation: str
    ) -> None:
        # A failed or incomplete listing must not remove jobs we already know about.
        for job in await self._list_jobs(run_id, batch_id, operation):
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
        self, run_id: int, batch_id: str, observed_jobs: list[WorkflowJob]
    ) -> list[WorkflowJob]:
        known_jobs = {job.name: job for job in observed_jobs}
        # The jobs response may lag behind the workflow status. Refresh it after downloading artifacts.
        await self._refresh_jobs(run_id, known_jobs, batch_id, "reconciling final workflow jobs")
        # An unfinished job has no result yet. Do not mistake that for a test failure.
        return [job for job in known_jobs.values() if job.status is WorkflowJobStatus.COMPLETED]

    async def _list_jobs(self, run_id: int, batch_id: str, operation: str) -> list[WorkflowJob]:
        """Fetch the run's jobs. If a later page fails, keep the jobs already fetched."""
        jobs: list[WorkflowJob] = []
        try:
            async for page in self._client.list_workflow_jobs(
                self._options.owner, self._options.repo, run_id, per_page=100, retry=JOBS_LISTING_RETRY
            ):
                jobs.extend(page.data.jobs)
        except ValidationError as error:
            self._metrics.record_operation(Operation.REFRESH_JOBS, failed=True)
            raise self._response_failure(operation, batch_id, run_id, error) from error
        except Exception:
            self._logger.warning("Failed to list workflow jobs", exc_info=True)
            self._metrics.record_operation(Operation.REFRESH_JOBS, failed=True)
        else:
            self._metrics.record_operation(Operation.REFRESH_JOBS, failed=False)
        return jobs

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        run = self._options.run_fields
        inputs = {
            "batch_id": message.batch_id,
            "checkout_sha": str(run["checkout_sha"]),
            # Keys the workflow's cancellation group; see `ResolvedRun.concurrency_key`.
            "concurrency_key": self._options.concurrency_key,
            # The batch is dispatched at the default branch, so its own context describes master.
            # These two say which commit the results belong to, for CI Visibility and the check run.
            "head_sha": str(run["head_sha"]),
            "head_branch": str(run["head_branch"]),
            "context": str(run["context"]),
            # The batch withholds every credential when this is true, so it is sent on every dispatch
            # rather than only when set: an absent input would default the workflow to trusting it.
            "is_fork": str(run["is_fork"]).lower(),
            "integrations": json.dumps(message.integrations),
            "job_list": encode_job_list([self._job_input(message, job) for job in message.job_list]),
        }
        # GitHub rejects inputs the workflow does not declare, so unset means absent, not empty.
        if self._options.pytest_args:
            inputs["pytest_args"] = self._options.pytest_args
        if self._options.origin_run_url:
            inputs["origin_run_url"] = self._options.origin_run_url
        if self._options.pr_number is not None:
            inputs["pr_number"] = str(self._options.pr_number)
        size = sum(len(value) for value in inputs.values())
        if size > WORKFLOW_INPUTS_LIMIT:
            raise JobListTooLargeError(message.batch_id, size)

        return inputs

    def _job_input(self, batch: TestBatch, job: BatchJob) -> dict[str, Any]:
        """Serialize a job with its artifact identity and centrally defined CI Visibility tags."""
        fields = {**self._options.run_fields, **batch_fields(batch), **job_fields(job)}
        return {
            **dataclasses.asdict(job),
            "artifact_name": job.artifact_name(),
            "additional_tags": _serialize_test_tags(fields),
        }

    async def _download_artifacts(self, run_id: int, batch_id: str) -> dict[str, Path]:
        """Download the run's artifacts and return an artifact-name -> path map.

        The map keys on the GitHub artifact name (the contract a `BatchJob` reproduces via
        `artifact_name`), letting the producer resolve each job's directory deterministically.
        """
        artifact_dirs: dict[str, Path] = {}
        failures: list[tuple[int, str]] = []
        with self._metrics.time_operation(
            Operation.COLLECT_ARTIFACTS, duration_metric='artifacts.download.duration'
        ) as result:
            degraded = False
            try:
                async for page in self._artifact_client.list_workflow_run_artifacts(
                    self._options.owner, self._options.repo, run_id, per_page=100
                ):
                    for artifact in page.data.artifacts:
                        url = self._artifact_download_url(artifact)
                        if url is None:
                            degraded = True
                            continue
                        target = await self._download_artifact(artifact, url)
                        if target is None:
                            failures.append((artifact.id, artifact.name))
                        else:
                            artifact_dirs[artifact.name] = target
            except ValidationError as error:
                raise self._response_failure("listing workflow artifacts", batch_id, run_id, error) from error
            except Exception:
                self._logger.warning("Failed to list workflow run artifacts", exc_info=True)
                degraded = True
            # An incomplete listing degrades the collection like a failed download does.
            result.failed = degraded or bool(failures)
        if failures:
            self._logger.warning(
                "Failed to download %s %s for workflow run %s",
                len(failures),
                "artifact" if len(failures) == 1 else "artifacts",
                run_id,
                failure_count=len(failures),
                failed_artifacts=failures,
            )
        return artifact_dirs

    def _artifact_download_url(self, artifact: Artifact) -> str | None:
        if artifact.expired:
            self._logger.info(
                "Skipping expired artifact %s",
                artifact.name,
                artifact_id=artifact.id,
                artifact_name=artifact.name,
            )
            return None
        if not artifact.archive_download_url:
            self._logger.info(
                "Skipping artifact %s without a download URL",
                artifact.name,
                artifact_id=artifact.id,
                artifact_name=artifact.name,
            )
            return None
        return artifact.archive_download_url

    async def _download_artifact(self, artifact: Artifact, url: str) -> Path | None:
        target = self._options.artifacts_base_path / artifact.name
        try:
            await self._artifact_client.download_artifact(url, target)
            self._logger.info(
                "Downloaded artifact %s",
                artifact.name,
                artifact_id=artifact.id,
                artifact_name=artifact.name,
                path=str(target),
            )
            return target
        except Exception as exc:
            self._logger.warning(
                "Failed to download artifact %s",
                artifact.name,
                artifact_id=artifact.id,
                artifact_name=artifact.name,
                error=str(exc),
            )
            return None
