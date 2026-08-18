# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskPullRequestUpdater processor.

The updater owns exactly one comment and must never let it regress, so most of what matters here is
ordering and idempotence: create once, edit thereafter, reject anything stale. It also reports to the
run summary, which is the only surface a run without a pull request has, and the reason a failed
comment write never fails the run.
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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def summary_file(tmp_path, monkeypatch):
    """Point every test's run summary at its own file.

    Autouse on purpose: without it a test run inside GitHub Actions would append these fixtures to the
    real job summary, and tests that never mention the summary would silently exercise the no-op path.
    """
    path = tmp_path / "step-summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    return path


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


def _updater(client: FakeAsyncGitHubClient, *, pr_number: int | None = PR_NUMBER) -> TaskPullRequestUpdater:
    return TaskPullRequestUpdater(
        "pr-updater", client, PullRequestUpdaterOptions(owner=OWNER, repo=REPO, pr_number=pr_number)
    )


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("PATCH", "https://api.github.com/")
    return httpx.HTTPStatusError("boom", request=request, response=httpx.Response(status_code, request=request))


def _validation_error(*messages: str) -> httpx.HTTPStatusError:
    """A 422 shaped the way GitHub shapes one.

    A generic top-level ``message`` with the specific explanation per entry of ``errors``, whose
    ``code`` is ``custom`` — the documented shape for a validation failure that has no dedicated code.
    """
    request = httpx.Request("PATCH", "https://api.github.com/")
    payload = {
        "message": "Validation Failed",
        "errors": [
            {"resource": "IssueComment", "code": "custom", "field": "body", "message": message} for message in messages
        ],
    }
    return httpx.HTTPStatusError("boom", request=request, response=httpx.Response(422, json=payload, request=request))


def _too_long_error() -> httpx.HTTPStatusError:
    """The only 422 the minimal fallback can fix."""
    return _validation_error("body is too long (maximum is 65536 characters)")


def _spam_error() -> httpx.HTTPStatusError:
    """The other 422 GitHub documents for these endpoints, which a shorter body cannot fix."""
    return _validation_error("was flagged as spam and cannot be created")


def _auth_error(status_code: int) -> GitHubAuthenticationError:
    """What the real client raises for 401 and 403.

    ``AsyncGitHubClient._request`` converts every non-rate-limit response with one of those statuses
    into a ``GitHubAuthenticationError``, so a test that injects a bare ``HTTPStatusError`` for a 403
    is asserting a shape the updater never actually receives.
    """
    request = httpx.Request("PATCH", "https://api.github.com/")
    return GitHubAuthenticationError("boom", request=request, response=httpx.Response(status_code, request=request))


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


@pytest.mark.parametrize(
    "error",
    [
        # The status the real client produces for "you may not edit this comment". It arrives as a
        # GitHubAuthenticationError, so recovery has to see it through that type rather than through
        # the bare HTTPStatusError a hand-built 403 would give.
        pytest.param(_auth_error(403), id="403-as-the-client-raises-it"),
        pytest.param(_http_error(403), id="403-unconverted"),
        pytest.param(_http_error(404), id="404-comment-is-gone"),
    ],
)
def test_a_comment_we_cannot_edit_is_replaced_by_one_we_own(error: httpx.HTTPStatusError) -> None:
    """403 means the marker pointed at someone else's comment; 404 means it is gone.

    Neither improves on retry, and retrying until the budget ran out is what used to leave the run
    reporting nothing at all.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=77, body=f"{COMMENT_MARKER}\nnot ours")))
    client.mock_response("update_issue_comment", error, once=True)
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


def test_a_transient_failure_is_not_retried_here() -> None:
    """Retrying belongs to the GitHub client, so one retry strategy covers every caller.

    The updater used to run its own attempt loop. Two owners of the same concern is one too many, and
    the next snapshot supersedes a lost intermediate revision anyway.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_a_create_that_failed_after_landing_does_not_produce_a_duplicate() -> None:
    """The nastiest case: GitHub created the comment, then the response was lost.

    The next revision would post a second comment if it trusted the failure. The marker lookup is what
    prevents that, because it re-reads the PR and finds the comment the failed call actually created.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(502), once=True)
    # First lookup: nothing on the PR yet, so the updater creates. Every lookup after it: the
    # comment that first call really did create, despite reporting failure.
    client.mock_response("list_issue_comments", _comment_page(), once=True)
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=555, body=f"{COMMENT_MARKER}\npartial")))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))
    asyncio.run(updater.process_message(_update(2)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == 555


def test_a_lost_intermediate_revision_does_not_stop_the_next_one() -> None:
    """Losing an intermediate revision is survivable — the next snapshot supersedes it."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))
    assert updater.pr_comment_failed

    asyncio.run(updater.process_message(_update(2)))

    assert len(client.calls_to("create_issue_comment")) == 2
    assert not updater.pr_comment_failed


@pytest.mark.parametrize("done", [False, True])
def test_a_rejected_token_is_reported_without_failing_the_run(
    done: bool, caplog: pytest.LogCaptureFixture, summary_file
) -> None:
    """A credentials problem is a reporting problem, and reporting never fails the run.

    It is not retried — a rejected token does not improve on a second try — and its own message is the
    fix instruction, so that message is what gets logged rather than a generic write failure.
    """
    client = FakeAsyncGitHubClient()
    error = GitHubAuthenticationError(
        "GitHub rejected the credentials",
        request=httpx.Request("POST", "https://api.github.com/"),
        response=httpx.Response(401),
    )
    client.mock_response("create_issue_comment", error)
    updater = _updater(client)

    with caplog.at_level("ERROR"):
        asyncio.run(updater.process_message(_update(1, done=done)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert "rejected the credentials" in caplog.text
    assert updater.pr_comment_failed
    # The result is not lost with the comment: it is retained, and reported on the run page.
    assert updater.latest_body is not None
    assert summary_file.exists() is done


def test_a_rejected_token_is_not_mistaken_for_a_comment_we_do_not_own() -> None:
    """Recovering a 403 must not turn a genuine credentials failure into a silent comment rewrite.

    A 401 is not a status the unusable-comment recovery acts on, and having a comment to forget does
    not change that — so no replacement comment is created for it.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=77, body=f"{COMMENT_MARKER}\nours")))
    client.mock_response("update_issue_comment", _auth_error(401))

    asyncio.run(_updater(client).process_message(_update(1)))

    assert len(client.calls_to("update_issue_comment")) == 1
    client.assert_not_called("create_issue_comment")


def test_a_token_refused_for_every_comment_gives_up_rather_than_looping() -> None:
    """A 403 on the comment we just created is not an ownership problem — the token cannot write.

    Recovery forgets the tracked comment once; the create that follows has nothing left to forget, so
    it stops there instead of forgetting and recreating until the pass cap runs out.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=77, body=f"{COMMENT_MARKER}\nours")))
    client.mock_response("update_issue_comment", _auth_error(403))
    client.mock_response("create_issue_comment", _auth_error(403))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("update_issue_comment")) == 1
    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed


def test_a_failed_final_write_reports_to_the_run_summary_instead_of_failing(summary_file) -> None:
    """The run does not fail for a comment it could not write.

    Failing here used to throw away a complete, correct set of test results because the one surface
    that was meant to show them refused the write. The run summary is the answer: the report still
    lands, with a note saying the comment could not be updated.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(4, done=True)))

    assert updater.pr_comment_failed
    summary = summary_file.read_text()
    assert summary.startswith("> [!WARNING]")
    assert "pull request comment could not be updated" in summary
    assert "10/10 jobs" in summary


# ---------------------------------------------------------------------------
# Body too long
# ---------------------------------------------------------------------------


def test_a_body_rejected_as_too_long_is_retried_once_without_detail() -> None:
    """422 is not transient: resending the same body would fail identically."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)

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
    client.mock_response("create_issue_comment", _too_long_error(), once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1)))

    calls = client.calls_to("create_issue_comment")
    assert calls[0].kwargs["body"] != calls[1].kwargs["body"]


def test_a_minimal_body_rejected_again_is_not_shrunk_a_second_time(summary_file) -> None:
    """There is nothing left to drop, so a second rejection stops rather than looping."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error())
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1, done=True)))

    assert len(client.calls_to("create_issue_comment")) == 2
    assert updater.pr_comment_failed
    assert "pull request comment could not be updated" in summary_file.read_text()


def test_a_failed_minimal_retry_on_an_intermediate_revision_does_not_raise() -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    # The lost revision does not block the next snapshot, which is written normally.
    asyncio.run(updater.process_message(_update(2)))
    assert len(client.calls_to("create_issue_comment")) == 3


@pytest.mark.parametrize("done", [False, True])
def test_a_minimal_retry_that_lands_advances_the_revision(done: bool) -> None:
    """The minimal write returns straight out of the attempt loop, past the final-revision check.

    So the final revision needs its own case: succeeding there must report the run and advance, not
    fall through to the give-up policy that a final revision would otherwise trigger.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1, done=done)))

    assert len(client.calls_to("create_issue_comment")) == 2
    # The revision advanced, so a repeat of it is rejected as stale rather than written again.
    asyncio.run(updater.process_message(_failing_update(1, done=done)))
    assert len(client.calls_to("create_issue_comment")) == 2


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(_auth_error(403), id="403-as-the-client-raises-it"),
        pytest.param(_http_error(404), id="404-comment-is-gone"),
    ],
)
def test_a_minimal_retry_also_recovers_from_a_comment_it_cannot_edit(error: httpx.HTTPStatusError) -> None:
    """The fallback is the run's last chance to report, so it recovers the way the full write does.

    Without this it gave up on a comment it was never allowed to edit, at the one point where losing
    the write means the run reported nothing at all.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=77, body=f"{COMMENT_MARKER}\nnot ours")))
    client.mock_response("update_issue_comment", _too_long_error(), once=True)
    client.mock_response("update_issue_comment", error, once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1, done=True)))

    # The oversized edit, the minimal edit it refused, then a minimal comment of our own.
    assert len(client.calls_to("update_issue_comment")) == 2
    created = client.calls_to("create_issue_comment")
    assert len(created) == 1
    assert "test_number_0" not in created[0].kwargs["body"]


def test_a_minimal_retry_refused_everywhere_is_bounded_and_still_reports(summary_file) -> None:
    """Recovery is bounded: forgetting the comment cannot loop, and the report still lands."""
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", _comment_page(IssueComment(id=77, body=f"{COMMENT_MARKER}\nnot ours")))
    client.mock_response("update_issue_comment", _too_long_error(), once=True)
    client.mock_response("update_issue_comment", _http_error(404))
    client.mock_response("create_issue_comment", _http_error(404))
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1, done=True)))

    # Bounded by MAX_WRITE_PASSES: the oversized edit, the minimal edit, the create that replaced it.
    assert len(client.calls_to("update_issue_comment")) == 2
    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed
    assert "pull request comment could not be updated" in summary_file.read_text()


# ---------------------------------------------------------------------------
# Run summary
# ---------------------------------------------------------------------------


def test_the_final_snapshot_reports_to_the_run_summary(summary_file) -> None:
    """Written on every run, so opening the workflow always shows the final result."""
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client).process_message(_update(1, done=True)))

    summary = summary_file.read_text()
    assert "Dispatcher tests" in summary
    assert "10/10 jobs" in summary
    assert "Final result" in summary
    # The marker is how the updater finds its comment; a run summary is never looked up.
    assert COMMENT_MARKER not in summary
    assert not summary.startswith("> [!WARNING]")


def test_an_intermediate_snapshot_does_not_report_to_the_run_summary(summary_file) -> None:
    """The summary is the last word on the run, so it is written once, when there is a last word."""
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))
    asyncio.run(updater.process_message(_update(2)))

    assert not summary_file.exists()


def test_a_run_without_a_pull_request_still_reports_to_the_run_summary(summary_file) -> None:
    """The whole reason the summary exists: master pushes, the nightly schedule and merge-queue runs.

    Those have no pull request, so before this the final result of a scheduled run existed only in a
    log line nobody opens.
    """
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client, pr_number=None).process_message(_update(1, done=True)))

    assert "10/10 jobs" in summary_file.read_text()
    client.assert_not_called("create_issue_comment")
    client.assert_not_called("update_issue_comment")


def test_a_run_without_a_pull_request_is_never_marked_as_a_failed_comment(summary_file) -> None:
    """There was no comment to fail, so the summary must not apologise for one."""
    updater = _updater(FakeAsyncGitHubClient(), pr_number=None)

    asyncio.run(updater.process_message(_update(1, done=True)))

    assert not updater.pr_comment_failed
    assert "could not be updated" not in summary_file.read_text()


def test_the_run_summary_survives_a_missing_environment(monkeypatch) -> None:
    """Outside GitHub Actions there is nowhere to write, which is not an error."""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY")
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client).process_message(_update(1, done=True)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_the_run_summary_is_written_once_for_a_repeated_final_revision(summary_file) -> None:
    """write_step_summary appends, so a duplicate snapshot would append a second whole report."""
    updater = _updater(FakeAsyncGitHubClient())

    asyncio.run(updater.process_message(_update(1, done=True)))
    asyncio.run(updater.process_message(_update(1, done=True)))

    assert summary_file.read_text().count("Final result") == 1


# ---------------------------------------------------------------------------
# The retained report
# ---------------------------------------------------------------------------


def test_the_newest_report_is_retained_for_the_caller() -> None:
    """The caller persists this as a workflow output, so it must track the newest snapshot."""
    updater = _updater(FakeAsyncGitHubClient())
    assert updater.latest_body is None

    asyncio.run(updater.process_message(_update(1)))
    first = updater.latest_body
    asyncio.run(updater.process_message(_update(2)))

    assert first is not None
    assert updater.latest_body is not None
    assert updater.latest_body != first
    assert "2/10 jobs" in updater.latest_body


def test_the_report_is_retained_even_when_every_write_fails() -> None:
    """This is the point of retaining it: the results survive the surface that would not take them."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1, done=True)))

    assert updater.latest_body is not None
    assert "10/10 jobs" in updater.latest_body


def test_a_stale_revision_does_not_replace_the_retained_report() -> None:
    """The retained report may only move forwards, for the same reason the comment may not."""
    updater = _updater(FakeAsyncGitHubClient())

    asyncio.run(updater.process_message(_update(5)))
    newest = updater.latest_body
    asyncio.run(updater.process_message(_update(2)))

    assert updater.latest_body == newest


def test_a_lost_write_does_not_hold_the_revision_back() -> None:
    """The guard protects the retained report too, so it advances with the report, not with the write.

    Leaving it behind on a failure would let an earlier revision still in flight overwrite a later
    one that had already been retained.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(3)))
    asyncio.run(updater.process_message(_update(3)))

    # The second delivery of revision 3 is stale, not a fresh chance at a failed write.
    assert len(client.calls_to("create_issue_comment")) == 1


# ---------------------------------------------------------------------------
# Telling one 422 from another
# ---------------------------------------------------------------------------


def test_a_validation_error_that_is_not_about_length_is_not_answered_with_a_shorter_body() -> None:
    """GitHub documents 422 for these endpoints as validation failed *or* spammed.

    Shrinking the body cannot fix a spam rejection, and trying hid the real cause behind a fallback
    that was never going to work.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _spam_error())
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed


def test_the_real_cause_of_an_unrelated_validation_error_reaches_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _spam_error())

    with caplog.at_level("ERROR"):
        asyncio.run(_updater(client).process_message(_update(1)))

    assert "PR comment write failed" in caplog.text
    assert "too long" not in caplog.text


def test_an_unreadable_validation_response_is_treated_as_too_long() -> None:
    """The safer guess. Being wrong costs one request; the other way costs the only report we had.

    A 422 with no readable body cannot be ruled out as the over-long case, and that case is the only
    one the updater can do anything about.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(422), once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1)))

    calls = client.calls_to("create_issue_comment")
    assert len(calls) == 2
    assert len(calls[1].kwargs["body"]) < len(calls[0].kwargs["body"])


def test_a_length_message_is_recognised_at_the_top_level_of_the_response() -> None:
    """Only one of the two message fields is documented to exist, so both are read."""
    request = httpx.Request("PATCH", "https://api.github.com/")
    error = httpx.HTTPStatusError(
        "boom",
        request=request,
        response=httpx.Response(
            422, json={"message": "body is too long (maximum is 65536 characters)"}, request=request
        ),
    )
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", error, once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 2


def test_a_non_validation_status_is_never_read_as_too_long() -> None:
    """A 500 whose body happens to mention length must not trigger the fallback."""
    request = httpx.Request("PATCH", "https://api.github.com/")
    error = httpx.HTTPStatusError(
        "boom", request=request, response=httpx.Response(500, json={"message": "too long"}, request=request)
    )
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", error)

    asyncio.run(_updater(client).process_message(_failing_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1
