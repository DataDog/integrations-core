# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the status vocabulary: conclusion mapping and timeout classification."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ddev.cli.ci.tests.status import (
    TEST_JOB_TIMEOUT_MINUTES,
    Status,
    batch_status,
    conclusion_to_status,
    has_run,
    has_started_running,
    is_queued,
    job_status,
    timed_out,
)
from ddev.utils.github_async.models import WorkflowJob, WorkflowJobConclusion, WorkflowJobStatus
from tests.cli.ci.tests.helpers import RUNNER_NAME
from tests.helpers.github_async import make_workflow_job

REPO_ROOT = Path(__file__).parents[5]
TEST_BATCH_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test-batch.yml"


def _ran_for(conclusion: WorkflowJobConclusion, minutes: int, *, runner_name: str | None = RUNNER_NAME) -> WorkflowJob:
    """A completed job that spent `minutes` between its timestamps, whether or not it ran."""
    return make_workflow_job(
        conclusion=conclusion,
        runner_name=runner_name,
        started_at="2026-01-01T10:00:00Z",
        completed_at=f"2026-01-01T{10 + minutes // 60:02d}:{minutes % 60:02d}:00Z",
    )


@pytest.mark.parametrize("job_id", ["test", "test_fork"])
def test_the_workflows_test_jobs_use_the_timeout_constant(job_id: str):
    """The constant classifies timeout stops, so the workflow's own limit must not drift from it."""
    workflow = yaml.safe_load(TEST_BATCH_WORKFLOW.read_text(encoding="utf-8"))
    assert workflow["jobs"][job_id]["timeout-minutes"] == TEST_JOB_TIMEOUT_MINUTES


@pytest.mark.parametrize(
    ("conclusion", "expected"),
    [
        ("success", Status.SUCCESS),
        ("skipped", Status.SKIPPED),
        ("failure", Status.FAILURE),
        ("cancelled", Status.CANCELLED),
        ("timed_out", Status.FAILURE),
        ("action_required", Status.FAILURE),
        ("neutral", Status.FAILURE),
        (None, Status.FAILURE),
    ],
)
def test_conclusion_to_status(conclusion: str | None, expected: Status):
    result = conclusion_to_status(conclusion)
    assert result is expected
    assert isinstance(result, Status)


@pytest.mark.parametrize(
    ("status", "conclusion", "runner_name", "queued", "started", "ran"),
    [
        pytest.param(WorkflowJobStatus.QUEUED, None, None, True, False, False, id="queued"),
        pytest.param(WorkflowJobStatus.WAITING, None, None, True, False, False, id="waiting"),
        pytest.param(WorkflowJobStatus.PENDING, None, None, True, False, False, id="pending"),
        pytest.param(WorkflowJobStatus.REQUESTED, None, None, False, False, False, id="requested"),
        pytest.param(WorkflowJobStatus.IN_PROGRESS, None, RUNNER_NAME, False, True, False, id="in-progress"),
        pytest.param(
            WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.SUCCESS, RUNNER_NAME, False, True, True, id="success"
        ),
        pytest.param(
            WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.FAILURE, RUNNER_NAME, False, True, True, id="failure"
        ),
        pytest.param(
            WorkflowJobStatus.COMPLETED,
            WorkflowJobConclusion.CANCELLED,
            RUNNER_NAME,
            False,
            True,
            True,
            id="ran-then-cancelled",
        ),
        # Skipped jobs and jobs cancelled while queued were never picked up by a runner.
        pytest.param(
            WorkflowJobStatus.COMPLETED, WorkflowJobConclusion.SKIPPED, None, False, False, False, id="skipped"
        ),
        pytest.param(
            WorkflowJobStatus.COMPLETED,
            WorkflowJobConclusion.CANCELLED,
            None,
            False,
            False,
            False,
            id="cancelled-while-queued",
        ),
    ],
)
def test_a_jobs_state_on_a_runner(
    status: WorkflowJobStatus,
    conclusion: WorkflowJobConclusion | None,
    runner_name: str | None,
    queued: bool,
    started: bool,
    ran: bool,
):
    """Only a job a runner was assigned to has timing worth measuring; `requested` is not a wait."""
    job = make_workflow_job(status=status, conclusion=conclusion, runner_name=runner_name)

    assert (is_queued(job), has_started_running(job), has_run(job)) == (queued, started, ran)


@pytest.mark.parametrize(
    ("conclusion", "runner_name", "minutes", "expected_timed_out", "expected_status"),
    [
        pytest.param(
            WorkflowJobConclusion.CANCELLED,
            RUNNER_NAME,
            TEST_JOB_TIMEOUT_MINUTES,
            True,
            Status.FAILURE,
            id="ran-to-the-limit",
        ),
        pytest.param(
            WorkflowJobConclusion.CANCELLED,
            RUNNER_NAME,
            TEST_JOB_TIMEOUT_MINUTES + 1,
            True,
            Status.FAILURE,
            id="ran-past-the-limit",
        ),
        pytest.param(
            WorkflowJobConclusion.CANCELLED,
            RUNNER_NAME,
            TEST_JOB_TIMEOUT_MINUTES - 1,
            False,
            Status.CANCELLED,
            id="ran-short-of-the-limit",
        ),
        pytest.param(
            WorkflowJobConclusion.CANCELLED, None, 4 * 60, False, Status.CANCELLED, id="cancelled-while-queued"
        ),
        pytest.param(WorkflowJobConclusion.TIMED_OUT, None, 0, True, Status.FAILURE, id="concluded-timed-out"),
    ],
)
def test_job_status_from_timeout_evidence(
    conclusion: WorkflowJobConclusion,
    runner_name: str | None,
    minutes: int,
    expected_timed_out: bool,
    expected_status: Status,
):
    """GitHub reports a timeout stop as `cancelled`, so the evidence decides: a run to the limit
    is a timeout, a shorter one was cancelled, and a queued job never ran either way."""
    job = _ran_for(conclusion, minutes, runner_name=runner_name)
    assert timed_out(job) is expected_timed_out
    assert job_status(job) is expected_status


@pytest.mark.parametrize(
    ("conclusion", "timeout_stop", "expected"),
    [
        pytest.param("cancelled", False, Status.CANCELLED, id="genuine-cancellation"),
        pytest.param("cancelled", True, Status.FAILURE, id="timeout-cancellation"),
        pytest.param("failure", True, Status.FAILURE, id="failed-run"),
        pytest.param("success", False, Status.SUCCESS, id="successful-run"),
    ],
)
def test_batch_status(conclusion: str, timeout_stop: bool, expected: Status):
    """Only a detected timeout reclassifies a cancelled run; every other conclusion stands."""
    jobs = [_ran_for(WorkflowJobConclusion.CANCELLED, TEST_JOB_TIMEOUT_MINUTES)] if timeout_stop else []
    assert batch_status(conclusion, jobs) is expected
