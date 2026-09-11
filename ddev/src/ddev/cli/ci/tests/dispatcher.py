# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The Dispatcher: the event bus that runs a batching plan and reports the result."""

from __future__ import annotations

import asyncio
import logging
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

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
from ddev.monitoring.context import MonitorContext
from ddev.monitoring.runtime import MonitoringRuntime
from ddev.utils.github_actions import write_step_summary
from ddev.utils.rate_limiting import RelaxedRateLimits

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.progress import DispatcherProgress
    from ddev.utils.github_async import AsyncGitHubClient

logger = logging.getLogger(__name__)

# A cancelled job gets SIGINT, SIGTERM about 7.5s later, then a hard kill about 2.5s after that, so a
# cancelled run abandons its pacing: the budget it was rationing outlives the process.
CANCELLED_RATE_LIMITS = RelaxedRateLimits(max_wait_seconds=2.0, max_rate=10_000.0)


@dataclass(frozen=True)
class DispatcherContext:
    """The run being tested. `build_dispatcher` consumes part of it; the rest describes the run
    for the plan header and for the monitoring run context (see `run_fields`).

    `base_sha` and `checkout_sha` are deliberately separate: a pull request is tested at the merge
    commit (`refs/pull/<n>/merge`) but its checks belong to the head commit. Outside a pull request
    the two are the same.
    """

    owner: str
    repo: str
    checkout_sha: str
    base_sha: str
    branch: str
    workflow: str
    workflow_ref: str
    target_branch: str | None = None
    pr_number: int | None = None
    tags: tuple[str, ...] = ()
    pytest_args: str = ''
    is_fork: bool = False


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


def tag_fields(tags: tuple[str, ...]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for tag in tags:
        key, _, value = tag.partition(':')
        if key:
            fields[key] = value
    return fields


PROTECTED_RUN_FIELDS = frozenset({'repo', 'branch', 'commit', 'context', 'pr_number', 'target-branch'})


def run_fields(context: DispatcherContext) -> dict[str, Any]:
    """Resolved identity wins; non-PR context uses the caller's tag or defaults to master."""
    fields = tag_fields(context.tags)
    fields.update(
        {
            # The head revision the run reports on. `checkout_sha` is deliberately not used: for a
            # pull request it is a merge ref, not a SHA.
            'commit': context.base_sha,
            'branch': context.branch,
            'pr_number': context.pr_number,
            'target-branch': context.target_branch,
            'repo': f'{context.owner}/{context.repo}',
        }
    )
    if context.pr_number is not None:
        fields['context'] = 'pr'
    elif 'context' not in fields:
        fields['context'] = 'master'
    return fields


def message_fields(message: BaseMessage) -> dict[str, Any]:
    """Run-wide reports must not inherit the identity of the batch that triggered them."""
    match message:
        case TestBatch(batch_id=batch_id):
            return {'batch_id': batch_id}
        case BatchProgressUpdate(batch_id=batch_id, run_id=run_id) | BatchFinished(batch_id=batch_id, run_id=run_id):
            return {'batch_id': batch_id, 'run_id': run_id}
        case _:
            return {}


def message_scope(context: MonitorContext) -> MessageScope:
    def scope(message: BaseMessage) -> AbstractContextManager[None]:
        return context.scope(message_fields(message))

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
        run_logger: logging.Logger | None = None,
        monitor: ComponentMonitor | None = None,
        message_scope: MessageScope | None = None,
    ):
        super().__init__(
            run_logger or logger,
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
        if self._monitor is None:
            self._logger.info('Dispatched %s batches', len(self._batches))
        else:
            # Queued, not dispatched: the workflows start when the runner's messages are processed.
            self._monitor.logger.info('Queued planned batches', batch_count=len(self._batches))

    async def on_message_received(self, message: BaseMessage):
        self._logger.debug("Message received: %s(%s)", type(message).__name__, message.id)

    async def on_finalize(self, exception: Exception | None):
        request = self.shutdown_request
        try:
            if request is not None:
                await self._shutdown_cleanup(request)
            progress = self._gatherer.progress
            self._outcome = DispatcherOutcome(
                progress=progress,
                final_report_published=self._reporter.final_report_published,
                shutdown=request,
            )
            if self._monitor is None:
                self._logger.info(summary_line(progress, shutdown=request))
            else:
                self._monitor.logger.info(summary_line(progress, shutdown=request))
            if (body := self._reporter.latest_body) is not None:
                write_step_summary(render_run_summary(body, pr_comment_failed=self._reporter.pr_comment_failed))
        finally:
            await self._client.aclose()

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
    context: DispatcherContext,
    config: DispatcherConfig,
    token: str,
    artifacts_path: Path,
    output_path: Path,
    run_logger: logging.Logger | None = None,
    monitoring: MonitoringRuntime | None = None,
) -> Dispatcher:
    """Assemble the client, the three tasks and the Dispatcher from a plan and its run context.

    One HTTP pool is shared by every task. Artifact collection uses its own local bucket;
    all buckets share the provider's budget and pauses.

    The caller owns ``monitoring``; omitting it retains stdlib logging.
    """
    from ddev.utils.github_async import AsyncGitHubClient

    def view(name: str) -> ComponentMonitor | None:
        return monitoring.component(name) if monitoring is not None else None

    active_logger = run_logger or logger
    integrations = frozenset(integration for batch in batches for integration in batch.integrations)
    rate_limiters = RateLimiterFactory(config.github_rate_limits, active_logger)
    client = AsyncGitHubClient(token, rate_limiter=rate_limiters.get_limiter(integrations))

    runner = TaskTestRunner(
        "test-runner",
        client,
        TestRunnerOptions(
            owner=context.owner,
            repo=context.repo,
            workflow_id=context.workflow,
            ref=context.workflow_ref,
            base_sha=context.base_sha,
            checkout_sha=context.checkout_sha,
            artifacts_base_path=artifacts_path,
            branch=context.branch,
            is_fork=context.is_fork,
            poll_interval_seconds=config.poll_interval_seconds,
            pytest_args=context.pytest_args,
        ),
        artifact_client=client.with_rate_limit(rate_limiters.artifacts),
        monitor=view('test-runner'),
    )
    gatherer = TaskTestGatherer("test-gatherer", output_path, batches, monitor=view('test-gatherer'))
    reporter = TaskRunReporter(
        "run-reporter",
        client,
        RunReporterOptions(owner=context.owner, repo=context.repo, pr_number=context.pr_number),
        monitor=view('run-reporter'),
    )

    return Dispatcher(
        batches=batches,
        client=client,
        runner=runner,
        gatherer=gatherer,
        reporter=reporter,
        max_timeout=config.global_timeout_seconds,
        grace_period=config.grace_period_seconds,
        run_logger=active_logger,
        monitor=view('dispatcher'),
        message_scope=message_scope(monitoring.context) if monitoring is not None else None,
    )
