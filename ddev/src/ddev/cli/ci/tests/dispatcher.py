# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The Dispatcher: the event bus that runs a batching plan and reports the result."""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.messages import BatchFinished, TestBatch, UpdatePRComment
from ddev.cli.ci.tests.pr_comment import render_run_summary, summary_line
from ddev.cli.ci.tests.rate_limiting import RateLimiterFactory
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_run_reporter import RunReporterOptions, TaskRunReporter
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator
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


class RunContext(StrEnum):
    """What kind of run the Dispatcher is testing, reported as a monitoring tag."""

    PR = "pr"
    MASTER = "master"
    AGENT_TEST = "agent-test"
    RELEASE = "release"


@dataclass(frozen=True)
class DispatcherContext:
    """The run being tested. `build_dispatcher` consumes part of it; the rest describes the run
    for the plan header and, once metrics land, for their tags.

    `base_sha` and `checkout_sha` are deliberately separate: a pull request is tested at the merge
    commit (`refs/pull/<n>/merge`) but its checks belong to the head commit. Outside a pull request
    the two are the same.
    """

    owner: str
    repo: str
    run_context: RunContext
    checkout_sha: str
    base_sha: str
    branch: str
    workflow: str
    workflow_ref: str
    target_branch: str | None = None
    pr_number: int | None = None


@dataclass(frozen=True)
class DispatcherOutcome:
    """What a finished Dispatcher execution amounts to, for the caller to exit on."""

    progress: DispatcherProgress
    final_report_published: bool

    @property
    def successful(self) -> bool:
        """Whether every batch finished without failing and the final report was not lost.

        An unfinished plan is a failure: results nobody can see must not read as green. So is losing
        the final snapshot to a pull-request comment that would not take it. An intermediate comment
        failure is not, since the next snapshot supersedes it.

        A run with no pull request has nothing to lose the report to, so it passes that condition on
        arrival. `on_finalize` logs `summary_line` whatever happens, and the run summary is written
        when GitHub Actions offers one, so such a run still reports somewhere.
        """
        return (
            self.final_report_published
            and self.progress.done
            and all(batch.status is not Status.FAILURE for batch in self.progress.batches)
        )


class Dispatcher(EventBusOrchestrator):
    """Runs a batching plan to completion and publishes its result.

    The whole plan is known before the bus starts, so `on_initialize` queues the initial update and
    every batch: `TestBatch` -> runner -> `BatchFinished` -> gatherer -> `UpdatePRComment` -> reporter.
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
    ):
        super().__init__(run_logger or logger, max_timeout=max_timeout, grace_period=grace_period)
        self._batches = batches
        self._client = client
        self._runner = runner
        self._gatherer = gatherer
        self._reporter = reporter
        self._outcome: DispatcherOutcome | None = None
        self._cancelled = False

        self.register_processor(runner, [TestBatch])
        self.register_processor(gatherer, [BatchFinished])
        self.register_processor(reporter, [UpdatePRComment])

    @property
    def outcome(self) -> DispatcherOutcome | None:
        """The result of the execution, or None before `run` has finished."""
        return self._outcome

    @property
    def cancelled(self) -> bool:
        """Whether the run was cancelled from outside rather than finishing or timing out."""
        return self._cancelled

    async def on_initialize(self):
        self.submit_message(self._gatherer.build_initial_update())
        for batch in self._batches:
            self.submit_message(batch)
        self._logger.info("Dispatched %s batches", len(self._batches))

    def on_shutdown_signal(self, received: signal.Signals) -> None:
        """Record that the run was cancelled, then size what is left for the seconds it has.

        Both signals arrive on a cancelled job, seconds apart, so the second must not restart what the
        first began.
        """
        if self._cancelled:
            self._logger.info("Already cancelling; ignoring %s", received.name)
            return

        self._cancelled = True
        # Recorded and stopped before anything that can raise: this runs as a loop callback, so a
        # failure here goes to the loop's exception handler and the second signal returns early.
        super().on_shutdown_signal(received)
        self._client.enter_shutdown_mode(rate_limits=CANCELLED_RATE_LIMITS)

    async def on_message_received(self, message: BaseMessage):
        self._logger.debug("Message received: %s(%s)", type(message).__name__, message.id)

    async def on_finalize(self, exception: Exception | None):
        try:
            if self._cancelled:
                await self._report_cancellation()
            progress = self._gatherer.progress
            self._outcome = DispatcherOutcome(
                progress=progress,
                final_report_published=self._reporter.final_report_published,
            )
            self._logger.info(summary_line(progress))
            if (body := self._reporter.latest_body) is not None:
                write_step_summary(render_run_summary(body, pr_comment_failed=self._reporter.pr_comment_failed))
        finally:
            await self._client.aclose()

    async def _report_cancellation(self) -> None:
        """Say the run was cancelled, and stop the work it started.

        Concurrent because both are independent calls competing for the same few seconds, and neither
        is allowed to abandon the other: without `return_exceptions` the first failure would return
        from here while the rest were still in flight, racing the kill.

        Check runs are not closed here. Each batch closes its own on the way out, and that happens
        before this hook runs, once the bus has awaited the tasks it cancelled.
        """
        outcomes = await asyncio.gather(
            self._reporter.publish_cancelled(),
            self._runner.cancel_dispatched_runs(),
            return_exceptions=True,
        )
        # A cancellation is not a failed step, and must not be reported as one or swallowed: it is
        # returned as a value here rather than raised, so it needs picking out by hand.
        cancellation: asyncio.CancelledError | None = None
        for outcome in outcomes:
            if isinstance(outcome, asyncio.CancelledError):
                cancellation = outcome
            elif isinstance(outcome, BaseException):
                self._logger.error("Cancellation cleanup step failed: %s", outcome, exc_info=outcome)
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
) -> Dispatcher:
    """Assemble the client, the three tasks and the Dispatcher from a plan and its run context.

    One client and one rate limiter are shared by every task, so the run's request rate is bounded
    as a whole rather than per task. The limiter tier is chosen from every integration in the plan,
    which is the slowest thing the run will wait on.
    """
    from ddev.utils.github_async import AsyncGitHubClient

    active_logger = run_logger or logger
    integrations = frozenset(integration for batch in batches for integration in batch.integrations)
    rate_limiter = RateLimiterFactory(config.github_rate_limits, active_logger).get_limiter(integrations)
    client = AsyncGitHubClient(token, rate_limiter=rate_limiter)

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
            poll_interval_seconds=config.poll_interval_seconds,
        ),
    )
    gatherer = TaskTestGatherer("test-gatherer", output_path, batches)
    reporter = TaskRunReporter(
        "run-reporter",
        client,
        RunReporterOptions(owner=context.owner, repo=context.repo, pr_number=context.pr_number),
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
    )
