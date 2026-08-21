# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""The Dispatcher: the event bus that runs a batching plan and reports the result."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.messages import BatchFinished, TestBatch, UpdatePRComment
from ddev.cli.ci.tests.pr_comment import render_run_summary, summary_line
from ddev.cli.ci.tests.rate_limiting import RateLimiterFactory
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_pull_request_updater import PullRequestUpdaterOptions, TaskPullRequestUpdater
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.event_bus.orchestrator import BaseMessage, EventBusOrchestrator
from ddev.utils.github_actions import write_step_summary

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
    from ddev.cli.ci.tests.progress import DispatcherProgress
    from ddev.utils.github_async import AsyncGitHubClient

logger = logging.getLogger(__name__)


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
        """Whether every batch finished without failing and the final report reached its reader.

        A run whose results nobody can see is not green, so an unfinished plan and an unpublished
        final report both count as failures. An intermediate comment failure does not: the next
        snapshot supersedes it.
        """
        return (
            self.final_report_published
            and self.progress.done
            and all(batch.status is not Status.FAILURE for batch in self.progress.batches)
        )


class Dispatcher(EventBusOrchestrator):
    """Runs a batching plan to completion and publishes its result.

    The whole plan is known before the bus starts, so `on_initialize` queues the initial update and
    every batch: `TestBatch` -> runner -> `BatchFinished` -> gatherer -> `UpdatePRComment` -> updater.
    """

    def __init__(
        self,
        *,
        batches: list[TestBatch],
        client: AsyncGitHubClient,
        runner: TaskTestRunner,
        gatherer: TaskTestGatherer,
        updater: TaskPullRequestUpdater,
        max_timeout: float | None,
        grace_period: float,
        run_logger: logging.Logger | None = None,
    ):
        super().__init__(run_logger or logger, max_timeout=max_timeout, grace_period=grace_period)
        self._batches = batches
        self._client = client
        self._gatherer = gatherer
        self._updater = updater
        self._outcome: DispatcherOutcome | None = None

        self.register_processor(runner, [TestBatch])
        self.register_processor(gatherer, [BatchFinished])
        self.register_processor(updater, [UpdatePRComment])

    @property
    def outcome(self) -> DispatcherOutcome | None:
        """The result of the execution, or None before `run` has finished."""
        return self._outcome

    async def on_initialize(self):
        self.submit_message(self._gatherer.build_initial_update())
        for batch in self._batches:
            self.submit_message(batch)
        self._logger.info("Dispatched %s batches", len(self._batches))

    async def on_message_received(self, message: BaseMessage):
        self._logger.debug("Message received: %s(%s)", type(message).__name__, message.id)

    async def on_finalize(self, exception: Exception | None):
        try:
            progress = self._gatherer.progress
            self._outcome = DispatcherOutcome(
                progress=progress,
                final_report_published=self._updater.final_report_published,
            )
            self._logger.info(summary_line(progress))
            if (body := self._updater.latest_body) is not None:
                write_step_summary(render_run_summary(body, pr_comment_failed=self._updater.pr_comment_failed))
        finally:
            await self._client.aclose()


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
    updater = TaskPullRequestUpdater(
        "pull-request-updater",
        client,
        PullRequestUpdaterOptions(owner=context.owner, repo=context.repo, pr_number=context.pr_number),
    )

    return Dispatcher(
        batches=batches,
        client=client,
        runner=runner,
        gatherer=gatherer,
        updater=updater,
        max_timeout=config.global_timeout_seconds,
        grace_period=config.grace_period_seconds,
        run_logger=active_logger,
    )
