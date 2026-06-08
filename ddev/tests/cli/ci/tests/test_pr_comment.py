# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the PR comment formatter."""

from __future__ import annotations

from ddev.cli.ci.tests._pr_comment import COMMENT_MARKER, format_pr_comment
from ddev.cli.ci.tests.messages import FailedCheck, UpdatePRComment, WorkflowStatus


def _status(run_id: int, success: int, failed_checks: list[FailedCheck]) -> WorkflowStatus:
    return WorkflowStatus(
        url=f"https://github.com/o/r/actions/runs/{run_id}",
        id=run_id,
        success_count=success,
        failed_count=len(failed_checks),
        failed_checks=failed_checks,
    )


def test_marker_is_first_line() -> None:
    body = format_pr_comment(UpdatePRComment(id="x", done=False, workflows=[]))
    assert body.startswith(COMMENT_MARKER)


def test_running_header_when_not_done() -> None:
    body = format_pr_comment(UpdatePRComment(id="x", done=False, workflows=[_status(1, 2, [])]))
    assert "🧪 Test Dispatcher — _running_" in body
    assert "still running" in body


def test_complete_header_success_when_no_failures() -> None:
    body = format_pr_comment(UpdatePRComment(id="x", done=True, workflows=[_status(1, 3, [])]))
    assert "✅ Test Dispatcher — _complete_" in body
    assert "**3** succeeded, **0** failed." in body
    assert "Failed jobs" not in body


def test_complete_header_failure_when_failures() -> None:
    check = FailedCheck(name="ntp", url="https://github.com/o/r/actions/runs/1", environment="py3.13")
    body = format_pr_comment(UpdatePRComment(id="x", done=True, workflows=[_status(1, 1, [check])]))
    assert "❌ Test Dispatcher — _complete_" in body


def test_totals_sum_across_workflows() -> None:
    workflows = [_status(1, 2, []), _status(2, 3, [])]
    body = format_pr_comment(UpdatePRComment(id="x", done=True, workflows=workflows))
    assert "**5** succeeded, **0** failed." in body


def test_failed_jobs_grouped_by_workflow_with_step_and_tests() -> None:
    check = FailedCheck(
        name="kafka",
        url="https://github.com/o/r/actions/runs/2",
        environment="py3.13",
        error="Run unit tests",
        failed_tests=["tests.test_a::test_fail"],
    )
    body = format_pr_comment(UpdatePRComment(id="x", done=True, workflows=[_status(2, 0, [check])]))
    assert "[Workflow run](https://github.com/o/r/actions/runs/2)" in body
    assert "`kafka` · `py3.13` — Run unit tests" in body
    assert "Failed tests: `tests.test_a::test_fail`" in body


def test_timed_out_job_shows_timed_out() -> None:
    check = FailedCheck(
        name="mongo", url="https://github.com/o/r/actions/runs/3", environment="py3.13", error="timed out"
    )
    body = format_pr_comment(UpdatePRComment(id="x", done=True, workflows=[_status(3, 0, [check])]))
    assert "`mongo` · `py3.13` — timed out" in body


def test_successful_workflow_section_omitted() -> None:
    check = FailedCheck(name="kafka", url="u", environment="py3.13", error="boom")
    workflows = [_status(1, 5, []), _status(2, 0, [check])]
    body = format_pr_comment(UpdatePRComment(id="x", done=True, workflows=workflows))
    assert body.count("[Workflow run]") == 1
