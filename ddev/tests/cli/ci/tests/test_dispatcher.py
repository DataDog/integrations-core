# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the Dispatcher: the bus that carries a plan from dispatch to published report."""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import os
import signal
import sys
import time
from collections.abc import AsyncIterator
from io import StringIO
from pathlib import Path
from typing import Any

import httpx
import pytest

from ddev.cli.ci.tests import dispatcher as dispatcher_module
from ddev.cli.ci.tests import rate_limiting
from ddev.cli.ci.tests.dispatcher import (
    CANCELLED_RATE_LIMITS,
    PROTECTED_RUN_FIELDS,
    Dispatcher,
    DispatcherContext,
    build_dispatcher,
    message_fields,
    run_fields,
)
from ddev.cli.ci.tests.dispatcher_config import DispatcherConfig
from ddev.cli.ci.tests.messages import (
    BatchFinished,
    BatchJob,
    BatchProgressUpdate,
    TestBatch,
    UpdatePRComment,
)
from ddev.cli.ci.tests.pr_comment import (
    ALERT_RUNNING_NOTE,
    CANCELLED_HEADING,
    FAILED_HEADING,
    TIMED_OUT_HEADING,
)
from ddev.cli.ci.tests.progress import DispatcherProgress, ExecutionState
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_run_reporter import RunReporterOptions, TaskRunReporter
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.shutdown import ShutdownKind, ShutdownRequest
from ddev.monitoring import MonitoringRuntime, console_formatter
from ddev.utils.github_async import AsyncGitHubClient, GitHubResponse
from ddev.utils.github_async.models import (
    ArtifactsList,
    IssueComment,
    WorkflowDispatchResult,
    WorkflowJob,
    WorkflowJobsList,
    WorkflowJobStatus,
    WorkflowRun,
)
from ddev.utils.rate_limiting import BucketEvent, InstrumentedAsyncLimiter, RateLimitEvent
from tests.cli.ci.tests.helpers import invalid_response_error, jobs_reported, make_batch, make_job
from tests.helpers.github_async import DEFAULT_COMMENT_ID, DEFAULT_DISPATCH_HTML_URL, FakeAsyncGitHubClient
from tests.helpers.monitoring import RecordingJsonHandler, RecordingSink

# Every test here runs a Dispatcher to completion, and `on_finalize` writes the run summary. Without
# this the reports land in the real job summary whenever the suite runs inside a workflow.
pytestmark = pytest.mark.usefixtures("step_summary")

CONTEXT = DispatcherContext(
    owner="DataDog",
    repo="integrations-core",
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
    max_timeout: float = 30,
) -> Dispatcher:
    """A Dispatcher over the three real tasks, so the subscriptions under test are production's."""
    monitoring = MonitoringRuntime()
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
        artifact_client=client,  # type: ignore[arg-type]
        monitor=monitoring.component('test-runner'),
    )
    gatherer = TaskTestGatherer(
        "test-gatherer", tmp_path / "results", batches, monitor=monitoring.component('test-gatherer')
    )
    reporter = TaskRunReporter(
        "run-reporter",
        client,  # type: ignore[arg-type]
        RunReporterOptions(owner=CONTEXT.owner, repo=CONTEXT.repo, pr_number=pr_number),
        monitor=monitoring.component('run-reporter'),
    )
    return Dispatcher(
        batches=batches,
        client=client,  # type: ignore[arg-type]
        runner=runner,
        gatherer=gatherer,
        reporter=reporter,
        max_timeout=max_timeout,
        grace_period=0.2,
        monitor=monitoring.component('dispatcher'),
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

    # The initial plan and the final collected result both reach the same comment.
    created = client.calls_to("create_issue_comment")
    edited = client.calls_to("update_issue_comment")
    assert len(created) == 1
    assert created[0].kwargs["issue_number"] == 42
    assert edited
    assert jobs_reported(created[0].kwargs["body"]) == 0
    assert jobs_reported(edited[-1].kwargs["body"]) == 1

    outcome = dispatcher.outcome
    assert outcome is not None
    assert outcome.successful
    assert outcome.progress.done
    assert outcome.progress.passed == 1


def test_dispatcher_assembly_routes_artifact_requests_to_the_artifact_tier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    events: list[RateLimitEvent] = []
    requests: dict[str, str] = {}
    job = make_job()
    run_url = "https://github.com/DataDog/integrations-core/actions/runs/123"

    def handle(request: httpx.Request) -> httpx.Response:
        bucket = next(event for event in reversed(events) if isinstance(event, BucketEvent))
        requests[request.url.path] = bucket.name
        if request.url.path.endswith("/dispatches"):
            return httpx.Response(200, json={"workflow_run_id": 123, "run_url": str(request.url), "html_url": run_url})
        if request.url.path.endswith("/artifacts"):
            return httpx.Response(200, json={"total_count": 0, "artifacts": []})
        if request.url.path.endswith("/jobs"):
            return httpx.Response(
                200,
                json={
                    "total_count": 1,
                    "jobs": [
                        {"id": 1, "run_id": 123, "name": job.name, "status": "completed", "conclusion": "success"}
                    ],
                },
            )
        assert request.url.path == "/repos/DataDog/integrations-core/actions/runs/123"
        return httpx.Response(
            200, json={"id": 123, "status": "completed", "conclusion": "success", "html_url": run_url}
        )

    def make_client(
        token: str, *, rate_limiter: InstrumentedAsyncLimiter, logger: logging.Logger | None = None
    ) -> AsyncGitHubClient:
        return AsyncGitHubClient(token, rate_limiter=rate_limiter, logger=logger, transport=httpx.MockTransport(handle))

    monkeypatch.setattr("ddev.utils.github_async.AsyncGitHubClient", make_client)
    monkeypatch.setattr(rate_limiting, "event_logger", lambda _: events.append)
    dispatcher = build_dispatcher(
        batches=[make_batch(job)],
        context=dataclasses.replace(CONTEXT, pr_number=None),
        config=DispatcherConfig(grace_period_seconds=0.1, global_timeout_seconds=5),
        token="test-token",
        artifacts_path=tmp_path / "artifacts",
        output_path=tmp_path / "results",
        monitoring=MonitoringRuntime(),
    )

    dispatcher.run()

    assert dispatcher.outcome.progress.done
    prefix = "/repos/DataDog/integrations-core/actions/runs/123"
    assert requests[f"{prefix}/artifacts"] == "artifacts"
    assert requests[f"{prefix}/jobs"] == "default"
    assert requests[prefix] == "default"


def test_progress_reaches_the_comment_before_artifact_collection_finishes(
    client: FakeAsyncGitHubClient, tmp_path: Path
):
    job = make_job()
    mock_job_result(client, job, "success")
    dispatcher = build_bus(client, tmp_path, [make_batch(job)])
    collecting_reported = asyncio.Event()
    collection_released = False
    update_comment = client.update_issue_comment
    list_artifacts = client.list_workflow_run_artifacts

    async def record_comment(
        owner: str, repo: str, comment_id: int, body: str, **kwargs: Any
    ) -> GitHubResponse[IssueComment]:
        result = await update_comment(owner, repo, comment_id, body, **kwargs)
        if "📥 collecting artifacts" in body:
            collecting_reported.set()
        return result

    async def collect_after_reporting(*args: Any, **kwargs: Any) -> AsyncIterator[GitHubResponse[ArtifactsList]]:
        nonlocal collection_released
        async with asyncio.timeout(3):
            await collecting_reported.wait()
        collection_released = True
        async for page in list_artifacts(*args, **kwargs):
            yield page

    client.update_issue_comment = record_comment
    client.list_workflow_run_artifacts = collect_after_reporting

    dispatcher.run()

    assert collection_released
    assert dispatcher.outcome.progress.done
    assert dispatcher.outcome.final_report_published


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


def test_missing_final_job_metadata_keeps_the_run_unsuccessful(client: FakeAsyncGitHubClient, tmp_path: Path):
    job = make_job()
    client.mock_response(
        "get_workflow_run",
        WorkflowRun(id=123, status="in_progress", html_url="https://github.com/o/r/actions/runs/123"),
        once=True,
    )
    client.mock_response(
        "list_workflow_jobs",
        WorkflowJobsList(
            total_count=1,
            jobs=[WorkflowJob(id=1, run_id=123, name=job.name, status=WorkflowJobStatus.IN_PROGRESS)],
        ),
        once=True,
    )
    client.mock_response("list_workflow_jobs", RuntimeError("Final job metadata unavailable"))
    dispatcher = build_bus(client, tmp_path, [make_batch(job)])

    dispatcher.run()

    assert not dispatcher.outcome.progress.done
    assert not dispatcher.outcome.successful


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

    The signal goes out from inside `get_workflow_run`, the first call after a run is recorded in
    flight, so the run's handlers are already installed and there is something for the cleanup to
    find.
    """
    got_workflow_run = client.get_workflow_run

    async def cancel_once_a_run_is_in_flight(*args, **kwargs):
        response = await got_workflow_run(*args, **kwargs)
        os.kill(os.getpid(), signal.SIGINT)
        return response

    client.get_workflow_run = cancel_once_a_run_is_in_flight  # type: ignore[method-assign]

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
    # The run page is rendered from the same report, so it cannot claim the run is still going.
    assert CANCELLED_HEADING.removeprefix("## ") in step_summary.read_text(encoding="utf-8")

    outcome = dispatcher.outcome
    assert outcome is not None
    assert not outcome.successful
    assert outcome.shutdown is not None
    assert outcome.shutdown.kind is ShutdownKind.CANCELLED


def test_a_timed_out_run_reports_itself_and_cancels_what_it_started(
    client: FakeAsyncGitHubClient, tmp_path: Path, step_summary: Path
):
    """A timeout produces a terminal report and requests cancellation of unfinished runs."""
    dispatcher = build_bus(client, tmp_path, [make_batch(make_job())], max_timeout=0.5)
    a_run_that_never_finishes(client)

    dispatcher.run()

    outcome = dispatcher.outcome
    assert outcome is not None
    assert not outcome.successful
    assert not dispatcher.cancelled
    assert outcome.shutdown is not None
    assert outcome.shutdown.kind is ShutdownKind.TIMED_OUT
    assert len(client.calls_to("enter_shutdown_mode")) == 1
    assert client.last_call("enter_shutdown_mode").kwargs == {"rate_limits": CANCELLED_RATE_LIMITS}
    assert [call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")] == [123]
    terminal_body = client.last_call("update_issue_comment").kwargs["body"]
    assert TIMED_OUT_HEADING in terminal_body
    assert "max_timeout" in terminal_body
    assert "Dispatcher tests · in progress" not in terminal_body
    assert ALERT_RUNNING_NOTE not in terminal_body
    assert TIMED_OUT_HEADING.removeprefix("## ") in step_summary.read_text(encoding="utf-8")


def stop_from_inside_the_run(
    dispatcher: Dispatcher, client: FakeAsyncGitHubClient, *, request: ShutdownRequest
) -> None:
    """Request a shutdown once a remote run is tracked."""
    got_workflow_run = client.get_workflow_run

    async def stop_once_a_run_is_in_flight(owner: str, repo: str, run_id: int) -> GitHubResponse[WorkflowRun]:
        response = await got_workflow_run(owner, repo, run_id)
        dispatcher.request_shutdown(request)
        return response

    client.get_workflow_run = stop_once_a_run_is_in_flight  # type: ignore[method-assign]

    dispatcher.run()


def dispatched_run(run_id: int) -> WorkflowDispatchResult:
    return WorkflowDispatchResult(
        workflow_run_id=run_id,
        run_url=f"https://api.github.com/repos/o/r/actions/runs/{run_id}",
        html_url=f"https://github.com/o/r/actions/runs/{run_id}",
    )


def running_run(run_id: int) -> WorkflowRun:
    return WorkflowRun(
        id=run_id,
        name="test-batch",
        status="in_progress",
        conclusion=None,
        html_url=f"https://github.com/o/r/actions/runs/{run_id}",
    )


@pytest.mark.parametrize("shutdown_mode_fails", [False, True], ids=["shutdown-ok", "shutdown-fails"])
def test_a_fatal_response_failure_cancels_every_dispatched_run(
    client: FakeAsyncGitHubClient,
    tmp_path: Path,
    step_summary: Path,
    shutdown_mode_fails: bool,
):
    """A bad live jobs response stops polling and requests cancellation of every unfinished run."""
    client.mock_response("create_workflow_dispatch", dispatched_run(123), once=True)
    client.mock_response("create_workflow_dispatch", dispatched_run(456), once=True)
    client.mock_response("get_workflow_run", running_run(123), run_id=123)
    client.mock_response("get_workflow_run", running_run(456), run_id=456)
    client.mock_response("list_workflow_jobs", WorkflowJobsList(total_count=0, jobs=[]), run_id=123)
    client.mock_response("list_workflow_jobs", invalid_response_error(), run_id=456)
    if shutdown_mode_fails:
        client.mock_response("enter_shutdown_mode", RuntimeError("shutdown mode is broken"))
    batches = [
        make_batch(make_job()),
        make_batch(make_job("job-2"), batch_id="batch-02"),
    ]
    dispatcher = build_bus(client, tmp_path, batches)

    with pytest.raises(FatalProcessingError, match="batch-02") as exc_info:
        dispatcher.run()

    assert "run 456" in str(exc_info.value)
    assert len(client.calls_to("enter_shutdown_mode")) == 1
    assert client.last_call("enter_shutdown_mode").kwargs == {"rate_limits": CANCELLED_RATE_LIMITS}
    assert sorted(call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")) == [123, 456]
    assert not dispatcher.cancelled
    for call in client.calls_to("update_issue_comment"):
        assert CANCELLED_HEADING not in call.kwargs["body"]
    terminal_body = client.last_call("update_issue_comment").kwargs["body"]
    assert FAILED_HEADING in terminal_body
    assert "Dispatcher tests · in progress" not in terminal_body
    assert ALERT_RUNNING_NOTE not in terminal_body
    assert "listing workflow jobs (batch batch-02, run 456)" in terminal_body
    summary = step_summary.read_text(encoding="utf-8")
    assert FAILED_HEADING in summary
    assert "listing workflow jobs (batch batch-02, run 456)" in summary
    outcome = dispatcher.outcome
    assert outcome is not None
    assert not outcome.progress.done
    assert not outcome.successful


def test_a_programmatic_stop_goes_through_the_same_path_as_a_signal(
    client: FakeAsyncGitHubClient, tmp_path: Path, step_summary: Path
):
    """A programmatic stop reports and cleans up without receiving an OS signal."""
    dispatcher = build_bus(client, tmp_path, [make_batch(make_job())])
    a_run_that_never_finishes(client)

    stop_from_inside_the_run(dispatcher, client, request=ShutdownRequest.cancelled())

    assert dispatcher.cancelled
    assert client.last_call("enter_shutdown_mode").kwargs == {"rate_limits": CANCELLED_RATE_LIMITS}
    assert CANCELLED_HEADING in client.last_call("update_issue_comment").kwargs["body"]
    assert [call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")] == [123]
    assert CANCELLED_HEADING.removeprefix("## ") in step_summary.read_text(encoding="utf-8")


def test_a_comment_write_failure_does_not_prevent_remote_cancellation(
    client: FakeAsyncGitHubClient, tmp_path: Path, step_summary: Path
):
    """A failed comment write does not prevent remote cancellation or the terminal step summary."""
    dispatcher = build_bus(client, tmp_path, [make_batch(make_job())])
    a_run_that_never_finishes(client)
    for method in ("update_issue_comment", "create_issue_comment", "list_issue_comments"):
        client.mock_response(method, RuntimeError("the comment API is down"))

    stop_from_inside_the_run(dispatcher, client, request=ShutdownRequest.cancelled())

    assert [call.kwargs["run_id"] for call in client.calls_to("cancel_workflow_run")] == [123]
    assert CANCELLED_HEADING.removeprefix("## ") in step_summary.read_text(encoding="utf-8")
    outcome = dispatcher.outcome
    assert outcome is not None
    assert not outcome.successful


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


class ObservingGatherer(TaskTestGatherer):
    def process_message(self, message: BatchFinished | BatchProgressUpdate) -> None:
        self.monitor.metrics.count("observed", tags={"tag": message.batch_id})
        super().process_message(message)


@pytest.mark.parametrize(
    ('context', 'fields'),
    [
        (
            CONTEXT,
            {
                'commit': 'head-sha',
                'branch': 'a-branch',
                'context': 'pr',
                'pr_number': 42,
                'target-branch': 'master',
                'repo': 'DataDog/integrations-core',
            },
        ),
        (
            dataclasses.replace(
                CONTEXT, pr_number=None, target_branch=None, checkout_sha='a-master-sha', base_sha='a-master-sha'
            ),
            {
                'commit': 'a-master-sha',
                'branch': 'a-branch',
                'context': 'master',
                'pr_number': None,
                'target-branch': None,
                'repo': 'DataDog/integrations-core',
            },
        ),
        (
            dataclasses.replace(CONTEXT, tags=('commit:sneaky', 'team:platform')),
            {
                'commit': 'head-sha',
                'branch': 'a-branch',
                'context': 'pr',
                'pr_number': 42,
                'target-branch': 'master',
                'repo': 'DataDog/integrations-core',
                'team': 'platform',
            },
        ),
        (
            dataclasses.replace(CONTEXT, pr_number=None, tags=('context:release',)),
            {
                'commit': 'head-sha',
                'branch': 'a-branch',
                'context': 'release',
                'pr_number': None,
                'target-branch': 'master',
                'repo': 'DataDog/integrations-core',
            },
        ),
    ],
    ids=['pull-request', 'default-branch', 'caller-tags', 'caller-context'],
)
def test_run_fields(context, fields):
    assert run_fields(context) == fields


def test_message_fields_scope_the_context_of_each_message():
    batch = make_batch()
    progress = BatchProgressUpdate(
        id="progress",
        batch_id=batch.batch_id,
        run_id=123,
        workflow_url="https://example.com/run/123",
        state=ExecutionState.RUNNING,
        sequence=1,
    )
    finished = BatchFinished(
        id="finished",
        batch_id=batch.batch_id,
        status=Status.SUCCESS,
        run_id=123,
        workflow_url="https://example.com/run/123",
        artifacts_path="a-path",
    )
    report = UpdatePRComment(id="report", revision=0, progress=DispatcherProgress(batches=(), done=True))

    assert message_fields(batch) == {
        "message_type": "TestBatch",
        "message_id": batch.id,
        "batch_id": "batch-01",
        "batch_job_count": 1,
        "batch_integration_count": 1,
        "batch_integrations": ["ntp"],
    }
    assert message_fields(progress) == {
        "message_type": "BatchProgressUpdate",
        "message_id": "progress",
        "batch_id": "batch-01",
        "run_id": 123,
        "workflow_url": "https://example.com/run/123",
        "batch_state": "running",
        "workflow_conclusion": None,
    }
    assert message_fields(finished) == {
        "message_type": "BatchFinished",
        "message_id": "finished",
        "batch_id": "batch-01",
        "run_id": 123,
        "workflow_url": "https://example.com/run/123",
        "batch_job_count": 0,
        "batch_state": "finished",
        "workflow_status": "completed",
        "workflow_conclusion": "success",
        "timed_out": False,
    }
    # The aggregate report carries its own revision context, never a batch's identity.
    assert message_fields(report) == {
        "message_type": "UpdatePRComment",
        "message_id": "report",
        "revision": 0,
        "done": True,
    }


def test_the_shared_runtime_is_wired_through_build_dispatcher(client, tmp_path, monkeypatch):
    monkeypatch.setattr("ddev.utils.github_async.AsyncGitHubClient", lambda token, rate_limiter=None, **kwargs: client)
    monkeypatch.setattr(dispatcher_module, "TaskTestGatherer", ObservingGatherer)
    job = make_job()
    mock_job_result(client, job, "success")
    sink = RecordingSink()
    stream = StringIO()
    console_handler = logging.StreamHandler(stream)
    console_handler.setFormatter(console_formatter(hidden_fields=PROTECTED_RUN_FIELDS))
    monitoring = MonitoringRuntime(console_handler=console_handler, metrics_sink=sink)
    monitoring.set_run_fields(**run_fields(CONTEXT))

    dispatcher = build_dispatcher(
        batches=[make_batch(job)],
        context=CONTEXT,
        config=DispatcherConfig(grace_period_seconds=0.1, global_timeout_seconds=5),
        token="test-token",
        artifacts_path=tmp_path / "artifacts",
        output_path=tmp_path / "results",
        monitoring=monitoring,
    )

    dispatcher.run()

    assert sink.records
    for record in sink.records:
        assert record.fields["batch_id"] == record.tags["tag"]
        assert record.fields["component"] == "test-gatherer"
    queued = [line for line in stream.getvalue().splitlines() if "Queued planned batches" in line]
    assert len(queued) == 1
    assert "component=dispatcher" in queued[0]
    assert "plan_batch_count=1" in queued[0]


def test_a_monitored_run_carries_message_and_workflow_identity_per_event(client, tmp_path, monkeypatch):
    monkeypatch.setattr("ddev.utils.github_async.AsyncGitHubClient", lambda token, rate_limiter=None, **kwargs: client)
    job = make_job()
    mock_job_result(client, job, "success")
    handler = RecordingJsonHandler()
    monitoring = MonitoringRuntime(console_handler=handler)
    monitoring.set_run_fields(**run_fields(CONTEXT))

    dispatcher = build_dispatcher(
        batches=[make_batch(job)],
        context=CONTEXT,
        config=DispatcherConfig(grace_period_seconds=0.1, global_timeout_seconds=5),
        token="test-token",
        artifacts_path=tmp_path / "artifacts",
        output_path=tmp_path / "results",
        monitoring=monitoring,
    )

    dispatcher.run()
    monitoring.close()

    received = [event for event in handler.events if event["event"] == "Message received"]
    assert {event["message_type"] for event in received} >= {
        "TestBatch",
        "BatchProgressUpdate",
        "UpdatePRComment",
    }
    assert all(event["message_id"] for event in received)
    progress = next(event for event in received if event["message_type"] == "BatchProgressUpdate")
    assert progress["batch_id"] == "batch-01"
    assert progress["run_id"] == 123
    assert progress["workflow_url"] == DEFAULT_DISPATCH_HTML_URL
    assert progress["batch_state"] in {"queued", "artifact_download"}

    by_event = {event["event"]: event for event in handler.events}
    dispatched = by_event["Dispatched batch"]
    assert dispatched["batch_id"] == "batch-01"
    assert dispatched["run_id"] == 123
    assert dispatched["workflow_url"] == DEFAULT_DISPATCH_HTML_URL

    completed = by_event["Workflow completed"]
    assert completed["batch_id"] == "batch-01"
    assert completed["run_id"] == 123
    assert completed["workflow_status"] == "completed"
    assert completed["workflow_conclusion"] == "success"

    # The gatherer runs in a worker thread: its logs still carry the batch the message described.
    gathered = by_event["Gathering batch results"]
    assert gathered["batch_id"] == "batch-01"
    assert gathered["run_id"] == 123
    assert gathered["batch_job_count"] == 1

    comment = by_event["PR comment written"]
    assert comment["message_type"] == "UpdatePRComment"
    assert comment["message_id"]
    assert comment["revision"] > 0
    assert comment["done"] is True
    assert comment["comment_id"] == DEFAULT_COMMENT_ID
    assert comment["published"] is True
    assert "batch_id" not in comment
