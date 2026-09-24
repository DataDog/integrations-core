# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The Dispatcher: the event bus that runs a batching plan and reports the result."""

from __future__ import annotations

import asyncio
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.dispatcher_attributes import batch_fields, job_fields, message_fields, run_fields
from ddev.cli.ci.tests.messages import BatchFinished, BatchProgressUpdate, TestBatch, UpdatePRComment
from ddev.cli.ci.tests.pr_comment import render_run_summary, summary_line
from ddev.cli.ci.tests.rate_limiting import RateLimiterFactory
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_run_reporter import RunReporterOptions, TaskRunReporter
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator, MessageScope
from ddev.event_bus.shutdown import ShutdownKind, ShutdownRequest
from ddev.monitoring import ComponentMonitor
from ddev.monitoring.adapter import ComponentLogAdapter
from ddev.monitoring.context import MonitorContext
from ddev.monitoring.runtime import MonitoringRuntime
from ddev.utils.github_actions import get_workflow_run_url, write_step_summary
from ddev.utils.rate_limiting import RelaxedRateLimits

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ddev.cli.ci.dispatch_run import ResolvedRun
    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.progress import DispatcherProgress
    from ddev.utils.github_async import AsyncGitHubClient

# A cancelled job gets SIGINT, SIGTERM about 7.5s later, then a hard kill about 2.5s after that, so a
# cancelled run abandons its pacing: the budget it was rationing outlives the process.
CANCELLED_RATE_LIMITS = RelaxedRateLimits(max_wait_seconds=2.0, max_rate=10_000.0)


@dataclass(frozen=True)
class DispatcherOutcome:
    """What a finished Dispatcher execution amounts to, for the caller to exit on."""

    progress: DispatcherProgress
    final_report_published: bool
    shutdown: ShutdownRequest | None = None

    @property
    def successful(self) -> bool:
        """Whether all batches finished without failure and the final report was published.

        Any shutdown request makes the outcome unsuccessful.
        """
        return (
            self.shutdown is None
            and self.final_report_published
            and self.progress.done
            and all(batch.status is not Status.FAILURE for batch in self.progress.batches)
        )

    @property
    def cancelled(self) -> bool:
        """Whether the run ended by cancellation rather than by finishing or failing."""
        return self.shutdown is not None and self.shutdown.kind is ShutdownKind.CANCELLED

    @property
    def timed_out(self) -> bool:
        """Whether the run ended because its timeout elapsed."""
        return self.shutdown is not None and self.shutdown.kind is ShutdownKind.TIMED_OUT


def message_scope(context: MonitorContext, batches: Sequence[TestBatch]) -> MessageScope:
    """Scope each message against the plan, so batch-scoped events resolve one canonical batch by id."""
    planned = {batch.batch_id: batch for batch in batches}

    def scope(message: BaseMessage) -> AbstractContextManager[None]:
        fields = {
            'message_type': type(message).__name__,
            'message_id': message.id,
            **message_fields(message),
        }
        if isinstance(message, TestBatch | BatchProgressUpdate | BatchFinished):
            # Progress and results correlate on the stable batch id, so they see the same
            # canonical batch fields the dispatch did, resolved from the original plan.
            if (batch := planned.get(message.batch_id)) is not None:
                fields.update(batch_fields(batch))
        elif isinstance(message, UpdatePRComment):
            fields.update(revision=message.revision, done=message.progress.done)
        return context.scope(fields)

    return scope


class Dispatcher(EventBusOrchestrator):
    """Runs a batching plan to completion and publishes its result.

    The whole plan is known before the bus starts, so `on_initialize` queues the initial update and
    every batch: `TestBatch` -> runner -> progress/results -> gatherer -> `UpdatePRComment` -> reporter.
    """

    def __init__(
        self,
        *,
        batches: list[TestBatch],
        client: AsyncGitHubClient,
        runner: TaskTestRunner,
        gatherer: TaskTestGatherer,
        reporter: TaskRunReporter,
        max_timeout: float | None,
        grace_period: float,
        monitor: ComponentMonitor,
        message_scope: MessageScope | None = None,
    ):
        super().__init__(
            ComponentLogAdapter(monitor),
            max_timeout=max_timeout,
            grace_period=grace_period,
            message_scope=message_scope,
        )
        self._batches = batches
        self._client = client
        self._runner = runner
        self._gatherer = gatherer
        self._reporter = reporter
        self._outcome: DispatcherOutcome | None = None
        self._monitor = monitor

        self.register_processor(runner, [TestBatch])
        self.register_processor(gatherer, [BatchFinished, BatchProgressUpdate])
        self.register_processor(reporter, [UpdatePRComment])

    @property
    def outcome(self) -> DispatcherOutcome | None:
        """The result of the execution, or None before `run` has finished."""
        return self._outcome

    @property
    def cancelled(self) -> bool:
        """Whether the run was cancelled from outside rather than failing or timing out."""
        request = self.shutdown_request
        return request is not None and request.kind is ShutdownKind.CANCELLED

    def request_shutdown(self, request: ShutdownRequest) -> bool:
        """Prepare the client only when this shutdown request is accepted."""
        if not super().request_shutdown(request):
            return False
        try:
            self._client.enter_shutdown_mode(rate_limits=CANCELLED_RATE_LIMITS)
        except Exception:
            self._logger.exception("Failed to enter shutdown mode")
        return True

    async def on_initialize(self):
        self.submit_message(self._gatherer.build_initial_update())
        for batch in self._batches:
            self.submit_message(batch)
        # Queued, not dispatched: the workflows start when the runner's messages are processed.
        self._monitor.logger.info('Queued planned batches', plan_batch_count=len(self._batches))

    async def on_message_received(self, message: BaseMessage):
        self._monitor.logger.debug(
            'Message received', message_type=type(message).__name__, message_id=message.id, **message_fields(message)
        )

    async def on_finalize(self, exception: Exception | None):
        request = self.shutdown_request
        try:
            # Processors have drained; report their results even if remote cleanup fails.
            self._report_incomplete_jobs()
            if request is not None:
                await self._shutdown_cleanup(request)
            progress = self._gatherer.progress
            self._outcome = DispatcherOutcome(
                progress=progress,
                final_report_published=self._reporter.final_report_published,
                shutdown=request,
            )
            self._monitor.logger.info(summary_line(progress, shutdown=request))
            if (body := self._reporter.latest_body) is not None:
                write_step_summary(render_run_summary(body, pr_comment_failed=self._reporter.pr_comment_failed))
        finally:
            await self._client.aclose()

    def _report_incomplete_jobs(self) -> None:
        """Best-effort accounting: reporting errors must not prevent shutdown cleanup."""
        try:
            progress_by_batch = {batch.batch_id: batch for batch in self._gatherer.progress.batches}
            metrics = self._monitor.metrics
            for batch in self._batches:
                if batch.run_id is None:
                    continue
                final = progress_by_batch[batch.batch_id]
                collected = {
                    job_progress.job.name
                    for job_progress in final.jobs_progress
                    if job_progress.collected_result is not None
                }
                for job in batch.job_list:
                    metrics.count('jobs.incomplete', int(job.name not in collected), **job_fields(job))
        except Exception:
            self._logger.exception('Failed to report incomplete jobs')

    async def _shutdown_cleanup(self, request: ShutdownRequest) -> None:
        """Attempt terminal reporting and remote cancellation without either abandoning the other."""
        outcomes = await asyncio.gather(
            self._reporter.publish_shutdown(request),
            self._runner.cancel_dispatched_runs(),
            return_exceptions=True,
        )
        # A cancelled cleanup task still propagates after both tasks settle.
        cancellation: asyncio.CancelledError | None = None
        for outcome in outcomes:
            if isinstance(outcome, asyncio.CancelledError):
                cancellation = outcome
            elif isinstance(outcome, BaseException):
                self._logger.error("Shutdown cleanup step failed: %s", outcome, exc_info=outcome)
        if cancellation is not None:
            raise cancellation


def build_dispatcher(
    *,
    batches: list[TestBatch],
    run: ResolvedRun,
    config: DispatcherConfig,
    token: str,
    artifacts_path: Path,
    output_path: Path,
    monitoring: MonitoringRuntime,
    tags: Sequence[str] = (),
    pytest_args: str = '',
) -> Dispatcher:
    """Assemble the client, monitored tasks and Dispatcher from a plan and its resolved run.

    One HTTP pool is shared by every task. Artifact collection uses its own local bucket;
    all buckets share the provider's budget and pauses. The caller owns `monitoring`; each
    processor reports its own metrics through the monitor it is given.
    """
    from ddev.cli.ci.tests.github_monitor import GitHubMonitor
    from ddev.utils.github_async import AsyncGitHubClient

    client_monitor = monitoring.component('github-async')
    client_logger = ComponentLogAdapter(client_monitor)
    github_monitor = GitHubMonitor(client_monitor)
    integrations = frozenset(integration for batch in batches for integration in batch.integrations)
    rate_limiters = RateLimiterFactory(
        config.github_rate_limits, client_logger, on_event=github_monitor.rate_limit_event
    )
    client = AsyncGitHubClient(
        token,
        rate_limiter=rate_limiters.get_limiter(integrations),
        logger=client_logger,
        observer=github_monitor,
    )

    canonical_run_fields = run_fields(run, tags=tags)
    runner = TaskTestRunner(
        "test-runner",
        client,
        TestRunnerOptions(
            owner=run.owner,
            repo=run.repo,
            workflow_id=config.workflow,
            ref=config.workflow_ref,
            run_fields=canonical_run_fields,
            concurrency_key=run.concurrency_key,
            artifacts_base_path=artifacts_path,
            poll_interval_seconds=config.poll_interval_seconds,
            pytest_args=pytest_args,
            origin_run_url=get_workflow_run_url(),
            pr_number=run.pr_number,
        ),
        artifact_client=client.with_rate_limit(rate_limiters.artifacts),
        monitor=monitoring.component('test-runner'),
    )
    gatherer = TaskTestGatherer(
        "test-gatherer",
        output_path,
        batches,
        monitor=monitoring.component('test-gatherer'),
    )
    reporter = TaskRunReporter(
        "run-reporter",
        client,
        RunReporterOptions(owner=run.owner, repo=run.repo, pr_number=run.pr_number),
        monitor=monitoring.component('run-reporter'),
    )

    return Dispatcher(
        batches=batches,
        client=client,
        runner=runner,
        gatherer=gatherer,
        reporter=reporter,
        max_timeout=config.global_timeout_seconds,
        grace_period=config.grace_period_seconds,
        monitor=monitoring.component('dispatcher'),
        message_scope=message_scope(monitoring.context, batches),
    )
