# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the Dispatcher: the bus that carries a plan from dispatch to published report."""

from __future__ import annotations

from pathlib import Path

import pytest

from ddev.cli.ci.tests.dispatcher import Dispatcher, DispatcherContext, RunContext
from ddev.cli.ci.tests.messages import BatchJob, TestBatch
from ddev.cli.ci.tests.pr_comment import COMMENT_MARKER
from ddev.cli.ci.tests.task_pull_request_updater import PullRequestUpdaterOptions, TaskPullRequestUpdater
from ddev.cli.ci.tests.task_test_gatherer import TaskTestGatherer
from ddev.cli.ci.tests.task_test_runner import TaskTestRunner, TestRunnerOptions
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import ArtifactsList, WorkflowJob, WorkflowJobsList, WorkflowRun
from tests.cli.ci.tests.helpers import jobs_reported, make_job
from tests.helpers.github_async import FakeAsyncGitHubClient

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


def wrap(data):
    return GitHubResponse(data=data, headers={})


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
    updater = TaskPullRequestUpdater(
        "pull-request-updater",
        client,  # type: ignore[arg-type]
        PullRequestUpdaterOptions(owner=CONTEXT.owner, repo=CONTEXT.repo, pr_number=pr_number),
    )
    return Dispatcher(
        batches=batches,
        client=client,  # type: ignore[arg-type]
        runner=runner,
        gatherer=gatherer,
        updater=updater,
        max_timeout=30,
        grace_period=0.2,
    )


def batch(job: BatchJob, batch_id: str = "batch-01") -> TestBatch:
    return TestBatch(id=batch_id, batch_id=batch_id, job_list=[job], jobs_count=1, integrations=[job.target])


@pytest.fixture
def client(request) -> FakeAsyncGitHubClient:
    """A fake GitHub that completes every dispatched run with *conclusion*."""
    conclusion = getattr(request, "param", "success")
    fake = FakeAsyncGitHubClient()
    fake.mock_response(
        "get_workflow_run",
        wrap(
            WorkflowRun(
                id=123,
                name="test-batch",
                status="completed",
                conclusion=conclusion,
                html_url="https://github.com/DataDog/integrations-core/actions/runs/123",
            )
        ),
    )
    fake.mock_response("list_workflow_run_artifacts", wrap(ArtifactsList(total_count=0, artifacts=[])))
    return fake


def mock_job_result(fake: FakeAsyncGitHubClient, job: BatchJob, conclusion: str) -> None:
    fake.mock_response(
        "list_workflow_jobs",
        wrap(
            WorkflowJobsList(
                total_count=1,
                jobs=[WorkflowJob(id=1, run_id=123, name=job.name, status="completed", conclusion=conclusion)],
            )
        ),
    )


def test_a_batch_travels_from_dispatch_to_the_pull_request_comment(client, tmp_path):
    """The wiring assertion: one batch in, and its result reaches the comment.

    It fails if any of the three subscriptions is wrong, because each message is only produced by
    the task that consumes the one before it.
    """
    job = make_job()
    mock_job_result(client, job, "success")
    dispatcher = build_bus(client, tmp_path, [batch(job)])

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
    dispatcher = build_bus(client, tmp_path, [batch(job)])

    dispatcher.run()

    outcome = dispatcher.outcome
    assert outcome is not None
    assert not outcome.successful
    assert outcome.progress.failed == 1


def test_the_report_is_written_to_the_run_summary(client, tmp_path, monkeypatch):
    """A run with no pull request has the run summary as its only report."""
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    job = make_job()
    mock_job_result(client, job, "success")
    dispatcher = build_bus(client, tmp_path, [batch(job)], pr_number=None)

    dispatcher.run()

    client.assert_not_called("create_issue_comment")
    report = summary.read_text(encoding="utf-8")
    assert "Dispatcher tests" in report
    # The marker exists to find a comment; nothing looks a run summary up.
    assert COMMENT_MARKER not in report
