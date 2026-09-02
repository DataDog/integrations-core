# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the Dispatcher: the bus that carries a plan from dispatch to published report."""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import pytest

from ddev.cli.ci.tests.dispatcher import (
    CANCELLED_RATE_LIMITS,
    Dispatcher,
    DispatcherContext,
    RunContext,
)
from ddev.cli.ci.tests.messages import BatchJob, TestBatch
from ddev.cli.ci.tests.pr_comment import CANCELLED_HEADING
from ddev.cli.ci.tests.task_run_reporter import RunReporterOptions, TaskRunReporter
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.utils.github_async.models import ArtifactsList, WorkflowJob, WorkflowJobsList, WorkflowRun
from tests.cli.ci.tests.helpers import jobs_reported, make_batch, make_job
from tests.helpers.github_async import FakeAsyncGitHubClient

# Every test here runs a Dispatcher to completion, and `on_finalize` writes the run summary. Without
# this the reports land in the real job summary whenever the suite runs inside a workflow.
pytestmark = pytest.mark.usefixtures("step_summary")

CONTEXT = DispatcherContext(
    owner="DataDog",
    repo="integrations-core",
    run_context=RunContext.PR,
    checkout_sha="refs/pull/42/merge",
    base_sha="head-sha",
    branch="a-branch",
    workflow="test-batch.yml",
    workflow_ref="master",
    target_branch="master",
    pr_number=42,
)


def build_bus(
    client: FakeAsyncGitHubClient,
    tmp_path: Path,
    batches: list[TestBatch],
    *,
    pr_number: int | None = 42,
) -> Dispatcher:
    """A Dispatcher over the three real tasks, so the subscriptions under test are production's."""
    runner = TaskTestRunner(
        "test-runner",
        client,  # type: ignore[arg-type]
        TestRunnerOptions(
            owner=CONTEXT.owner,
            repo=CONTEXT.repo,
            workflow_id=CONTEXT.workflow,
            ref=CONTEXT.workflow_ref,
            base_sha=CONTEXT.base_sha,
            checkout_sha=CONTEXT.checkout_sha,
            artifacts_base_path=tmp_path / "artifacts",
            poll_interval_seconds=0.0,
        ),
    )
    gatherer = TaskTestGatherer("test-gatherer", tmp_path / "results", batches)
    reporter = TaskRunReporter(
        "run-reporter",
        client,  # type: ignore[arg-type]
        RunReporterOptions(owner=CONTEXT.owner, repo=CONTEXT.repo, pr_number=pr_number),
    )
    return Dispatcher(
        batches=batches,
        client=client,  # type: ignore[arg-type]
        runner=runner,
        gatherer=gatherer,
        reporter=reporter,
        max_timeout=30,
        grace_period=0.2,
    )


@pytest.fixture
def client(request) -> FakeAsyncGitHubClient:
    """A fake GitHub that completes every dispatched run with *conclusion*."""
    conclusion = getattr(request, "param", "success")
    fake = FakeAsyncGitHubClient()
    fake.mock_response(
        "get_workflow_run",
        WorkflowRun(
            id=123,
            name="test-batch",
            status="completed",
            conclusion=conclusion,
            html_url="https://github.com/DataDog/integrations-core/actions/runs/123",
        ),
    )
    fake.mock_response("list_workflow_run_artifacts", ArtifactsList(total_count=0, artifacts=[]))
    return fake


def mock_job_result(fake: FakeAsyncGitHubClient, job: BatchJob, conclusion: str) -> None:
    fake.mock_response(
        "list_workflow_jobs",
        WorkflowJobsList(
            total_count=1,
            jobs=[WorkflowJob(id=1, run_id=123, name=job.name, status="completed", conclusion=conclusion)],
        ),
    )


def test_a_batch_travels_from_dispatch_to_the_pull_request_comment(client, tmp_path):
    """The wiring assertion: one batch in, and its result reaches the comment.

    It fails if any of the three subscriptions is wrong, because each message is only produced by
    the task that consumes the one before it.
    """
    job = make_job()
    mock_job_result(client, job, "success")
    dispatcher = build_bus(client, tmp_path, [make_batch(job)])

    dispatcher.run()

    dispatches = client.calls_to("create_workflow_dispatch")
    assert len(dispatches) == 1
    assert dispatches[0].kwargs["workflow_id"] == "test-batch.yml"
    assert dispatches[0].kwargs["ref"] == "master"
    assert dispatches[0].kwargs["inputs"]["batch_id"] == "batch-01"
    assert dispatches[0].kwargs["inputs"]["checkout_sha"] == "refs/pull/42/merge"

    # The plan is published before anything runs, then edited once the batch has been gathered.
    created = client.calls_to("create_issue_comment")
    edited = client.calls_to("update_issue_comment")
    assert len(created) == 1
    assert created[0].kwargs["issue_number"] == 42
    assert len(edited) == 1
    assert jobs_reported(created[0].kwargs["body"]) == 0
    assert jobs_reported(edited[0].kwargs["body"]) == 1

    outcome = dispatcher.outcome
    assert outcome is not None
    assert outcome.successful
    assert outcome.progress.done
    assert outcome.progress.passed == 1


@pytest.mark.parametrize("client", ["failure"], indirect=True)
def test_a_failed_batch_makes_the_run_unsuccessful(client, tmp_path):
    job = make_job()
    mock_job_result(client, job, "failure")
    dispatcher = build_bus(client, tmp_path, [make_batch(job)])

    dispatcher.run()

    outcome = dispatcher.outcome
    assert outcome is not None
    assert not outcome.successful
    assert outcome.progress.failed == 1


def test_the_report_is_written_to_the_run_summary(client, tmp_path, step_summary):
    """A run with no pull request has the run summary as its only report."""
    job = make_job()
    mock_job_result(client, job, "success")
    dispatcher = build_bus(client, tmp_path, [make_batch(job)], pr_number=None)

    dispatcher.run()

    client.assert_not_called("create_issue_comment")
    assert jobs_reported(step_summary.read_text(encoding="utf-8")) == 1


# Cancellation tests send a real SIGINT to their own process, which needs two things every time.
# On Windows no handler can be installed, and `os.kill` with a signal other than `CTRL_*` calls
# `TerminateProcess`, so the pytest process would die rather than the test failing. And an escaped
# `KeyboardInterrupt` aborts the session, taking every test after it. Both live here so a new
# cancellation test gets them by construction.
requires_signals = pytest.mark.skipif(sys.platform == "win32", reason="The Dispatcher only runs on Linux CI runners")


def run_cancelled_by_sigint(dispatcher: Dispatcher, client: FakeAsyncGitHubClient) -> None:
    """Run *dispatcher* to completion, signalling it once it has a dispatched run to clean up.

    The signal goes out from inside `create_check_run`, so the run's handlers are already installed
    and there is something in flight for the cleanup to find.
    """
    created_check_run = client.create_check_run

    async def cancel_once_the_check_run_exists(*args, **kwargs):
        response = await created_check_run(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGINT)
        return response

    client.create_check_run = cancel_once_the_check_run_exists  # type: ignore[method-assign]

    try:
        dispatcher.run()
    except KeyboardInterrupt:  # pragma: no cover - only if the run installed no handler
        # Reported rather than left to propagate, which would abort the whole session instead of
        # failing this test.
        pytest.fail("SIGINT reached the interpreter: the run handled no cancellation signal")


def a_run_that_never_finishes(client: FakeAsyncGitHubClient) -> None:
    """Keep every dispatched run `in_progress`, so a batch is still polling when the signal lands."""
    client.mock_response(
        "get_workflow_run",
        WorkflowRun(
            id=123,
            name="test-batch",
            status="in_progress",
            conclusion=None,
            html_url="https://github.com/DataDog/integrations-core/actions/runs/123",
        ),
    )


@requires_signals
def test_a_cancelled_run_reports_itself_and_stops_the_work_it_started(client, tmp_path, step_summary):
    """A cancelled job gets about ten seconds before it is killed, and must not go quietly.

    The two things only this process can do still happen: say so on the pull request, and cancel the
    workflow runs it started.
    """
    dispatcher = build_bus(client, tmp_path, [make_batch(make_job())])
    a_run_that_never_finishes(client)

    run_cancelled_by_sigint(dispatcher, client)

    assert dispatcher.cancelled
    # The cleanup competes with a ~10s kill using a bucket the run has been spending all along, so
    # without this it is paced for a run that still had its whole window ahead of it.
    assert client.last_call("enter_shutdown_mode").kwargs == {"rate_limits": CANCELLED_RATE_LIMITS}
    # The initial plan already created the comment, so the cancelled report edits that one.
    assert CANCELLED_HEADING in client.last_call("update_issue_comment").kwargs["body"]
    assert [call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")] == [123]
    # Each batch closes its own check run on the way out, so the cleanup does not repeat it.
    assert client.last_call("update_check_run").kwargs["conclusion"] == "cancelled"
    # The run page is rendered from the same report, so it cannot claim the run is still going.
    assert CANCELLED_HEADING.removeprefix("## ") in step_summary.read_text(encoding="utf-8")


@requires_signals
def test_a_run_still_winds_down_when_shutdown_mode_cannot_be_entered(client, tmp_path):
    """The signal handler's own failures are invisible: the loop logs them and the next signal, which
    finds the run already cancelling, returns without retrying. So the stop cannot be left downstream
    of anything that might raise, or the run waits to be killed instead of winding down.
    """
    dispatcher = build_bus(client, tmp_path, [make_batch(make_job())])
    a_run_that_never_finishes(client)
    client.mock_response("enter_shutdown_mode", RuntimeError("the limiter is not what we think it is"))

    start = time.perf_counter()
    run_cancelled_by_sigint(dispatcher, client)
    elapsed = time.perf_counter() - start

    # The bus's own timeout is 30s, so anything near it means the stop never arrived.
    assert elapsed < 5
    assert [call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")] == [123]
