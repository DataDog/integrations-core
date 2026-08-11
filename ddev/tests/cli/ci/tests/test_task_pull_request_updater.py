# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskPullRequestUpdater processor.

The updater owns exactly one comment and must never let it regress, so most of what matters here is
ordering and idempotence: create once, edit thereafter, reject anything stale, and treat a failed
write differently depending on whether it was the final snapshot.
"""

from __future__ import annotations

import asyncio
import re

import httpx
import pytest

from ddev.cli.ci.tests.messages import BatchJob, Platform, UpdatePRComment
from ddev.cli.ci.tests.pr_comment import COMMENT_MARKER
from ddev.cli.ci.tests.progress import (
    BatchProgress,
    DispatcherProgress,
    ExecutionState,
    JobAttemptProgress,
    JobProgress,
)
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_pull_request_updater import PullRequestUpdaterOptions, TaskPullRequestUpdater
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import IssueComment
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.github_errors import GitHubAuthenticationError
from ddev.utils.junit import JUnitCounts, JUnitReport, JUnitResult, JUnitResultKind, JUnitTestCase, JUnitTestSuite
from tests.helpers.github_async import DEFAULT_COMMENT_ID, FakeAsyncGitHubClient

OWNER = "DataDog"
REPO = "integrations-core"
PR_NUMBER = 24817


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


TOTAL_JOBS = 10


def _job(index: int, *, reported: bool) -> JobProgress:
    job = BatchJob(
        name=f"target-{index}-py3.12-linux",
        target=f"target-{index}",
        runner="ubuntu-latest",
        environment="py3.12",
        platform=Platform.LINUX,
        unit_tests=True,
        e2e_tests=False,
    )
    attempts = (
        (
            JobAttemptProgress(
                attempt=1,
                job_id=9,
                status=Status.SUCCESS,
                conclusion=WorkflowJobConclusion.SUCCESS,
                failed_steps=(),
                job_url="https://github.com/o/r/actions/runs/1/job/9",
                reports=(),
            ),
        )
        if reported
        else ()
    )
    return JobProgress(job=job, attempts=attempts)


def _progress(*, done: bool = False, complete: int = TOTAL_JOBS) -> DispatcherProgress:
    """A snapshot where *complete* of ``TOTAL_JOBS`` jobs have reported.

    The count is what makes one revision's rendered body differ from another's. The comment itself no
    longer prints the revision — it is internal metadata — so the tests that check which snapshot was
    written have to look at content the reader actually sees.
    """
    finished = complete == TOTAL_JOBS
    batch = BatchProgress(
        batch_id="batch-01",
        run_id=121,
        workflow_url="https://github.com/o/r/actions/runs/121",
        state=ExecutionState.FINISHED if finished else ExecutionState.RUNNING,
        status=Status.SUCCESS if finished else None,
        current_attempt=1,
        max_attempts=1,
        retries_remaining=0,
        retrying_jobs=(),
        jobs_progress=tuple(_job(index, reported=index < complete) for index in range(TOTAL_JOBS)),
    )
    return DispatcherProgress(batches=(batch,), done=done)


def _jobs_reported(body: str) -> int:
    """The completed-job count the comment shows, as a stand-in for which snapshot was rendered."""
    match = re.search(r"\*\*(\d+)/\d+ jobs\*\*", body)
    assert match is not None, body
    return int(match.group(1))


def _failing_progress(*, done: bool = False) -> DispatcherProgress:
    """A snapshot with real failure detail, so the full body is bigger than the minimal one."""
    job = BatchJob(
        name="redis-py3.12-linux",
        target="redis",
        runner="ubuntu-latest",
        environment="py3.12",
        platform=Platform.LINUX,
        unit_tests=True,
        e2e_tests=False,
    )
    cases = tuple(
        JUnitTestCase(
            classname="tests.test_check",
            name=f"test_number_{index}",
            time=0.1,
            results=(JUnitResult(kind=JUnitResultKind.FAILURE, message="boom"),),
        )
        for index in range(40)
    )
    suite = JUnitTestSuite(
        name="tests",
        reported_counts=JUnitCounts(tests=len(cases), failures=len(cases), errors=0, skipped=0),
        time=1.0,
        timestamp=None,
        hostname=None,
        test_cases=cases,
    )
    attempt = JobAttemptProgress(
        attempt=1,
        job_id=9,
        status=Status.FAILURE,
        conclusion=WorkflowJobConclusion.FAILURE,
        failed_steps=(),
        job_url="https://github.com/o/r/actions/runs/1/job/9",
        reports=(JUnitReport(name="unit", test_suites=(suite,)),),
    )
    batch = BatchProgress(
        batch_id="batch-01",
        run_id=121,
        workflow_url="https://github.com/o/r/actions/runs/121",
        state=ExecutionState.FINISHED,
        status=Status.FAILURE,
        current_attempt=1,
        max_attempts=1,
        retries_remaining=0,
        retrying_jobs=(),
        jobs_progress=(JobProgress(job=job, attempts=(attempt,)),),
    )
    return DispatcherProgress(batches=(batch,), done=done)


def _update(revision: int, *, done: bool = False) -> UpdatePRComment:
    """Revision N reports N jobs, so a rendered body identifies the snapshot it came from."""
    complete = TOTAL_JOBS if done else min(revision, TOTAL_JOBS)
    return UpdatePRComment(id=f"msg-{revision}", revision=revision, progress=_progress(done=done, complete=complete))


def _failing_update(revision: int, *, done: bool = False) -> UpdatePRComment:
    return UpdatePRComment(id=f"msg-{revision}", revision=revision, progress=_failing_progress(done=done))


def _updater(
    client: FakeAsyncGitHubClient,
    *,
    pr_number: int | None = PR_NUMBER,
    max_write_attempts: int = 3,
) -> TaskPullRequestUpdater:
    return TaskPullRequestUpdater(
        "pr-updater",
        client,
        PullRequestUpdaterOptions(owner=OWNER, repo=REPO, pr_number=pr_number, max_write_attempts=max_write_attempts),
    )


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("PATCH", "https://api.github.com/")
    return httpx.HTTPStatusError("boom", request=request, response=httpx.Response(status_code, request=request))


def _comment_page(*comments: IssueComment) -> GitHubResponse:
    return GitHubResponse.model_validate({"data": list(comments), "headers": {}})


# ---------------------------------------------------------------------------
# Create, then update
# ---------------------------------------------------------------------------


def test_first_revision_creates_the_comment_and_later_ones_edit_it() -> None:
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(0)))
    asyncio.run(updater.process_message(_update(1)))
    asyncio.run(updater.process_message(_update(2, done=True)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert len(client.calls_to("update_issue_comment")) == 2
    # Every edit targets the comment the create returned.
    for call in client.calls_to("update_issue_comment"):
        assert call.kwargs["comment_id"] == DEFAULT_COMMENT_ID
    # The comment is looked up once, not on every revision.
    assert len(client.calls_to("list_issue_comments")) == 1


def test_created_body_carries_the_marker() -> None:
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client).process_message(_update(0)))

    assert client.last_call("create_issue_comment").kwargs["body"].startswith(COMMENT_MARKER)


def test_an_existing_marked_comment_is_reused_instead_of_creating_another() -> None:
    """A re-run of Dispatcher on the same PR must edit its previous comment, not add a second one."""
    client = FakeAsyncGitHubClient()
    client.mock_response(
        "list_issue_comments",
        _comment_page(
            IssueComment(id=1, body="a human comment"),
            IssueComment(id=77, body=f"{COMMENT_MARKER}\n## previous run"),
        ),
    )

    asyncio.run(_updater(client).process_message(_update(0)))

    client.assert_not_called("create_issue_comment")
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == 77


def test_a_comment_quoting_ours_is_not_mistaken_for_it() -> None:
    """Quoting our comment copies the marker into the quote, but that copy is someone else's.

    The quote is prefixed with "> ", so anchoring the match at the start rules it out. Adopting it
    would mean every edit is refused and the run reports nothing.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response(
        "list_issue_comments",
        _comment_page(IssueComment(id=31, body=f"> {COMMENT_MARKER}\n> ## Dispatcher tests\n\nlooks wrong to me")),
    )

    asyncio.run(_updater(client).process_message(_update(0)))

    assert len(client.calls_to("create_issue_comment")) == 1
    client.assert_not_called("update_issue_comment")


@pytest.mark.parametrize("status", [403, 404])
def test_a_comment_we_cannot_edit_is_replaced_by_one_we_own(status: int) -> None:
    """403 means the marker pointed at someone else's comment; 404 means it is gone.

    Neither improves on retry, and retrying until the budget ran out is what used to leave the run
    reporting nothing at all.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=77, body=f"{COMMENT_MARKER}\nnot ours")))
    client.mock_response("update_issue_comment", _http_error(status), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    # First it tried to edit the comment it found, then it created its own.
    assert len(client.calls_to("update_issue_comment")) == 1
    assert len(client.calls_to("create_issue_comment")) == 1

    # And from then on it edits the comment it created, not the one it could not.
    asyncio.run(updater.process_message(_update(2)))
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == DEFAULT_COMMENT_ID


def test_an_unmarked_comment_is_not_mistaken_for_ours() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=1, body="Dispatcher tests · passed")))

    asyncio.run(_updater(client).process_message(_update(0)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_the_marker_is_found_on_a_later_page() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response(
        "list_issue_comments",
        [
            _comment_page(IssueComment(id=1, body="chatter")),
            _comment_page(IssueComment(id=88, body=f"{COMMENT_MARKER}\nprevious")),
        ],
    )

    asyncio.run(_updater(client).process_message(_update(0)))

    client.assert_not_called("create_issue_comment")
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == 88


# ---------------------------------------------------------------------------
# Monotonicity
# ---------------------------------------------------------------------------


def test_a_stale_revision_is_ignored() -> None:
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(2)))
    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("update_issue_comment")) == 0
    assert len(client.calls_to("create_issue_comment")) == 1
    # The comment still shows revision 2's snapshot; revision 1 never reached GitHub.
    assert _jobs_reported(client.last_call("create_issue_comment").kwargs["body"]) == 2


def test_a_duplicate_of_the_current_revision_is_ignored() -> None:
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))
    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1
    client.assert_not_called("update_issue_comment")


def test_revision_zero_is_rendered() -> None:
    """Revision 0 is the initial plan, not a sentinel; it must not be treated as already-seen."""
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client).process_message(_update(0)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_out_of_order_delivery_leaves_the_newest_revision_in_place() -> None:
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(0)))
    asyncio.run(updater.process_message(_update(3)))
    asyncio.run(updater.process_message(_update(2)))
    asyncio.run(updater.process_message(_update(1)))

    assert _jobs_reported(client.last_call("update_issue_comment").kwargs["body"]) == 3
    assert len(client.calls_to("update_issue_comment")) == 1


def test_concurrent_revisions_are_serialized() -> None:
    """Batches finish concurrently, so two updates can be in flight; the comment must not regress."""
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    async def scenario() -> None:
        await asyncio.gather(
            updater.process_message(_update(1)),
            updater.process_message(_update(2)),
            updater.process_message(_update(3)),
        )

    asyncio.run(scenario())

    bodies = [client.last_call("create_issue_comment").kwargs["body"]]
    bodies += [call.kwargs["body"] for call in client.calls_to("update_issue_comment")]
    reported = [_jobs_reported(body) for body in bodies]
    assert reported == sorted(reported)
    assert reported[-1] == 3


# ---------------------------------------------------------------------------
# No pull request to comment on
# ---------------------------------------------------------------------------


def test_no_pr_number_renders_to_the_log_and_calls_no_api(caplog: pytest.LogCaptureFixture) -> None:
    """Master pushes, the nightly cron and merge-queue runs have no PR; the graph stays the same."""
    client = FakeAsyncGitHubClient()

    with caplog.at_level("INFO"):
        asyncio.run(_updater(client, pr_number=None).process_message(_update(0, done=True)))

    client.assert_not_called("create_issue_comment")
    client.assert_not_called("update_issue_comment")
    client.assert_not_called("list_issue_comments")
    assert f"Dispatcher tests complete: {TOTAL_JOBS}/{TOTAL_JOBS} jobs" in caplog.text


def test_no_pr_number_does_not_fail_the_run_on_the_final_snapshot() -> None:
    """The done-write policy must not fire when there was never a comment to write."""
    asyncio.run(_updater(FakeAsyncGitHubClient(), pr_number=None).process_message(_update(9, done=True)))


# ---------------------------------------------------------------------------
# Write failures
# ---------------------------------------------------------------------------


def test_a_transient_failure_is_retried_and_the_revision_advances() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 2
    # The revision advanced, so a later one is accepted and an earlier one is not.
    asyncio.run(updater.process_message(_update(1)))
    client.assert_not_called("update_issue_comment")


def test_a_create_that_failed_after_landing_does_not_produce_a_duplicate() -> None:
    """The nastiest case: GitHub created the comment, then the response was lost.

    A blind retry would post a second comment. The marker lookup is what prevents that, because the
    retry re-reads the PR and finds the comment the failed call actually created.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(502), once=True)
    # First lookup: nothing on the PR yet, so the updater creates. Every lookup after it: the
    # comment that first call really did create, despite reporting failure.
    client.mock_response("list_issue_comments", _comment_page(), once=True)
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=555, body=f"{COMMENT_MARKER}\npartial")))

    asyncio.run(_updater(client).process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == 555


def test_exhausted_attempts_on_an_intermediate_revision_do_not_raise() -> None:
    """Losing an intermediate revision is survivable — the next snapshot supersedes it."""
    client = FakeAsyncGitHubClient()
    for _ in range(3):
        client.mock_response("create_issue_comment", _http_error(500), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 3
    # The revision did not advance, so the next snapshot still gets written.
    asyncio.run(updater.process_message(_update(2)))
    assert len(client.calls_to("create_issue_comment")) == 4


@pytest.mark.parametrize("done", [False, True])
def test_an_authentication_error_propagates_immediately(done: bool) -> None:
    """A rejected token does not improve on retry, and its message is the fix instruction.

    Retrying it wasted three calls and then replaced it with a generic write failure, which told the
    operator nothing about the token.
    """
    client = FakeAsyncGitHubClient()
    error = GitHubAuthenticationError(
        "GitHub rejected the credentials",
        request=httpx.Request("POST", "https://api.github.com/"),
        response=httpx.Response(401),
    )
    client.mock_response("create_issue_comment", error)

    with pytest.raises(GitHubAuthenticationError, match="rejected the credentials"):
        asyncio.run(_updater(client).process_message(_update(1, done=done)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_exhausted_attempts_on_the_final_revision_fail_the_run() -> None:
    client = FakeAsyncGitHubClient()
    for _ in range(3):
        client.mock_response("create_issue_comment", _http_error(500), once=True)

    with pytest.raises(FatalProcessingError, match="final Dispatcher PR comment"):
        asyncio.run(_updater(client).process_message(_update(4, done=True)))


# ---------------------------------------------------------------------------
# Body too long
# ---------------------------------------------------------------------------


def test_a_body_rejected_as_too_long_is_retried_once_without_detail() -> None:
    """422 is not transient: resending the same body would fail identically."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(422), once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1)))

    calls = client.calls_to("create_issue_comment")
    assert len(calls) == 2
    # The retry drops the failure detail, which is what made the body too long.
    assert "test_number_0" in calls[0].kwargs["body"]
    assert "test_number_0" not in calls[1].kwargs["body"]
    assert len(calls[1].kwargs["body"]) < len(calls[0].kwargs["body"])
    # It is still a Dispatcher comment, and still reports the totals.
    assert calls[1].kwargs["body"].startswith(COMMENT_MARKER)
    assert "**1/1 jobs**" in calls[1].kwargs["body"]


def test_the_oversized_body_is_not_resent_verbatim() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(422), once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1)))

    calls = client.calls_to("create_issue_comment")
    assert calls[0].kwargs["body"] != calls[1].kwargs["body"]


def test_a_failed_minimal_retry_on_the_final_revision_fails_the_run() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(422), once=True)
    client.mock_response("create_issue_comment", _http_error(422), once=True)

    with pytest.raises(FatalProcessingError, match="final Dispatcher PR comment"):
        asyncio.run(_updater(client).process_message(_update(1, done=True)))


def test_a_failed_minimal_retry_on_an_intermediate_revision_does_not_raise() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(422), once=True)
    client.mock_response("create_issue_comment", _http_error(422), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    # The revision did not advance, so the next snapshot is still attempted.
    asyncio.run(updater.process_message(_update(2)))
    assert len(client.calls_to("create_issue_comment")) == 3
