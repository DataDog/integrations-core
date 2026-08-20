# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskPullRequestUpdater processor.

Mostly ordering and idempotence — create once, edit thereafter, reject anything stale — plus what a
failed write does, which is to keep the report and never fail the run.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace

import httpx
import pytest

from ddev.cli.ci.tests import pr_comment
from ddev.cli.ci.tests.messages import UpdatePRComment
from ddev.cli.ci.tests.pr_comment import COMMENT_MARKER
from ddev.cli.ci.tests.progress import JobAttemptProgress, JobProgress, ProgressError
from ddev.cli.ci.tests.status import Status
from ddev.cli.ci.tests.task_pull_request_updater import PullRequestUpdaterOptions, TaskPullRequestUpdater
from ddev.utils.github_async.models import IssueComment
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.github_errors import GitHubAuthenticationError, GitHubBodyTooLongError
from tests.cli.ci.tests.helpers import (
    TOTAL_JOBS,
    comment_page,
    failing_progress,
    jobs_reported,
    make_job,
    uniform_progress,
)
from tests.helpers.github_async import DEFAULT_COMMENT_ID, FakeAsyncGitHubClient

OWNER = "DataDog"
REPO = "integrations-core"
PR_NUMBER = 24817


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _update(revision: int, *, done: bool = False) -> UpdatePRComment:
    """Revision N reports N jobs, so a rendered body identifies the snapshot it came from."""
    complete = TOTAL_JOBS if done else min(revision, TOTAL_JOBS)
    return UpdatePRComment(
        id=f"msg-{revision}", revision=revision, progress=uniform_progress(done=done, complete=complete)
    )


def _failing_update(revision: int, *, done: bool = False) -> UpdatePRComment:
    return UpdatePRComment(id=f"msg-{revision}", revision=revision, progress=failing_progress(done=done))


def _updater(client: FakeAsyncGitHubClient, *, pr_number: int | None = PR_NUMBER) -> TaskPullRequestUpdater:
    return TaskPullRequestUpdater(
        "pr-updater", client, PullRequestUpdaterOptions(owner=OWNER, repo=REPO, pr_number=pr_number)
    )


def _marked_comment(comment_id: int = 77, note: str = "ours") -> IssueComment:
    return IssueComment(id=comment_id, body=f"{COMMENT_MARKER}\n{note}")


def _http_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("PATCH", "https://api.github.com/")
    return httpx.HTTPStatusError("boom", request=request, response=httpx.Response(status_code, request=request))


def _validation_error(*messages: str) -> httpx.HTTPStatusError:
    """A 422 shaped the way GitHub shapes one: a generic top-level message, the specifics per entry."""
    request = httpx.Request("PATCH", "https://api.github.com/")
    payload = {
        "message": "Validation Failed",
        "errors": [
            {"resource": "IssueComment", "code": "custom", "field": "body", "message": message} for message in messages
        ],
    }
    return httpx.HTTPStatusError("boom", request=request, response=httpx.Response(422, json=payload, request=request))


def _too_long_error() -> httpx.HTTPStatusError:
    """The only 422 a smaller body can fix."""
    return _validation_error("body is too long (maximum is 65536 characters)")


def _spam_error() -> httpx.HTTPStatusError:
    """The other 422 GitHub documents for these endpoints, which a shorter body cannot fix."""
    return _validation_error("was flagged as spam and cannot be created")


def _auth_error(status_code: int) -> GitHubAuthenticationError:
    """What the real client raises for 401 and 403, rather than a bare `HTTPStatusError`."""
    request = httpx.Request("PATCH", "https://api.github.com/")
    return GitHubAuthenticationError("boom", request=request, response=httpx.Response(status_code, request=request))


# ---------------------------------------------------------------------------
# Create, then update
# ---------------------------------------------------------------------------


def test_first_revision_creates_the_comment_and_later_ones_edit_it():
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


def test_created_body_carries_the_marker():
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client).process_message(_update(0)))

    assert client.last_call("create_issue_comment").kwargs["body"].startswith(COMMENT_MARKER)


@pytest.mark.parametrize(
    ("comments", "expected_comment_id"),
    [
        pytest.param((IssueComment(id=1, body="a human comment"), _marked_comment()), 77, id="marked-comment-reused"),
        pytest.param((_marked_comment(88, "previous"),), 88, id="marked-comment-on-a-later-page"),
        pytest.param((IssueComment(id=1, body="Dispatcher tests · passed"),), None, id="unmarked-comment-ignored"),
        pytest.param(
            (IssueComment(id=31, body=f"> {COMMENT_MARKER}\n> ## Dispatcher tests\n\nlooks wrong to me"),),
            None,
            id="quote-copying-the-marker-ignored",
        ),
        pytest.param((), None, id="nothing-on-the-pull-request"),
    ],
)
def test_the_comment_edited_is_the_one_the_marker_identifies(
    comments: tuple[IssueComment, ...], expected_comment_id: int | None
):
    """A re-run must edit its previous comment rather than add a second one.

    Anchoring the marker at the start of the body is what rules out a quote, since a quote prefixes it
    with "> ". ``expected_comment_id`` of ``None`` means the updater found nothing to adopt.
    """
    client = FakeAsyncGitHubClient()
    # One page per comment, so the marker is reached by paginating rather than only on the first page.
    client.mock_response("list_issue_comments", [comment_page(comment) for comment in comments] or [comment_page()])

    asyncio.run(_updater(client).process_message(_update(0)))

    if expected_comment_id is None:
        assert len(client.calls_to("create_issue_comment")) == 1
        client.assert_not_called("update_issue_comment")
    else:
        client.assert_not_called("create_issue_comment")
        assert client.last_call("update_issue_comment").kwargs["comment_id"] == expected_comment_id


@pytest.mark.parametrize(
    "error",
    [
        # The real client converts a 403 into GitHubAuthenticationError, so recovery has to see it
        # through that type and not only through the bare HTTPStatusError a hand-built 403 would give.
        pytest.param(_auth_error(403), id="403-as-the-client-raises-it"),
        pytest.param(_http_error(403), id="403-unconverted"),
        pytest.param(_http_error(404), id="404-comment-is-gone"),
    ],
)
def test_a_comment_we_cannot_edit_is_replaced_by_one_we_own(error: httpx.HTTPStatusError):
    """403 means the marker pointed at someone else's comment; 404 means it is gone.

    Neither improves on retry, so the updater writes a comment it does own instead.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", comment_page(_marked_comment(77, "not ours")))
    client.mock_response("update_issue_comment", error, once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    # First it tried to edit the comment it found, then it created its own.
    assert len(client.calls_to("update_issue_comment")) == 1
    assert len(client.calls_to("create_issue_comment")) == 1

    # And from then on it edits the comment it created, not the one it could not.
    asyncio.run(updater.process_message(_update(2)))
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == DEFAULT_COMMENT_ID


# ---------------------------------------------------------------------------
# Monotonicity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("revisions", "expected_final", "expected_edits"),
    [
        pytest.param([2, 1], 2, 0, id="a-stale-revision-is-ignored"),
        pytest.param([1, 1], 1, 0, id="a-duplicate-of-the-current-revision-is-ignored"),
        pytest.param([0, 3, 2, 1], 3, 1, id="out-of-order-delivery-keeps-the-newest"),
        pytest.param([5, 2], 5, 0, id="a-gap-in-the-sequence-is-not-a-reason-to-rewind"),
    ],
)
def test_neither_the_comment_nor_the_retained_report_goes_backwards(
    revisions: list[int], expected_final: int, expected_edits: int
):
    """Batches finish concurrently, so an early revision can arrive after a later one has landed.

    The first delivery creates and every accepted one after it edits, so the edit count is how many were
    not rejected as stale.
    """
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    for revision in revisions:
        asyncio.run(updater.process_message(_update(revision)))

    assert len(client.calls_to("update_issue_comment")) == expected_edits
    written = client.calls_to("create_issue_comment") + client.calls_to("update_issue_comment")
    assert jobs_reported(written[-1].kwargs["body"]) == expected_final
    assert updater.latest_body is not None
    assert jobs_reported(updater.latest_body) == expected_final


def test_revision_zero_is_rendered():
    """Revision 0 is the initial plan, not a sentinel; it must not be treated as already-seen."""
    client = FakeAsyncGitHubClient()

    asyncio.run(_updater(client).process_message(_update(0)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_concurrent_revisions_are_serialized():
    """Two updates can be in flight at once, and the comment must not regress between them."""
    client = FakeAsyncGitHubClient()
    updater = _updater(client)

    async def scenario():
        await asyncio.gather(
            updater.process_message(_update(1)),
            updater.process_message(_update(2)),
            updater.process_message(_update(3)),
        )

    asyncio.run(scenario())

    bodies = [client.last_call("create_issue_comment").kwargs["body"]]
    bodies += [call.kwargs["body"] for call in client.calls_to("update_issue_comment")]
    reported = [jobs_reported(body) for body in bodies]
    assert reported == sorted(reported)
    assert reported[-1] == 3


# ---------------------------------------------------------------------------
# No pull request to comment on
# ---------------------------------------------------------------------------


def test_no_pr_number_renders_to_the_log_and_calls_no_api(caplog: pytest.LogCaptureFixture):
    """Master pushes, the nightly cron and merge-queue runs have no PR; the graph stays the same."""
    client = FakeAsyncGitHubClient()

    with caplog.at_level("INFO"):
        asyncio.run(_updater(client, pr_number=None).process_message(_update(0, done=True)))

    client.assert_not_called("create_issue_comment")
    client.assert_not_called("update_issue_comment")
    client.assert_not_called("list_issue_comments")
    assert f"Dispatcher tests complete: {TOTAL_JOBS}/{TOTAL_JOBS} jobs" in caplog.text


def test_a_run_without_a_pull_request_still_retains_its_report():
    """There was no comment to fail, so the report is kept and nothing is marked as failed."""
    updater = _updater(FakeAsyncGitHubClient(), pr_number=None)

    asyncio.run(updater.process_message(_update(1, done=True)))

    assert not updater.pr_comment_failed
    assert updater.latest_body is not None
    assert jobs_reported(updater.latest_body) == TOTAL_JOBS


# ---------------------------------------------------------------------------
# Write failures
# ---------------------------------------------------------------------------


def test_a_transient_failure_is_not_retried_here():
    """Retrying is the GitHub client's job, so the updater makes exactly one call."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1


def test_a_create_that_failed_after_landing_does_not_produce_a_duplicate():
    """The nastiest case: GitHub created the comment, then the response was lost.

    The marker lookup is what stops the next revision posting a second one, because it re-reads the PR
    and finds the comment the failed call really did create.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(502), once=True)
    # First lookup: nothing on the PR yet, so the updater creates. Every lookup after it: the comment
    # that first call really did create, despite reporting failure.
    client.mock_response("list_issue_comments", comment_page(), once=True)
    client.mock_response("list_issue_comments", comment_page(_marked_comment(555, "partial")))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))
    asyncio.run(updater.process_message(_update(2)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert client.last_call("update_issue_comment").kwargs["comment_id"] == 555


def test_a_lost_intermediate_revision_does_not_stop_the_next_one():
    """Losing an intermediate revision is survivable — the next snapshot supersedes it."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))
    assert updater.pr_comment_failed

    asyncio.run(updater.process_message(_update(2)))

    assert len(client.calls_to("create_issue_comment")) == 2
    assert not updater.pr_comment_failed


def test_a_failed_write_keeps_the_report_rather_than_losing_it():
    """The point of retaining the report: the results survive the surface that would not take them."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(4, done=True)))

    assert updater.pr_comment_failed
    assert updater.latest_body is not None
    assert jobs_reported(updater.latest_body) == TOTAL_JOBS


def test_a_rejected_token_is_reported_without_failing_the_run(caplog: pytest.LogCaptureFixture):
    """A credentials problem is a reporting problem, and reporting never fails the run.

    Its own message is the fix instruction, so that is what gets logged rather than a generic failure.
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
        asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert "rejected the credentials" in caplog.text
    assert updater.pr_comment_failed
    assert updater.latest_body is not None


def test_a_rejected_token_is_not_mistaken_for_a_comment_we_do_not_own():
    """A 401 is not a status the unusable-comment recovery acts on, so no replacement is created."""
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", comment_page(_marked_comment()))
    client.mock_response("update_issue_comment", _auth_error(401))

    asyncio.run(_updater(client).process_message(_update(1)))

    assert len(client.calls_to("update_issue_comment")) == 1
    client.assert_not_called("create_issue_comment")


def test_a_token_refused_for_every_comment_gives_up_rather_than_looping():
    """A 403 on the comment we just created is not an ownership problem — the token cannot write.

    Recovery forgets the comment once; the create that follows has nothing left to forget, so it stops
    rather than recreating until the pass cap runs out.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", comment_page(_marked_comment()))
    client.mock_response("update_issue_comment", _auth_error(403))
    client.mock_response("create_issue_comment", _auth_error(403))
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1)))

    assert len(client.calls_to("update_issue_comment")) == 1
    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed


# ---------------------------------------------------------------------------
# Body too long
# ---------------------------------------------------------------------------


def test_a_body_rejected_as_too_long_is_resent_without_detail():
    """422 is not transient: resending the same body would fail identically."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1)))

    calls = client.calls_to("create_issue_comment")
    assert len(calls) == 2
    # The retry drops the failure detail, which is what made the body too long.
    assert "test_number_0" in calls[0].kwargs["body"]
    assert "test_number_0" not in calls[1].kwargs["body"]
    assert len(calls[1].kwargs["body"]) < len(calls[0].kwargs["body"])
    # It is still a Dispatcher comment, and still reports the totals.
    assert calls[1].kwargs["body"].startswith(COMMENT_MARKER)
    assert "**1/1 jobs**" in calls[1].kwargs["body"]

    # And the passes revision 1 spent shrinking do not come out of revision 2's budget: it gets the
    # full ladder of its own rather than inheriting a spent one.
    client.mock_response("update_issue_comment", _too_long_error(), once=True)
    asyncio.run(updater.process_message(_failing_update(2)))
    assert len(client.calls_to("update_issue_comment")) == 2


def test_the_last_tier_rejected_again_stops_rather_than_looping():
    """Once the smallest tier is refused there is nothing left to drop, so the ladder ends."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error())
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1, done=True)))

    # The full body, then the smallest tier. No third attempt, and no loop.
    assert len(client.calls_to("create_issue_comment")) == 2
    assert updater.pr_comment_failed


def test_a_snapshot_with_nothing_to_drop_is_not_resent():
    """A passing run has nothing to shed, so every tier renders the same body.

    Resending one GitHub just refused would spend a request to learn nothing, so the ladder stops.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error())
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(1, done=True)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed


def test_a_write_that_lands_on_a_smaller_tier_still_advances_the_revision():
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 2
    # The revision advanced, so a repeat of it is rejected as stale rather than written again.
    asyncio.run(updater.process_message(_failing_update(1)))
    assert len(client.calls_to("create_issue_comment")) == 2


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(_auth_error(403), id="403-as-the-client-raises-it"),
        pytest.param(_http_error(404), id="404-comment-is-gone"),
    ],
)
def test_a_smaller_tier_also_recovers_from_a_comment_it_cannot_edit(error: httpx.HTTPStatusError):
    """Shrinking and recovering compose: a smaller body still goes to a comment we are allowed to edit."""
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", comment_page(_marked_comment(77, "not ours")))
    client.mock_response("update_issue_comment", _too_long_error(), once=True)
    client.mock_response("update_issue_comment", error, once=True)

    asyncio.run(_updater(client).process_message(_failing_update(1, done=True)))

    # The oversized edit, the minimal edit it refused, then a minimal comment of our own.
    assert len(client.calls_to("update_issue_comment")) == 2
    created = client.calls_to("create_issue_comment")
    assert len(created) == 1
    assert "test_number_0" not in created[0].kwargs["body"]


def test_a_smaller_tier_refused_everywhere_is_bounded_and_still_reports():
    """Recovery is bounded: forgetting the comment cannot loop, and the report is still kept."""
    client = FakeAsyncGitHubClient()
    client.mock_response("list_issue_comments", comment_page(_marked_comment(77, "not ours")))
    client.mock_response("update_issue_comment", _too_long_error(), once=True)
    client.mock_response("update_issue_comment", _http_error(404))
    client.mock_response("create_issue_comment", _http_error(404))
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1, done=True)))

    # Bounded by MAX_WRITE_PASSES: the oversized edit, the minimal edit, the create that replaced it.
    assert len(client.calls_to("update_issue_comment")) == 2
    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed
    assert updater.latest_body is not None


# ---------------------------------------------------------------------------
# The retained report
# ---------------------------------------------------------------------------


def test_the_newest_report_is_retained_for_the_caller():
    """The orchestrator publishes this on shutdown, so it must track the newest snapshot."""
    updater = _updater(FakeAsyncGitHubClient())
    assert updater.latest_body is None

    asyncio.run(updater.process_message(_update(1)))
    first = updater.latest_body
    asyncio.run(updater.process_message(_update(2)))

    assert first is not None
    assert updater.latest_body is not None
    assert updater.latest_body != first
    assert jobs_reported(updater.latest_body) == 2


def test_a_lost_write_does_not_hold_the_revision_back():
    """The revision advances with the retained report, not with the write.

    Otherwise an earlier revision still in flight could overwrite a later one already retained.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _http_error(500), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_update(3)))
    asyncio.run(updater.process_message(_update(3)))

    # The second delivery of revision 3 is stale, not a fresh chance at a failed write.
    assert len(client.calls_to("create_issue_comment")) == 1


# ---------------------------------------------------------------------------
# Reacting to a rejection that shrinking cannot fix
#
# Classifying a 422 is the client's job and is tested there. What belongs here is what the updater does
# with the result: walk the ladder for a length problem, surface anything else.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        # GitHub documents 422 for these endpoints as validation failed *or* spammed, and a shorter
        # body cannot fix a spam rejection.
        pytest.param(_spam_error(), id="422-not-about-length"),
        # A 500 whose body happens to mention length is not a validation failure at all.
        pytest.param(
            httpx.HTTPStatusError(
                "boom",
                request=httpx.Request("PATCH", "https://api.github.com/"),
                response=httpx.Response(500, json={"message": "too long"}),
            ),
            id="500-mentioning-length",
        ),
    ],
)
def test_a_rejection_shrinking_cannot_fix_is_not_answered_with_a_shorter_body(error: httpx.HTTPStatusError):
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", error)
    updater = _updater(client)

    asyncio.run(updater.process_message(_failing_update(1)))

    assert len(client.calls_to("create_issue_comment")) == 1
    assert updater.pr_comment_failed


def test_the_real_cause_of_an_unrelated_validation_error_reaches_the_log(caplog: pytest.LogCaptureFixture):
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _spam_error())

    with caplog.at_level("ERROR"):
        asyncio.run(_updater(client).process_message(_update(1)))

    assert "PR comment write failed" in caplog.text
    assert "too long" not in caplog.text


# ---------------------------------------------------------------------------
# The tier ladder
# ---------------------------------------------------------------------------


def _tiered_update(revision: int, *, done: bool = False) -> UpdatePRComment:
    """A snapshot with failures *and* an unavailable result, so all three tiers differ."""
    progress = failing_progress(done=done)
    unavailable = JobProgress(
        job=make_job("mysql-py3.12-linux", target="mysql", environment="py3.12"),
        attempts=(
            JobAttemptProgress(
                attempt=1,
                job_id=11,
                status=Status.SUCCESS,
                conclusion=WorkflowJobConclusion.SUCCESS,
                failed_steps=(),
                job_url=None,
                reports=(),
                error=ProgressError.NO_ARTIFACTS,
            ),
        ),
    )
    batch = progress.batches[0]
    widened = replace(batch, jobs_progress=(*batch.jobs_progress, unavailable))
    return UpdatePRComment(id=f"msg-{revision}", revision=revision, progress=replace(progress, batches=(widened,)))


def test_the_ladder_walks_all_three_tiers():
    """Full, then compact, then minimal -- each smaller than the last."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    client.mock_response("create_issue_comment", _too_long_error(), once=True)

    asyncio.run(_updater(client).process_message(_tiered_update(1, done=True)))

    bodies = [call.kwargs["body"] for call in client.calls_to("create_issue_comment")]
    assert len(bodies) == 3
    sizes = [len(body.encode("utf-8")) for body in bodies]
    assert sizes[2] < sizes[1] < sizes[0]
    # Tier 2 sheds the secondary sections; tier 3 sheds the per-test detail but keeps the failures.
    assert "Unavailable results" in bodies[0]
    assert "Unavailable results" not in bodies[1]
    assert "test_number_0" in bodies[1]
    assert "test_number_0" not in bodies[2]
    assert "Failures" in bodies[2]
    assert "<table>" in bodies[2]


def test_a_too_long_body_never_escapes_the_updater():
    """The client raises a ValueError subclass, which the HTTP handler would not catch.

    A pre-flight raise bypassing the fallback would turn graceful degradation into a failed run.
    """
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error())

    for done in (False, True):
        asyncio.run(_updater(client).process_message(_tiered_update(1, done=done)))


def test_the_retained_report_is_the_full_one_even_when_a_smaller_tier_was_sent():
    """The run summary's own limit is 1 MiB, so the run page can keep the complete report."""
    client = FakeAsyncGitHubClient()
    client.mock_response("create_issue_comment", _too_long_error(), once=True)
    updater = _updater(client)

    asyncio.run(updater.process_message(_tiered_update(1, done=True)))

    assert updater.latest_body is not None
    assert "test_number_0" in updater.latest_body


def test_the_ladder_lands_when_github_is_stricter_than_our_measurement(monkeypatch):
    """The case the tiers exist for: GitHub refusing a body our own measurement passed.

    The renderer truncates itself to the limit, so the tiers are really there for GitHub's accounting
    disagreeing with ours. Simulated by a server that accepts only the smallest tier.
    """
    message = _tiered_update(1, done=True)
    tiers = [
        pr_comment.render_comment(message.progress),
        pr_comment.render_compact_comment(message.progress),
        pr_comment.render_minimal_comment(message.progress),
    ]
    # Every tier is within our own limit, so nothing here is caught before it is sent.
    assert all(len(tier.encode("utf-8")) <= pr_comment.COMMENT_BODY_LIMIT for tier in tiers)
    strict_limit = len(tiers[-1].encode("utf-8"))
    assert len(tiers[1].encode("utf-8")) > strict_limit, "the middle tier must not already fit"

    client = FakeAsyncGitHubClient()
    attempted: list[str] = []
    original = client.create_issue_comment

    async def stricter_github(owner, repo, issue_number, body, timeout=None):
        attempted.append(body)
        if len(body.encode("utf-8")) > strict_limit:
            raise GitHubBodyTooLongError.from_response(
                "body is too long (maximum is 65536 characters)", limit=pr_comment.COMMENT_BODY_LIMIT
            )
        return await original(owner, repo, issue_number, body, timeout)

    monkeypatch.setattr(client, "create_issue_comment", stricter_github)
    updater = _updater(client)

    asyncio.run(updater.process_message(message))

    # Full refused, compact refused, minimal accepted: the whole ladder, ending on a write.
    assert attempted == tiers
    assert not updater.pr_comment_failed
