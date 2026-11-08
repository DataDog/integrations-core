# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import base64
import dataclasses
import gzip
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from time import monotonic
from typing import Any
from uuid import uuid4

import httpx
from pydantic import ValidationError

from ddev.cli.ci.tests.dispatcher_attributes import batch_fields, job_fields, test_tag_mapping
from ddev.cli.ci.tests.execution_metrics import MetricsHelper, Operation, OperationState
from ddev.cli.ci.tests.messages import BatchFinished, BatchJob, BatchJobResult, BatchProgressUpdate, TestBatch
from ddev.cli.ci.tests.progress import ExecutionState
from ddev.cli.ci.tests.status import (
    Status,
    batch_status,
    has_started_running,
    is_queued,
    job_status,
)
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.monitoring import ComponentMonitor
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import Artifact, WorkflowJob, WorkflowRun
from ddev.utils.github_async.models.workflow import WorkflowJobStatus
from ddev.utils.github_async.retry import PRE_SEND_TRANSPORT_ERRORS, SAFE_RETRY, on_status
from ddev.utils.platform import PlatformName

# A cancelled job has roughly ten seconds before it is killed, and there may be several runs to stop.
# The retry policy bounds the ladder, not a socket, so a GitHub that accepts the connection and then
# goes quiet would hold this for the client's default and take every other cancellation with it.
CANCEL_REQUEST_TIMEOUT = 3.0

# GitHub rejects a workflow dispatch whose whole `inputs` object exceeds this.
# https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
WORKFLOW_INPUTS_LIMIT = 65535

# GitHub can answer 404 while a resource is becoming visible after a successful mutation.
SAFE_RETRY_WITH_404 = SAFE_RETRY.also_on(on_status(404))

DISPATCH_LOOKUP_DELAYS = (10, 30, 60)
DISPATCH_CLOCK_SKEW_SECONDS = 60
# Filtered workflow searches return at most 1,000 results, even with pagination.
DISPATCH_LOOKUP_RUN_LIMIT = 1000
DISPATCH_RUN_TITLE_PATTERN = re.compile(r"Test Batch \[dispatch:[0-9a-f]{32}\] .+")


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


def _workflow_rejects_dispatch_id(error: Exception) -> bool:
    if not isinstance(error, httpx.HTTPStatusError) or error.response.status_code != 422:
        return False
    try:
        payload = error.response.json()
    except ValueError:
        return False
    return (
        isinstance(payload, dict)
        and isinstance(message := payload.get("message"), str)
        and message.startswith("Unexpected inputs provided:")
        and '"dispatch_id"' in message
    )


def _is_ambiguous_dispatch_error(error: Exception) -> bool:
    return (isinstance(error, httpx.HTTPStatusError) and 500 <= error.response.status_code < 600) or (
        isinstance(error, httpx.TransportError) and not isinstance(error, PRE_SEND_TRANSPORT_ERRORS)
    )


def _serialize_test_tags(fields: Mapping[str, Any]) -> str:
    tags = test_tag_mapping(fields)
    return ','.join(f'{name}:{_sanitize_test_tag_value(value)}' for name, value in sorted(tags.items()))


def _sanitize_test_tag_value(value: str) -> str:
    return value.replace(',', '_').replace('\n', '_').replace('\r', '_')


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
        # Each batch's latest queued/running counts by platform, so the gauges can sum concurrent
        # batches; a completed batch keeps its platforms at zero.
        self._job_activity_by_batch: dict[str, dict[PlatformName, list[int]]] = {}
        self._queue_durations_reported: set[int] = set()
        # Separate from `_queue_durations_reported`: a job can be seen starting but never finishing.
        self._finished_jobs_reported: set[int] = set()
        self._logger = monitor.logger
        self.monitor = monitor
        self._metrics = MetricsHelper(monitor)

    def _response_failure(
        self, state: OperationState, action: str, batch_id: str, run_id: int | None, error: ValidationError
    ) -> FatalProcessingError:
        """Mark the operation failed and return a bounded failure; the validation error stays in its traceback."""
        run = f", run {run_id}" if run_id is not None else ""
        state.fail("Invalid GitHub response while %s (batch %s%s)", action, batch_id, run)
        count = error.error_count()
        reason = " ".join(
            (
                f"Invalid GitHub response while {action} (batch {batch_id}{run}): "
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
        with self._metrics.operation(Operation.DISPATCH_BATCH) as op:
            try:
                run_id, workflow_url = await self._dispatch_batch_run(message)
            except ValidationError as error:
                raise self._response_failure(op, "dispatching the batch", message.batch_id, None, error) from error
            except Exception:
                op.fail("Failed to dispatch batch %s", message.batch_id)
                raise
        self._runs_in_flight[message.batch_id] = run_id
        message.run_id = run_id
        self._report_launch(message)
        self.submit_message(
            BatchProgressUpdate(
                id=f"{message.id}-progress-0",
                batch_id=message.batch_id,
                run_id=run_id,
                workflow_url=workflow_url,
                state=ExecutionState.QUEUED,
                sequence=0,
            )
        )
        return run_id, workflow_url

    async def _dispatch_batch_run(self, message: TestBatch) -> tuple[int, str]:
        inputs = self._build_inputs(message)
        started = datetime.now(UTC) - timedelta(seconds=DISPATCH_CLOCK_SKEW_SECONDS)
        created = f">={started.isoformat(timespec='seconds')}"
        redispatched = False
        while True:
            try:
                dispatch = await self._client.create_workflow_dispatch(
                    self._options.owner,
                    self._options.repo,
                    self._options.workflow_id,
                    ref=self._options.ref,
                    inputs=inputs,
                    return_run_details=True,
                )
            except Exception as error:
                if not redispatched and "dispatch_id" in inputs and _workflow_rejects_dispatch_id(error):
                    self._logger.warning(
                        "Workflow does not accept dispatch_id; dispatching batch %s without recovery",
                        message.batch_id,
                        batch_id=message.batch_id,
                    )
                    inputs = {key: value for key, value in inputs.items() if key != "dispatch_id"}
                    continue
                if "dispatch_id" not in inputs or not _is_ambiguous_dispatch_error(error):
                    raise
                self._logger.warning(
                    "Ambiguous dispatch failure for batch %s; checking for a created run",
                    message.batch_id,
                    batch_id=message.batch_id,
                    error_kind=type(error).__name__,
                    status_code=error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None,
                    dispatch_attempt=2 if redispatched else 1,
                )
                try:
                    run = await self._find_dispatched_run(message, inputs["dispatch_id"], created)
                except Exception as lookup_error:
                    self._logger.warning(
                        "Dispatch lookup inconclusive for batch %s; not re-dispatching: %s",
                        message.batch_id,
                        lookup_error,
                        batch_id=message.batch_id,
                    )
                    raise error from lookup_error
                if run is not None:
                    self._logger.info(
                        "Batch %s adopted run %s",
                        message.batch_id,
                        run.id,
                        batch_id=message.batch_id,
                        run_id=run.id,
                    )
                    return run.id, run.html_url
                if redispatched:
                    self._logger.warning(
                        "No matching run found after re-dispatching batch %s; no further attempts",
                        message.batch_id,
                        batch_id=message.batch_id,
                    )
                    raise
                # The workflow guard suppresses duplicate work. A late winner can still cancel the
                # tracked retry, failing the batch as it does without recovery.
                self._logger.info("Re-dispatching batch %s", message.batch_id, batch_id=message.batch_id)
                redispatched = True
            else:
                return dispatch.data.workflow_run_id, dispatch.data.html_url

    async def _find_dispatched_run(self, message: TestBatch, dispatch_id: str, created: str) -> WorkflowRun | None:
        failed_at = monotonic()
        title = f"Test Batch [dispatch:{dispatch_id}] {message.batch_id}"
        for delay in DISPATCH_LOOKUP_DELAYS:
            await asyncio.sleep(max(0, delay - (monotonic() - failed_at)))
            seen: set[int] = set()
            matches: dict[int, WorkflowRun] = {}
            total_count: int | None = None
            unidentified_run_id: int | None = None
            async for page in self._client.list_workflow_runs(
                self._options.owner,
                self._options.repo,
                self._options.workflow_id,
                event="workflow_dispatch",
                created=created,
                per_page=100,
            ):
                total_count = max(total_count or 0, page.data.total_count)
                for run in page.data.workflow_runs:
                    if not DISPATCH_RUN_TITLE_PATTERN.fullmatch(run.display_title):
                        unidentified_run_id = run.id
                    seen.add(run.id)
                    if run.display_title == title:
                        matches[run.id] = run
            if total_count is None or total_count >= DISPATCH_LOOKUP_RUN_LIMIT or len(seen) != total_count:
                raise ValueError("Workflow run listing is truncated or incomplete")
            winner = min(
                (run for run in matches.values() if run.conclusion != "cancelled"),
                key=lambda run: run.id,
                default=None,
            )
            if winner is not None:
                self._logger.info(
                    "Dispatch lookup for batch %s found run %s",
                    message.batch_id,
                    winner.id,
                    batch_id=message.batch_id,
                    run_id=winner.id,
                    matching_runs=len(matches),
                )
                return winner
            if unidentified_run_id is not None:
                raise ValueError(f"Run {unidentified_run_id} lacks a dispatch identity in its title")
            self._logger.info(
                "Dispatch lookup for batch %s found no viable matching run after %s seconds",
                message.batch_id,
                round(monotonic() - failed_at, 1),
                batch_id=message.batch_id,
            )
        return None

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
        jobs = await self._reconcile_final_jobs(run_id, message, jobs)
        batch_jobs = BatchJobResult.correlate(message.job_list, jobs, artifact_dirs)
        status = batch_status(conclusion, jobs)
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

    def _report_job_activity(self, batch: TestBatch, known_jobs: Mapping[str, WorkflowJob]) -> None:
        """Gauge the run's planned jobs waiting for a runner or running, totaled by platform.

        The gauges have no batch tag, so each batch's latest counts are kept and summed. Every
        platform planned so far gets a sample, so an empty queue is a zero rather than a gap.
        """
        planned = {job.name: job.platform for job in batch.job_list}
        counts = {platform: [0, 0] for platform in planned.values()}
        for workflow_job in known_jobs.values():
            if (platform := planned.get(workflow_job.name)) is None:
                continue
            if is_queued(workflow_job):
                counts[platform][0] += 1
            elif workflow_job.status is WorkflowJobStatus.IN_PROGRESS:
                counts[platform][1] += 1
        self._job_activity_by_batch[batch.batch_id] = counts
        totals: dict[PlatformName, list[int]] = {}
        for per_batch in self._job_activity_by_batch.values():
            for platform, (queued, running) in per_batch.items():
                total = totals.setdefault(platform, [0, 0])
                total[0] += queued
                total[1] += running
        for platform, (queued, running) in totals.items():
            self.monitor.metrics.gauge('jobs.queued', queued, platform=platform)
            self.monitor.metrics.gauge('jobs.running', running, platform=platform)

    def _report_queue_durations(self, batch: TestBatch, observed: Iterable[WorkflowJob]) -> None:
        """Emit each planned job's runner wait once, at its first observation of having started.

        A short job can finish between two polls, so a completed job with a real outcome also proves
        it started. Job IDs are unique per attempt, so the recorded set collapses repeated
        observations without collapsing reruns. Unusable timing is skipped rather than zeroed, so a
        later listing that carries valid timing still can.
        """
        planned = {job.name: job for job in batch.job_list}
        for workflow_job in observed:
            job = planned.get(workflow_job.name)
            if (
                job is None
                or workflow_job.id in self._queue_durations_reported
                or not has_started_running(workflow_job)
            ):
                continue
            duration = workflow_job.queue_duration_seconds
            if duration is None:
                continue
            self._queue_durations_reported.add(workflow_job.id)
            self.monitor.metrics.distribution('job.queue.duration', duration, **job_fields(job))

    def _report_finished_jobs(self, batch: TestBatch, observed: Iterable[WorkflowJob]) -> None:
        """Report each planned job's duration and completion once per GitHub job ID, at the first listing
        showing it completed.

        Unusable timing is not retried on a later listing.
        """
        planned = {job.name: job for job in batch.job_list}
        for workflow_job in observed:
            job = planned.get(workflow_job.name)
            if (
                job is None
                or workflow_job.status is not WorkflowJobStatus.COMPLETED
                or workflow_job.id in self._finished_jobs_reported
            ):
                continue
            self._finished_jobs_reported.add(workflow_job.id)
            fields = job_fields(job, workflow_job)
            duration = fields.get('job_duration_seconds')
            if duration is not None:
                self.monitor.metrics.distribution('job.duration', duration, **fields)
            status = job_status(workflow_job)
            log = (
                self._logger.info
                if status in (Status.SUCCESS, Status.SKIPPED, Status.CANCELLED)
                else self._logger.warning
            )
            summary = status.value if duration is None else f"{status.value} in {duration:g}s"
            log("Job %s completed: %s", job.name, summary, **fields)

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
            with self._metrics.operation(Operation.FETCH_WORKFLOW) as op:
                try:
                    run = await self._client.get_workflow_run(
                        self._options.owner, self._options.repo, run_id, retry=SAFE_RETRY_WITH_404
                    )
                except ValidationError as error:
                    raise self._response_failure(
                        op, "polling workflow status", message.batch_id, run_id, error
                    ) from error
                except Exception:
                    op.fail("Failed to fetch workflow run %s for batch %s", run_id, message.batch_id)
                    raise
            completed = run.data.is_completed
            # Shutdown must not try to cancel a completed run while its artifacts are still being collected.
            if completed:
                self._runs_in_flight.pop(message.batch_id, None)
                if (duration := run.data.duration_seconds) is not None:
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
            # A completed workflow has nothing queued or running, whatever a failed or lagging final
            # listing left in `known_jobs`, and this is the batch's last sample.
            self._report_job_activity(message, {} if completed else known_jobs)
            self._report_queue_durations(message, known_jobs.values())
            self._report_finished_jobs(message, known_jobs.values())
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
            status=batch_status(run.conclusion, known_jobs.values()) if run.is_completed else None,
            sequence=sequence,
            jobs=tuple(known_jobs.values()),
        )
        self.submit_message(progress)
        return progress

    async def _refresh_jobs(self, run_id: int, known_jobs: dict[str, WorkflowJob], batch_id: str, action: str) -> None:
        # A failed or incomplete listing must not remove jobs we already know about.
        for job in await self._list_jobs(run_id, batch_id, action):
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
        self, run_id: int, batch: TestBatch, observed_jobs: list[WorkflowJob]
    ) -> list[WorkflowJob]:
        known_jobs = {job.name: job for job in observed_jobs}
        # The jobs response may lag behind the workflow status. Refresh it after downloading artifacts.
        await self._refresh_jobs(run_id, known_jobs, batch.batch_id, "reconciling final workflow jobs")
        # The listing can lag the run, so a job may first be seen started or finished here.
        self._report_queue_durations(batch, known_jobs.values())
        self._report_finished_jobs(batch, known_jobs.values())
        # The run is over, so a job not seen COMPLETED is a stale observation. The gatherer decides
        # what that means.
        return list(known_jobs.values())

    async def _list_jobs(self, run_id: int, batch_id: str, action: str) -> list[WorkflowJob]:
        """Fetch the run's jobs. If a later page fails, keep the jobs already fetched."""
        jobs: list[WorkflowJob] = []
        with self._metrics.operation(Operation.REFRESH_JOBS) as op:
            try:
                async for page in self._client.list_workflow_jobs(
                    self._options.owner, self._options.repo, run_id, per_page=100, retry=SAFE_RETRY_WITH_404
                ):
                    jobs.extend(page.data.jobs)
            except ValidationError as error:
                raise self._response_failure(op, action, batch_id, run_id, error) from error
            except Exception:
                op.fail("Failed to list workflow jobs", exc_info=True)
        return jobs

    def _build_inputs(self, message: TestBatch) -> dict[str, str]:
        run = self._options.run_fields
        inputs = {
            "dispatch_id": uuid4().hex,
            "batch_id": message.batch_id,
            "checkout_sha": str(run["checkout_sha"]),
            # Keys the workflow's cancellation group; see `ResolvedRun.concurrency_key`.
            "concurrency_key": self._options.concurrency_key,
            # The batch is dispatched at the default branch, so its own context describes master.
            # These two say which commit the results belong to, for CI Visibility and the check run.
            "head_sha": str(run["head_sha"]),
            "context": str(run["context"]),
            # The batch withholds every credential when this is true, so it is sent on every dispatch
            # rather than only when set: an absent input would default the workflow to trusting it.
            "is_fork": str(run["is_fork"]).lower(),
            "integrations": json.dumps(message.integrations),
            "job_list": encode_job_list([self._job_input(message, job) for job in message.job_list]),
        }
        # Exactly one of these is set on the run, so the batch is told which ref its results belong
        # to without having to guess from the other.
        if run["head_branch"] is not None:
            inputs["head_branch"] = str(run["head_branch"])
        if run["head_tag"] is not None:
            inputs["head_tag"] = str(run["head_tag"])
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
        # Listed without a usable download: the operation still needs its one failure record.
        unavailable: list[str] = []
        with self._metrics.operation(Operation.COLLECT_ARTIFACTS) as op:
            listing_failed = False
            try:
                async for page in self._artifact_client.list_workflow_run_artifacts(
                    self._options.owner, self._options.repo, run_id, per_page=100
                ):
                    for artifact in page.data.artifacts:
                        url = self._artifact_download_url(artifact)
                        if url is None:
                            unavailable.append(artifact.name)
                            continue
                        target = await self._download_artifact(artifact, url)
                        if target is None:
                            failures.append((artifact.id, artifact.name))
                        else:
                            artifact_dirs[artifact.name] = target
            except ValidationError as error:
                raise self._response_failure(op, "listing workflow artifacts", batch_id, run_id, error) from error
            except Exception:
                op.fail("Failed to list workflow run artifacts", exc_info=True)
                listing_failed = True
            if failures:
                op.fail(
                    "Failed to download %s %s for workflow run %s",
                    len(failures),
                    "artifact" if len(failures) == 1 else "artifacts",
                    run_id,
                    failure_count=len(failures),
                    failed_artifacts=failures,
                )
            elif unavailable and not listing_failed:
                # A failed listing already carries the operation's warning.
                op.fail(
                    "Skipped %s unavailable %s for workflow run %s (expired or without a download URL)",
                    len(unavailable),
                    "artifact" if len(unavailable) == 1 else "artifacts",
                    run_id,
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
