# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the PR comment renderer.

The renderer is a pure projection of ``DispatcherProgress``, so these build snapshots by hand and
assert on the rendered body. What is worth testing is not the exact prose but the reporting rules:
an unfinished run must be unmistakable, a batch's status comes from the workflow rather than a
roll-up of its jobs, unavailable results never read as success, and nothing is dropped silently.
"""

from __future__ import annotations

import re

import pytest

from ddev.cli.ci.tests.messages import BatchJob
from ddev.cli.ci.tests.pr_comment import (
    COMMENT_MARKER,
    render_comment,
    render_compact_comment,
    render_minimal_comment,
    render_run_summary,
    summary_line,
)
from ddev.cli.ci.tests.progress import (
    BatchProgress,
    DispatcherProgress,
    ExecutionState,
    JobAttemptProgress,
    JobProgress,
    ProgressError,
)
from ddev.cli.ci.tests.status import Status
from ddev.utils.github_async.models.workflow import WorkflowJobConclusion
from ddev.utils.junit import JUnitCounts, JUnitReport, JUnitResult, JUnitResultKind, JUnitTestCase, JUnitTestSuite
from ddev.utils.platform import PlatformName
from tests.cli.ci.tests.helpers import make_job

# GitHub's own ceiling, from the 422 it returns: "body is too long (maximum is 65536 characters)".
# Not imported from the renderer on purpose — a test that reads the same constant it is checking
# would pass no matter what that constant said.
GITHUB_COMMENT_HARD_LIMIT = 65_536

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def batch_job(
    target: str = "redis", environment: str = "py3.12", platform: PlatformName = PlatformName.LINUX
) -> BatchJob:
    """A job as the renderer sees it. Only target, environment and platform reach the output."""
    return make_job(f"{target}-{environment}-{platform}", target=target, environment=environment, platform=platform)


def failing_report(*test_names: str) -> JUnitReport:
    cases = tuple(
        JUnitTestCase(
            classname="tests.test_check",
            name=name,
            time=0.1,
            results=(JUnitResult(kind=JUnitResultKind.FAILURE, message="boom"),),
        )
        for name in test_names
    )
    suite = JUnitTestSuite(
        name="tests",
        reported_counts=JUnitCounts(tests=len(cases), failures=len(cases), errors=0, skipped=0),
        time=1.0,
        timestamp=None,
        hostname=None,
        test_cases=cases,
    )
    return JUnitReport(name="unit", test_suites=(suite,))


def attempt(
    status: Status = Status.SUCCESS,
    *,
    number: int = 1,
    failed_steps: tuple[str, ...] = (),
    reports: tuple[JUnitReport, ...] = (),
    job_url: str | None = "https://github.com/o/r/actions/runs/1/job/9",
    error: ProgressError | None = None,
) -> JobAttemptProgress:
    return JobAttemptProgress(
        attempt=number,
        job_id=9,
        status=status,
        conclusion=WorkflowJobConclusion.SUCCESS if status is Status.SUCCESS else WorkflowJobConclusion.FAILURE,
        failed_steps=failed_steps,
        job_url=job_url,
        reports=reports,
        error=error,
    )


def job(*attempts: JobAttemptProgress, target: str = "redis", environment: str = "py3.12") -> JobProgress:
    return JobProgress(job=batch_job(target=target, environment=environment), attempts=attempts)


def batch(
    batch_id: str = "batch-01",
    *jobs: JobProgress,
    state: ExecutionState = ExecutionState.FINISHED,
    status: Status | None = Status.SUCCESS,
    run_id: int | None = 121,
    workflow_url: str | None = "https://github.com/o/r/actions/runs/121",
    current_attempt: int | None = 1,
    max_attempts: int = 1,
    error: ProgressError | None = None,
) -> BatchProgress:
    return BatchProgress(
        batch_id=batch_id,
        run_id=run_id,
        workflow_url=workflow_url,
        state=state,
        status=status,
        current_attempt=current_attempt,
        max_attempts=max_attempts,
        retries_remaining=0,
        retrying_jobs=(),
        jobs_progress=jobs,
        error=error,
    )


def _progress_bar_of(body: str) -> str:
    """The rendered progress bar: the first inline-code span in the body."""
    return body.split("`")[1]


def planned_batch(batch_id: str, job_count: int = 4) -> BatchProgress:
    jobs = tuple(job(target=f"target-{index}") for index in range(job_count))
    return batch(
        batch_id,
        *jobs,
        state=ExecutionState.PLANNED,
        status=None,
        run_id=None,
        workflow_url=None,
        current_attempt=None,
    )


# ---------------------------------------------------------------------------
# Scenarios from the design doc
# ---------------------------------------------------------------------------


def test_initial_snapshot_reads_as_starting() -> None:
    """Revision 0: every batch planned, nothing dispatched, no links yet."""
    progress = DispatcherProgress(
        batches=(planned_batch("batch-01"), planned_batch("batch-02"), planned_batch("batch-03")),
        done=False,
    )

    body = render_comment(progress)

    assert body.startswith(COMMENT_MARKER)
    assert "in progress" in body
    assert body.count("⏳ queued") == 3
    assert body.count("link available after dispatch") == 3
    assert "**0/12 jobs**" in body
    assert "⏳ 12 pending" in body
    # Nothing has run, so there is nothing to report beyond the plan.
    assert "Failures" not in body
    assert "Retried jobs" not in body


def test_a_retrying_batch_reads_as_plain_in_progress() -> None:
    """A rerun is Dispatcher's business, not the reader's: the batch is simply not finished yet.

    The retry is still reported where it is actionable — against the job that was retried.
    """
    progress = DispatcherProgress(
        batches=(
            batch("batch-01", job(attempt()), job(attempt())),
            batch(
                "batch-03",
                job(attempt(), attempt(Status.SUCCESS, number=2), target="postgres"),
                state=ExecutionState.RETRYING,
                status=None,
                current_attempt=2,
                max_attempts=3,
                run_id=123,
                workflow_url="https://github.com/o/r/actions/runs/123",
            ),
        ),
        done=False,
    )

    body = render_comment(progress)

    assert "🔄 in progress" in body
    # Neither the retry nor the attempt number surfaces at the batch level.
    assert "retrying" not in body
    assert "attempt" not in body
    # But the job that was retried still says so.
    assert "🔁 Retried jobs" in body
    assert "postgres / py3.12 / linux</code> — ✅ passed after 1 retry" in body


def test_a_running_batch_and_a_retrying_batch_are_indistinguishable() -> None:
    """Both are just unfinished work, so they must not render differently."""
    states = [ExecutionState.RUNNING, ExecutionState.RETRYING]
    chips = [
        render_comment(
            DispatcherProgress(
                batches=(batch("batch-01", job(), state=state, status=None, current_attempt=2, max_attempts=3),),
                done=False,
            )
        )
        for state in states
    ]

    assert chips[0] == chips[1]
    assert "🔄 in progress" in chips[0]


def test_final_snapshot_reads_as_complete_with_failures() -> None:
    progress = DispatcherProgress(
        batches=(
            batch("batch-01", job(attempt())),
            batch(
                "batch-02",
                job(attempt(Status.FAILURE, reports=(failing_report("test_connection", "test_timeout"),))),
                status=Status.FAILURE,
                run_id=122,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "## ❌ Dispatcher tests · failed" in body
    assert "> [!CAUTION]" in body
    assert "**2/2 jobs**" in body
    assert "✅ 1 passed · ❌ 1 failed" in body
    assert "2 failed tests" in body
    assert "<code>tests.test_check::test_connection</code>" in body
    assert "Final result" in body
    # Pending is only shown when something is actually outstanding.
    assert "pending" not in body


def test_all_passing_final_snapshot_has_no_alert() -> None:
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)

    body = render_comment(progress)

    assert "## ✅ Dispatcher tests · passed" in body
    assert "[!NOTE]" not in body
    assert "[!CAUTION]" not in body
    assert "Failures" not in body


def test_a_job_missing_its_artifacts_is_not_reported_as_a_pass() -> None:
    """A job can conclude ``success`` while its artifacts never arrive, so its result is unknown.

    Nothing failed, but the run is not a clean pass either: reporting it as passed would present an
    unestablished result as a green one, which is the one thing the unavailable section exists to
    prevent.
    """
    unavailable = job(attempt(error=ProgressError.NO_ARTIFACTS))
    progress = DispatcherProgress(batches=(batch("batch-01", unavailable),), done=True)

    body = render_comment(progress)

    assert "## ⚠️ Dispatcher tests · results incomplete" in body
    assert "Dispatcher tests · passed" not in body
    assert "⚠️ Unavailable results" in body
    # Not a failure: there is no failed job to point at, so a CAUTION would promise a section that
    # never gets rendered.
    assert "[!CAUTION]" not in body
    assert "[!WARNING]" in body


def test_incomplete_signals_agree_with_each_other() -> None:
    """The heading, alert and footer must tell the same story, as they do for an unfinished run."""
    progress = DispatcherProgress(
        batches=(batch("batch-01", job(attempt(error=ProgressError.NO_ARTIFACTS))),), done=True
    )

    body = render_comment(progress)

    assert "results incomplete" in body
    assert "[!WARNING]" in body
    assert "unavailable results" in body.rsplit("<sub>", 1)[1]
    # Still a final answer, so the footer says so rather than reading as still running.
    assert "Final result" in body
    assert "updates automatically" not in body


def test_a_batch_error_without_a_failed_status_reads_as_incomplete() -> None:
    """A workflow can conclude successfully and still report nothing to gather.

    That used to render as a failure with an empty failures section, because the batch error was
    counted as a failure while nothing was there to list.
    """
    progress = DispatcherProgress(
        batches=(batch("batch-01", status=Status.SUCCESS, error=ProgressError.NO_JOB_RESULTS),),
        done=True,
    )

    body = render_comment(progress)

    assert "## ⚠️ Dispatcher tests · results incomplete" in body
    assert "Dispatcher tests · passed" not in body
    assert "reported no job results" in body
    assert "[!CAUTION]" not in body


def test_a_real_failure_outranks_an_unavailable_result() -> None:
    """A failure is the more actionable of the two, so it decides the heading."""
    progress = DispatcherProgress(
        batches=(
            batch(
                "batch-01",
                job(attempt(Status.FAILURE, reports=(failing_report("test_connection"),)), target="postgres"),
                job(attempt(error=ProgressError.NO_ARTIFACTS), target="vault"),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "## ❌ Dispatcher tests · failed" in body
    assert "results incomplete" not in body
    assert "[!CAUTION]" in body
    assert "[!WARNING]" not in body
    # Both are still reported; only the heading has to choose.
    assert "❌ Failures" in body
    assert "⚠️ Unavailable results" in body


@pytest.mark.parametrize("count", [1, 2, 3])
def test_the_unavailable_count_matches_the_section(count: int) -> None:
    """The alert states a number the reader can check against the list directly below it."""
    jobs = [job(attempt(error=ProgressError.NO_ARTIFACTS), target=f"target-{index}") for index in range(count)]
    progress = DispatcherProgress(batches=(batch("batch-01", *jobs),), done=True)

    body = render_comment(progress)

    section = body.split("### ⚠️ Unavailable results")[1]
    assert section.count("— no artifacts") == count
    plural = "s" if count > 1 else ""
    assert f"{count} result{plural} could not be established" in body


# ---------------------------------------------------------------------------
# In-progress signalling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("done", [False, True])
def test_progress_signals_agree_with_each_other(done: bool) -> None:
    """The four in-progress signals are redundant on purpose; the bug to catch is one disagreeing.

    An unfinished run that renders like a final one is the worst failure this renderer can have, so
    the heading, alert, pending count and footer are asserted together rather than one per test.
    """
    jobs = (job(attempt()), job(attempt())) if done else (job(attempt()),)
    progress = DispatcherProgress(
        batches=(batch("batch-01", *jobs) if done else batch("batch-01", job(attempt()), job()),),
        done=done,
    )

    body = render_comment(progress)

    assert ("in progress" in body) is not done
    assert ("[!NOTE]" in body) is not done
    assert ("pending" in body) is not done
    assert ("updates automatically" in body) is not done
    assert ("Final result" in body) is done


def test_a_retrying_run_with_every_job_reported_still_reads_as_unfinished() -> None:
    """``complete == total`` on an unfinished run is reachable, not a contradiction.

    Every job in a retrying batch has reported — their latest attempts failed — so a jobs-only
    progress signal reads as 100%% while the run is far from over. The alert counts batches and the
    bar refuses to fill, or the comment would contradict its own heading.
    """
    progress = DispatcherProgress(
        batches=(
            batch("batch-01", job(attempt())),
            batch(
                "batch-02",
                job(attempt(Status.FAILURE), target="redis"),
                state=ExecutionState.RETRYING,
                status=None,
                current_attempt=2,
                max_attempts=3,
            ),
        ),
        done=False,
    )

    body = render_comment(progress)

    assert "**2/2 jobs**" in body
    assert "1 of 2 batches has not finished yet" in body
    # No pending jobs to report, so that clause is left out rather than printed as zero.
    assert "0 of 2 jobs have not reported" not in body
    # A full bar next to "in progress" is the contradiction this guards against.
    assert "░" in _progress_bar_of(body)
    assert "in progress" in body


def test_the_bar_only_fills_completely_when_the_run_is_done() -> None:
    finished = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)
    assert "░" not in _progress_bar_of(render_comment(finished))


def test_unfinished_run_never_claims_completion() -> None:
    """Even with every reported job passing, an unfinished run must not read as passed."""
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt()), job()),), done=False)

    body = render_comment(progress)

    assert "Dispatcher tests · passed" not in body
    assert "## 🔄 Dispatcher tests · in progress" in body
    assert "⏳ 1 pending" in body


# ---------------------------------------------------------------------------
# Status semantics
# ---------------------------------------------------------------------------


def test_batch_status_is_the_workflow_not_a_roll_up_of_its_jobs() -> None:
    """A workflow can fail in a setup or upload step while every tracked job passes.

    ``BatchProgress.status`` is the workflow's own conclusion, so re-deriving it from the jobs here
    would render this batch as passed and hide a real failure.
    """
    progress = DispatcherProgress(
        batches=(batch("batch-01", job(attempt()), job(attempt()), status=Status.FAILURE),),
        done=True,
    )

    body = render_comment(progress)

    assert "❌ failed" in body
    assert "✅ passed" not in body.split("### Batches")[1].split("</table>")[0]
    assert "## ❌ Dispatcher tests · failed" in body
    # There is no failed job to list, so say so rather than print an empty section.
    assert "the workflow failed with no tracked job failure" in body


def test_a_finished_batch_with_no_status_says_so_rather_than_guessing() -> None:
    """``status`` is ``None`` on a finished batch only if something went wrong upstream."""
    progress = DispatcherProgress(
        batches=(batch("batch-01", job(attempt()), status=None, error=ProgressError.NO_JOB_RESULTS),),
        done=True,
    )

    body = render_comment(progress)

    assert "❔ no status reported" in body
    assert "✅ passed" not in body.split("### Batches")[1].split("</table>")[0]


def test_skipped_is_shown_only_when_non_zero() -> None:
    passing = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)
    assert "skipped" not in render_comment(passing)

    with_skips = DispatcherProgress(batches=(batch("batch-01", job(attempt(Status.SKIPPED))),), done=True)
    assert "⏭️ 1 skipped" in render_comment(with_skips)


def test_only_the_latest_attempt_counts_toward_totals() -> None:
    """A job retried to success counts once, as a pass — not once per execution."""
    progress = DispatcherProgress(
        batches=(batch("batch-01", job(attempt(Status.FAILURE), attempt(Status.SUCCESS, number=2))),),
        done=True,
    )

    body = render_comment(progress)

    assert "**1/1 jobs**" in body
    assert "✅ 1 passed · ❌ 0 failed" in body
    assert "✅ passed after 1 retry" in body


def test_failed_steps_are_listed_when_no_test_failed() -> None:
    """A job can fail without any test failing — an infrastructure or setup step."""
    failed = job(attempt(Status.FAILURE, failed_steps=("Install deps",)))
    progress = DispatcherProgress(batches=(batch("batch-01", failed, status=Status.FAILURE),), done=True)

    body = render_comment(progress)

    assert "1 failed step" in body
    assert "<code>Install deps</code>" in body


def test_failed_job_with_no_detail_says_so() -> None:
    progress = DispatcherProgress(
        batches=(batch("batch-01", job(attempt(Status.FAILURE)), status=Status.FAILURE),),
        done=True,
    )

    assert "No test-level failure was reported" in render_comment(progress)


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (ProgressError.TIMED_OUT, "timed out"),
        (ProgressError.NO_JOB_RESULTS, "reported no job results"),
        (ProgressError.NO_ARTIFACTS, "no artifacts"),
    ],
)
def test_batch_errors_render_as_unavailable_never_as_success(error: ProgressError, expected: str) -> None:
    progress = DispatcherProgress(
        batches=(batch("batch-01", job(attempt()), status=Status.FAILURE, error=error),),
        done=True,
    )

    body = render_comment(progress)

    assert "⚠️ Unavailable results" in body
    assert expected in body
    assert "Dispatcher tests · passed" not in body


def test_job_level_error_is_reported_against_the_job() -> None:
    unavailable = job(attempt(Status.FAILURE, error=ProgressError.NO_ARTIFACTS))
    progress = DispatcherProgress(batches=(batch("batch-01", unavailable, status=Status.FAILURE),), done=True)

    body = render_comment(progress)

    assert "redis / py3.12 / linux</code> — no artifacts" in body


# ---------------------------------------------------------------------------
# Safety: escaping, structure, budget, degenerate input
# ---------------------------------------------------------------------------


def test_test_names_and_steps_are_escaped() -> None:
    """Test output is arbitrary text; it must not be able to break out of its block."""
    progress = DispatcherProgress(
        batches=(
            batch(
                "batch-01",
                job(
                    attempt(
                        Status.FAILURE,
                        reports=(failing_report('test_foo<bar> & "baz"</details>'),),
                    )
                ),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "test_foo&lt;bar&gt; &amp; &quot;baz&quot;&lt;/details&gt;" in body
    # The raw closing tag must not appear inside the rendered test name.
    assert body.count("</details>") == 1


def test_a_backtick_in_a_test_name_cannot_break_out() -> None:
    """``html.escape`` leaves backticks alone, so names must not sit in Markdown code spans.

    pytest puts parametrised values straight into the test id, so a backtick is reachable input; in a
    code span it would close the span early and let the rest of the name render as markup.
    """
    name = "test_eval[`ls` && <b>x</b>]"
    progress = DispatcherProgress(
        batches=(
            batch(
                "batch-01",
                job(attempt(Status.FAILURE, reports=(failing_report(name),))),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "test_eval[`ls` &amp;&amp; &lt;b&gt;x&lt;/b&gt;]</code>" in body
    # The name is inside an HTML element, so its backticks are inert rather than span delimiters.
    assert "- `" not in body


def test_failed_steps_are_escaped_too() -> None:
    """Step names come from the workflow file and get the same treatment as test names."""
    progress = DispatcherProgress(
        batches=(
            batch(
                "batch-01",
                job(attempt(Status.FAILURE, failed_steps=("Run `pytest` <hack>",))),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    assert "Run `pytest` &lt;hack&gt;</code>" in body
    assert "- `" not in body


def test_html_tags_are_balanced() -> None:
    """An unbalanced tag silently swallows the rest of the comment on GitHub."""
    progress = DispatcherProgress(
        batches=(
            batch("batch-01", job(attempt())),
            batch(
                "batch-02",
                job(attempt(Status.FAILURE, reports=(failing_report("test_a"),))),
                status=Status.FAILURE,
                error=ProgressError.TIMED_OUT,
            ),
        ),
        done=True,
    )

    body = render_comment(progress)

    for tag in ("details", "blockquote", "table", "tbody", "thead", "div", "sub", "code"):
        assert body.count(f"<{tag}") == body.count(f"</{tag}>"), tag


def test_large_run_stays_within_budget_and_says_what_was_dropped() -> None:
    """240 jobs, all failing with many tests each: far more detail than a comment can hold."""
    batches = tuple(
        batch(
            f"batch-{index:02d}",
            *[
                job(
                    attempt(
                        Status.FAILURE,
                        reports=(failing_report(*[f"test_number_{number}" for number in range(20)]),),
                    ),
                    target=f"integration-{index}-{slot}",
                )
                for slot in range(24)
            ],
            status=Status.FAILURE,
        )
        for index in range(10)
    )
    progress = DispatcherProgress(batches=batches, done=True)

    body = render_comment(progress)

    # Bytes, because that is the unit the client's guard measures and therefore the one the budget
    # targets. The body is dense with three-byte emoji and block-drawing characters, so a character
    # count would understate it.
    assert len(body.encode("utf-8")) <= GITHUB_COMMENT_HARD_LIMIT
    # The header survives intact: totals and every batch row are the highest-priority content.
    assert "**240/240 jobs**" in body
    assert body.count("<tr><td><code>batch-") == 10
    assert "not shown — the comment reached its size limit" in body
    for tag in ("details", "blockquote", "table", "div", "sub"):
        assert body.count(f"<{tag}") == body.count(f"</{tag}>"), tag


def test_dropped_count_is_accurate() -> None:
    """The overflow note must state the real number, not a placeholder."""
    jobs = [
        job(attempt(Status.FAILURE, reports=(failing_report(*[f"t{n}" for n in range(200)]),)), target=f"t-{index}")
        for index in range(60)
    ]
    progress = DispatcherProgress(batches=(batch("batch-01", *jobs, status=Status.FAILURE),), done=True)

    body = render_comment(progress)

    shown = body.count("<details open>")
    match = re.search(r"_(\d+) more failed jobs? not shown", body)
    assert match is not None
    assert shown + int(match.group(1)) == 60


def test_empty_snapshot_does_not_crash() -> None:
    body = render_comment(DispatcherProgress(batches=(), done=True))

    assert COMMENT_MARKER in body
    assert "**0/0 jobs**" in body
    assert "No batches were planned." in body


def test_minimal_comment_keeps_the_header_and_drops_the_detail() -> None:
    progress = DispatcherProgress(
        batches=(
            batch(
                "batch-01",
                job(attempt(Status.FAILURE, reports=(failing_report("test_a"),))),
                status=Status.FAILURE,
            ),
        ),
        done=True,
    )

    compact = render_compact_comment(progress)

    assert COMMENT_MARKER in compact
    assert "**1/1 jobs**" in compact
    assert "<table>" in compact
    # The failures survive the compact tier with their detail; only the secondary sections go.
    assert "Failures" in compact
    assert "test_a" in compact


def test_no_internal_metadata_leaks_into_the_comment() -> None:
    """The reader gets state, not plumbing: the message revision is never rendered."""
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)

    for body in (render_comment(progress), render_compact_comment(progress), render_minimal_comment(progress)):
        assert "evision" not in body


def test_summary_line_reports_state_and_counts() -> None:
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt()), job()),), done=False)

    assert summary_line(progress) == "Dispatcher tests in progress: 1/2 jobs, 1 passed, 0 failed, 0 skipped"


# ---------------------------------------------------------------------------
# Run summary
# ---------------------------------------------------------------------------


def test_the_run_summary_is_the_comment_without_the_marker() -> None:
    """The same report, on a surface that has nothing to find it by.

    The marker exists only so the updater can locate its comment. A run summary is written once and
    never looked up, so carrying the marker there would say nothing and would put it somewhere the
    updater's ownership rules do not apply.
    """
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)
    body = render_comment(progress)

    summary = render_run_summary(body, pr_comment_failed=False)

    assert not summary.startswith(COMMENT_MARKER)
    assert COMMENT_MARKER not in summary
    assert summary == body.removeprefix(COMMENT_MARKER).lstrip("\n")


def test_a_clean_run_summary_adds_nothing_of_its_own() -> None:
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)

    summary = render_run_summary(render_comment(progress), pr_comment_failed=False)

    assert "[!WARNING]" not in summary
    assert "could not be updated" not in summary
    assert summary.startswith("## ")


def test_a_failed_comment_write_is_announced_above_the_report() -> None:
    """The reader arrives from the run page with no idea a comment was attempted."""
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)

    summary = render_run_summary(render_comment(progress), pr_comment_failed=True)

    assert summary.startswith("> [!WARNING]")
    # The note precedes the heading, so it is read before the result it qualifies.
    assert summary.index("[!WARNING]") < summary.index("## ")
    assert "pull request comment could not be updated" in summary
    # The report itself is untouched below the note.
    assert summary.endswith(render_comment(progress).removeprefix(COMMENT_MARKER).lstrip("\n"))


def test_the_run_summary_preserves_a_report_that_reports_failures() -> None:
    """Whatever the comment would have said, the summary says — this is not a second renderer."""
    failing = job(attempt(Status.FAILURE, reports=(failing_report("test_boom"),)))
    progress = DispatcherProgress(batches=(batch("batch-01", failing, status=Status.FAILURE),), done=True)

    summary = render_run_summary(render_comment(progress), pr_comment_failed=True)

    assert "Dispatcher tests · failed" in summary
    assert "test_boom" in summary
    assert summary.count("[!WARNING]") == 1


def test_a_minimal_report_survives_the_run_summary() -> None:
    """The fallback body is what gets retained when the full one was rejected, so it must render."""
    progress = DispatcherProgress(batches=(batch("batch-01", job(attempt())),), done=True)

    summary = render_run_summary(render_minimal_comment(progress), pr_comment_failed=True)

    assert COMMENT_MARKER not in summary
    assert "Final result" in summary


def test_a_body_without_the_marker_is_passed_through_unharmed() -> None:
    """Stripping is not allowed to eat the first line of a body that never carried a marker."""
    summary = render_run_summary("## Some report\n\nbody", pr_comment_failed=False)

    assert summary == "## Some report\n\nbody"


# ---------------------------------------------------------------------------
# The three tiers
# ---------------------------------------------------------------------------


def _worst_case(job_count: int = 60, tests_per_job: int = 200) -> DispatcherProgress:
    """A finished run where every job failed with a long list of failing tests."""
    jobs = [
        job(
            attempt(Status.FAILURE, reports=(failing_report(*[f"test_number_{n}" for n in range(tests_per_job)]),)),
            target=f"target-{index}",
        )
        for index in range(job_count)
    ]
    return DispatcherProgress(batches=(batch("batch-01", *jobs, status=Status.FAILURE),), done=True)


def test_each_tier_is_smaller_than_the_one_before() -> None:
    """The ladder only helps if every step down actually sheds bytes."""
    progress = _worst_case()

    full = len(render_comment(progress).encode("utf-8"))
    compact = len(render_compact_comment(progress).encode("utf-8"))
    minimal = len(render_minimal_comment(progress).encode("utf-8"))

    assert minimal < compact <= full


def test_every_tier_fits_the_limit_for_a_worst_case_run() -> None:
    progress = _worst_case()

    for render in (render_comment, render_compact_comment, render_minimal_comment):
        assert len(render(progress).encode("utf-8")) <= GITHUB_COMMENT_HARD_LIMIT, render.__name__


def test_the_last_tier_names_the_failed_jobs_but_not_the_failed_tests() -> None:
    """What the tier is for: enough to see which jobs failed and open them, without the test lists."""
    progress = _worst_case(job_count=1, tests_per_job=3)

    body = render_minimal_comment(progress)

    # The job, its count and its link survive.
    assert "target-0" in body
    assert "200 failed tests" not in body
    assert "3 failed tests" in body
    assert "view job" in body
    # The names do not, and neither does the collapsible that held them.
    assert "test_number_0" not in body
    assert "<details" not in body
    # The batching stays: it is the other half of what a reader needs.
    assert "<table>" in body
    assert "Failures" in body


def test_the_last_tier_barely_grows_with_the_size_of_the_run() -> None:
    """Dropping the per-test lists is what removes the dominant term.

    A job's failing-test list is the multiplier — 200 names against one summary line — so the last
    tier grows per failed job rather than per failed test. That is what makes it fit where the others
    do not.
    """
    few = len(render_minimal_comment(_worst_case(job_count=1, tests_per_job=1)).encode("utf-8"))
    many_tests = len(render_minimal_comment(_worst_case(job_count=1, tests_per_job=500)).encode("utf-8"))

    # Five hundred more failing tests in the same job cost only the width of the count.
    assert many_tests - few < 20


def test_the_secondary_sections_are_what_the_compact_tier_drops() -> None:
    unavailable = job(attempt(error=ProgressError.NO_ARTIFACTS), target="flaky")
    retried = job(attempt(Status.FAILURE), attempt(Status.SUCCESS, number=2), target="postgres")
    progress = DispatcherProgress(batches=(batch("batch-01", unavailable, retried, max_attempts=2),), done=True)

    full = render_comment(progress)
    compact = render_compact_comment(progress)

    assert "Unavailable results" in full
    assert "Retried jobs" in full
    assert "Unavailable results" not in compact
    assert "Retried jobs" not in compact


def test_the_budget_is_measured_in_bytes_not_characters() -> None:
    """A body of non-ASCII test names must still fit, which a character budget would not guarantee."""
    jobs = [
        job(
            attempt(Status.FAILURE, reports=(failing_report(*[f"test_ünïcödé_{n}_日本語" for n in range(200)]),)),
            target=f"tärget-{index}",
        )
        for index in range(60)
    ]
    progress = DispatcherProgress(batches=(batch("batch-01", *jobs, status=Status.FAILURE),), done=True)

    body = render_comment(progress)

    assert len(body.encode("utf-8")) <= GITHUB_COMMENT_HARD_LIMIT
    # Characters alone would have left room that the bytes do not, which is the bug this rules out.
    assert len(body) < len(body.encode("utf-8"))
