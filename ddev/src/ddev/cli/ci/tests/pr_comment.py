# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Renders a ``DispatcherProgress`` snapshot into the body of the single Dispatcher PR comment.

Branches only on ``ExecutionState``, ``Status`` and ``ProgressError``, so the comment is a projection
of the aggregate rather than a second source of truth. The one exception is the footer, which reads
the run's own commit and URL from the environment.

Laid out like the Datadog CI Visibility comment. Badge images are deliberately absent — those are SVGs
on a host we do not publish to — so emoji carry the state.
"""

from __future__ import annotations

import html
from functools import partial
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.progress import ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from ddev.utils.github_actions import get_commit_sha, get_workflow_run_url
from ddev.utils.github_async import COMMENT_BODY_LIMIT

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from ddev.cli.ci.tests.progress import (
        BatchProgress,
        DispatcherProgress,
        JobAttemptProgress,
        JobProgress,
    )

    # A tier's section builder: given the snapshot and the bytes left, render the section or nothing.
    type SectionBuilder = Callable[[DispatcherProgress, int], str | None]

# Hidden first line of every Dispatcher comment. It brands the comment and is how the run reporter finds
# an existing one to edit, so nothing else may write it.
COMMENT_MARKER = "<!-- ddev-dispatcher-tests -->"

# Width of the text progress bar, in cells.
PROGRESS_BAR_WIDTH = 24

# Terminal but unfinished, which no other state in a report expresses: the rest derive from `done`.
CANCELLED_HEADING = "## 🚫 Dispatcher tests · cancelled"
CANCELLED_NOTE = "Anything below is what had been gathered by then, and batches still running were cancelled too."
# Said instead when no batch ever reported, where the note above would point at results that are absent.
CANCELLED_WITHOUT_RESULTS_NOTE = "The run was cancelled before any batch reported, so there are no results to show."

# Blocks are joined by a blank line, so each one costs two bytes beyond its own length. Newlines are
# one byte in UTF-8, so this is the same number in either unit.
SECTION_SEPARATOR = 2

# Room held back in every section for its own "N more not shown" line, so truncating a section can
# never itself be what silently drops the notice that truncation happened.
OVERFLOW_RESERVE = 160

PROGRESS_ERROR_TEXT = {
    ProgressError.TIMED_OUT: "timed out before results were gathered",
    ProgressError.NO_JOB_RESULTS: "the workflow reported no job results",
    ProgressError.NO_ARTIFACTS: "no artifacts were downloaded for this job",
}

# Prepended to the run summary when the pull-request comment could not be written. The run summary is
# then the only place the result exists, so it says so rather than looking like the intended surface.
RUN_SUMMARY_COMMENT_FAILED_NOTE = (
    "> [!WARNING]\n"
    "> **The pull request comment could not be updated.** This summary is the full report.\n"
    "> See the workflow logs for why the comment write failed."
)

# Said in both the alert and the footer, so a reader who skips one still learns the comment is live.
FOOTER_RUNNING_NOTE = "This comment updates automatically as each batch finishes."

STATUS_CHIP = {
    Status.SUCCESS: "✅ passed",
    Status.FAILURE: "❌ failed",
    Status.SKIPPED: "⏭️ skipped",
}


def _size(text: str) -> int:
    """UTF-8 byte length: the unit the client's guard measures, so the budget measures it too."""
    return len(text.encode("utf-8"))


def render_comment(progress: DispatcherProgress, *, cancelled: bool = False) -> str:
    """First of three tiers, budgeted in bytes against the client's own limit so the two cannot drift.

    The message's ``revision`` is deliberately not rendered: internal ordering metadata, already logged.
    """
    return _render(
        progress, (partial(_failures, detail=True), _unavailable, _retried), shows_unavailable=True, cancelled=cancelled
    )


def render_compact_comment(progress: DispatcherProgress, *, cancelled: bool = False) -> str:
    """Second tier: the failures keep their detail, the secondary sections go.

    Which tests failed is why anyone opens the comment; a retried-job list is one line per retry and can
    be the largest section in a flaky run.
    """
    return _render(progress, (partial(_failures, detail=True),), shows_unavailable=False, cancelled=cancelled)


def render_minimal_comment(progress: DispatcherProgress, *, cancelled: bool = False) -> str:
    """Last tier: batches, totals and a line per failed job, without naming the failed tests.

    The per-test lists are the dominant cost — 2.1 kB for a job with 40 failures against ~150 bytes for
    its summary line — so dropping them is what makes this fit. Only the batch table is unbudgeted, and
    it would need ~464 batches to exhaust the limit on its own.
    """
    return _render(progress, (partial(_failures, detail=False),), shows_unavailable=False, cancelled=cancelled)


def _render(
    progress: DispatcherProgress,
    sections: tuple[SectionBuilder, ...],
    *,
    shows_unavailable: bool,
    cancelled: bool = False,
) -> str:
    """Assemble a body from the header, whichever *sections* this tier keeps, and the footer.

    ``shows_unavailable`` tells the header whether this tier keeps ``_unavailable``, so the alert can
    neither point at a section that is not here nor stay silent about results it dropped.
    """
    header = _header(progress, shows_unavailable=shows_unavailable, cancelled=cancelled)
    footer = _footer(progress, cancelled=cancelled)

    # The header and footer always survive; the detail sections compete for what is left. Two
    # newlines join every block, so each section costs its own length plus that separator.
    remaining = COMMENT_BODY_LIMIT - _size(header) - _size(footer) - 4
    built = []
    for build in sections:
        section = build(progress, remaining - SECTION_SEPARATOR)
        if section is None:
            continue
        built.append(section)
        remaining -= _size(section) + SECTION_SEPARATOR

    return "\n\n".join([header, *built, footer])


def render_cancelled_notice() -> str:
    """What a run cancelled before any batch reported has to say: that it ran, and that it stopped.

    There is no snapshot to render, and the comment is the only place a reader learns the run existed.
    """
    footer = _footer(None, cancelled=True)
    return f"{COMMENT_MARKER}\n\n{CANCELLED_HEADING}\n\n{CANCELLED_WITHOUT_RESULTS_NOTE}\n\n{footer}"


def render_run_summary(body: str, *, pr_comment_failed: bool) -> str:
    """Turn a rendered comment *body* into the report written to the GitHub Actions run summary.

    Not a second renderer, so the run page and the pull request cannot disagree. Two differences only:
    the marker goes, since nothing looks a run summary up, and a failed comment write is announced,
    since a reader who arrived from the run page has no other way to know one was attempted.
    """
    report = body.removeprefix(COMMENT_MARKER).lstrip("\n")
    if not pr_comment_failed:
        return report

    return f"{RUN_SUMMARY_COMMENT_FAILED_NOTE}\n\n{report}"


def summary_line(progress: DispatcherProgress) -> str:
    """One-line plain-text summary, for logging a run that has no PR to comment on."""
    state = "complete" if progress.done else "in progress"
    return (
        f"Dispatcher tests {state}: {progress.complete}/{progress.total} jobs, "
        f"{progress.passed} passed, {progress.failed} failed, {progress.skipped} skipped"
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def _header(progress: DispatcherProgress, *, shows_unavailable: bool, cancelled: bool = False) -> str:
    """Marker, heading, in-progress alert and totals: the part that must never be truncated."""
    blocks = [COMMENT_MARKER, _heading(progress, cancelled=cancelled)]
    alert = _alert(progress, shows_unavailable=shows_unavailable, cancelled=cancelled)
    if alert is not None:
        blocks.append(alert)
    blocks.append(_totals(progress))
    blocks.append(_batch_table(progress))
    return "\n\n".join(blocks)


def _heading(progress: DispatcherProgress, *, cancelled: bool = False) -> str:
    """The run's outcome in one line. A failure outranks an unestablished result, which outranks a pass."""
    if cancelled:
        return CANCELLED_HEADING
    if not progress.done:
        return "## 🔄 Dispatcher tests · in progress"
    if _has_failure(progress):
        return "## ❌ Dispatcher tests · failed"
    if _unavailable_count(progress):
        return "## ⚠️ Dispatcher tests · results incomplete"
    return "## ✅ Dispatcher tests · passed"


def _alert(progress: DispatcherProgress, *, shows_unavailable: bool, cancelled: bool = False) -> str | None:
    """A native GitHub alert, so an unfinished run cannot be mistaken for a final one at a glance.

    A fallback tier sheds the section that lists unestablished results, so the alert states the count
    itself rather than pointing below, and carries it alongside a failure too. Without that, a fallback
    body would read as though every result was established.
    """
    if cancelled:
        return f"> [!CAUTION]\n> **The run was cancelled before it finished.** {CANCELLED_NOTE}"
    if not progress.done:
        return f"> [!NOTE]\n> **Tests are still running.** {_outstanding(progress)}\n> {FOOTER_RUNNING_NOTE}"

    unavailable = _unavailable_count(progress)
    if _has_failure(progress):
        alert = "> [!CAUTION]\n> **Dispatcher tests failed.** See the failures below."
        if unavailable and not shows_unavailable:
            verb = "are" if unavailable > 1 else "is"
            return f"{alert}\n> {_unavailable_phrase(unavailable)}, and {verb} not listed in this comment."
        return alert

    if unavailable:
        # Deliberately not a CAUTION: nothing failed, and there is no failures section to send anyone to.
        alert = f"> [!WARNING]\n> **{_unavailable_phrase(unavailable)}.** Nothing failed, but this is not a clean pass."
        return f"{alert}\n> See the unavailable results below." if shows_unavailable else alert
    return None


def _unavailable_phrase(count: int) -> str:
    plural = "s" if count > 1 else ""
    return f"{count} result{plural} could not be established"


def _outstanding(progress: DispatcherProgress) -> str:
    """What is left to do, counted in batches because they are the unit that actually finishes.

    A retrying batch has every job reported while the batch runs on, so a pending-jobs count alone can
    read as ``0`` on a run that is far from done.
    """
    unfinished = sum(1 for batch in progress.batches if batch.state is not ExecutionState.FINISHED)
    total = len(progress.batches)
    # The noun agrees with the total ("1 of 2 batches"), the verb with the outstanding count.
    plural = "es" if total != 1 else ""
    verb = "have" if unfinished != 1 else "has"
    outstanding = f"{unfinished} of {total} batch{plural} {verb} not finished yet."

    pending = progress.total - progress.complete
    if pending:
        outstanding += f" {pending} of {progress.total} jobs have not reported."
    return outstanding


def _totals(progress: DispatcherProgress) -> str:
    counts = [f"✅ {progress.passed} passed", f"❌ {progress.failed} failed"]
    if progress.skipped:
        counts.append(f"⏭️ {progress.skipped} skipped")
    pending = progress.total - progress.complete
    if pending:
        counts.append(f"⏳ {pending} pending")

    bar = _progress_bar(progress.complete, progress.total, done=progress.done)
    return f"`{bar}`  **{progress.complete}/{progress.total} jobs**\n{' · '.join(counts)}"


def _progress_bar(complete: int, total: int, *, done: bool) -> str:
    """The bar never reads as full until the run really is done.

    Every job in a retrying batch has reported, so ``complete == total`` happens well before the run
    finishes; a full bar there would contradict the heading next to it.
    """
    filled = round(PROGRESS_BAR_WIDTH * complete / total) if total else 0
    if not done:
        filled = min(filled, PROGRESS_BAR_WIDTH - 1)
    return "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)


def _batch_table(progress: DispatcherProgress) -> str:
    """Every batch, including the ones that have not started — the reason the snapshot carries them."""
    if not progress.batches:
        return "_No batches were planned._"

    rows = "\n".join(_batch_row(batch) for batch in progress.batches)
    return (
        "### Batches\n\n"
        "<table>\n"
        "<thead><tr><th>Batch</th><th>State</th><th>Jobs</th><th>Workflow</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n"
        "</table>"
    )


def _batch_row(batch: BatchProgress) -> str:
    done = sum(1 for job in batch.jobs_progress if job.latest is not None)
    workflow = (
        f'<a href="{html.escape(batch.workflow_url, quote=True)}">run {batch.run_id}</a>'
        if batch.workflow_url
        else "<em>link available after dispatch</em>"
    )
    return (
        f"<tr><td><code>{html.escape(batch.batch_id)}</code></td>"
        f"<td>{_batch_chip(batch)}</td>"
        f"<td>{done}/{len(batch.jobs_progress)}</td>"
        f"<td>{workflow}</td></tr>"
    )


def _batch_chip(batch: BatchProgress) -> str:
    """The batch's state chip.

    ``status`` is taken verbatim, never re-derived from ``jobs_progress``: it is the workflow's own
    conclusion, so a batch can be failed while every tracked job passed (a setup or upload step).
    Rolling the jobs up here would render that batch as passed and hide a real failure.
    """
    if batch.state is ExecutionState.FINISHED:
        chip = STATUS_CHIP.get(batch.status) if batch.status is not None else None
        return chip if chip is not None else "❔ no status reported"
    # A rerun is Dispatcher's own business, so at the batch level it is simply unfinished work. Which
    # jobs were retried is reported per job, where it is actionable.
    if batch.state in (ExecutionState.RUNNING, ExecutionState.RETRYING):
        return "🔄 in progress"
    return "⏳ queued"


# ---------------------------------------------------------------------------
# Detail sections, in the order they are given up under budget pressure
# ---------------------------------------------------------------------------


def _pack(entries: list[str], budget: int) -> tuple[list[str], int]:
    """Take entries in order while they fit. Returns what was kept and how many were dropped."""
    kept: list[str] = []
    for index, entry in enumerate(entries):
        cost = _size(entry) + (SECTION_SEPARATOR if kept else 0)
        if cost > budget:
            return kept, len(entries) - index
        kept.append(entry)
        budget -= cost
    return kept, 0


def _overflow_note(dropped: int, noun: str) -> str:
    plural = "s" if dropped > 1 else ""
    return f"_{dropped} more {noun}{plural} not shown — the comment reached its size limit._"


def _failures(progress: DispatcherProgress, budget: int, *, detail: bool = True) -> str | None:
    """The failed jobs. With *detail* off, each keeps its count but not the list of failing tests."""
    entries = []
    for job in _jobs(progress):
        attempt = job.latest
        if attempt is None or attempt.status is not Status.FAILURE:
            continue
        entries.append(_failed_job_entry(job, attempt, detail=detail))
    # A batch whose workflow failed without any tracked job failing is a real failure with nothing
    # to list; saying so beats an empty section or a silent omission.
    entries += [
        f"<code>{html.escape(batch.batch_id)}</code> — the workflow failed with no tracked job failure"
        for batch in progress.batches
        if batch.status is Status.FAILURE and not any(_is_failed(job) for job in batch.jobs_progress)
    ]
    if not entries:
        return None

    heading = "### ❌ Failures"
    wrapper = "\n\n<blockquote><div>\n\n\n\n</div></blockquote>"
    kept, dropped = _pack(entries, budget - _size(heading) - _size(wrapper) - OVERFLOW_RESERVE)
    if dropped:
        kept.append(_overflow_note(dropped, "failed job"))

    body = "\n\n".join(kept)
    return f"{heading}\n\n<blockquote><div>\n\n{body}\n\n</div></blockquote>"


def _failed_job_entry(job: JobProgress, attempt: JobAttemptProgress, *, detail: bool = True) -> str:
    link = f' &nbsp; <a href="{html.escape(attempt.job_url, quote=True)}">view job</a>' if attempt.job_url else ""
    entry = f"<code> {html.escape(_job_label(job))} </code>{link}"

    # ``<code>`` rather than a Markdown code span: ``html.escape`` leaves backticks alone, and a
    # backtick in a test id would close a span early and let the rest render as markup.
    failed_tests = attempt.failed_tests
    if failed_tests:
        items = "\n".join(f"- <code>{html.escape(f'{case.classname}::{case.name}')}</code>" for case in failed_tests)
        summary = f"{len(failed_tests)} failed test{'s' if len(failed_tests) > 1 else ''}"
    elif attempt.failed_steps:
        items = "\n".join(f"- <code>{html.escape(step)}</code>" for step in attempt.failed_steps)
        summary = f"{len(attempt.failed_steps)} failed step{'s' if len(attempt.failed_steps) > 1 else ''}"
    else:
        return f"{entry}\n<sub>No test-level failure was reported for this job.</sub>"

    if not detail:
        # The count without the names: enough to see the shape of the failure and open the job.
        return f"{entry}\n<sub>{summary}</sub>"

    return f"{entry}\n<details open>\n<summary>{summary}</summary>\n\n{items}\n\n</details>"


def _unavailable(progress: DispatcherProgress, budget: int) -> str | None:
    """Batches and jobs whose result could not be established — never rendered as success."""
    return _list_section("### ⚠️ Unavailable results", _unavailable_entries(progress), budget, "unavailable result")


def _unavailable_entries(progress: DispatcherProgress) -> list[str]:
    """One bullet per unestablished result.

    The header states how many there are and this renders them, so both read the same list: a count
    derived separately could disagree with the section printed right below it.
    """
    entries = [
        f"- <code>{html.escape(batch.batch_id)}</code> — {PROGRESS_ERROR_TEXT[batch.error]}"
        for batch in progress.batches
        if batch.error is not None
    ]
    for job in _jobs(progress):
        attempt = job.latest
        if attempt is None or attempt.error is None:
            continue
        entries.append(f"- <code>{html.escape(_job_label(job))}</code> — {PROGRESS_ERROR_TEXT[attempt.error]}")
    return entries


def _retried(progress: DispatcherProgress, budget: int) -> str | None:
    """Planned jobs that ran more than once. Retry count is executions minus one, never an attempt id."""
    entries = []
    for job in _jobs(progress):
        attempt = job.latest
        if job.retry_count == 0 or attempt is None:
            continue
        outcome = STATUS_CHIP.get(attempt.status, "❔ unknown")
        plural = "retries" if job.retry_count > 1 else "retry"
        entries.append(f"- <code>{html.escape(_job_label(job))}</code> — {outcome} after {job.retry_count} {plural}")
    return _list_section("### 🔁 Retried jobs", entries, budget, "retried job")


def _list_section(heading: str, entries: list[str], budget: int, noun: str) -> str | None:
    """A heading over a bullet list, truncated to *budget* with an explicit note when it is cut."""
    if not entries:
        return None
    kept, dropped = _pack(entries, budget - _size(heading) - SECTION_SEPARATOR - OVERFLOW_RESERVE)
    if dropped:
        kept.append(_overflow_note(dropped, noun))
    return f"{heading}\n\n" + "\n".join(kept)


# ---------------------------------------------------------------------------
# Footer and shared helpers
# ---------------------------------------------------------------------------


def _footer(progress: DispatcherProgress | None, *, cancelled: bool = False) -> str:
    """Whether this is the last word, and where the run that produced it lives.

    No status emoji on a finished run: the outcome is the heading's job, and a ✅ here read as "all
    good" on a run that had failed. What a reader cannot get anywhere else in the comment is which
    commit was tested and where Dispatcher itself ran, so that is what this says.
    """
    if not cancelled and (progress is None or not progress.done):
        return f"<sub>\n⏳ {FOOTER_RUNNING_NOTE}\n</sub>"

    note = "Dispatcher was cancelled" if cancelled else "Dispatcher finished"
    if sha := get_commit_sha():
        note += f" on <code>{html.escape(sha)}</code>"
    if run_url := get_workflow_run_url():
        note += f" — <a href=\"{html.escape(run_url, quote=True)}\">GitHub Run</a>"
    return f"<sub>\n{note}.\n</sub>"


def _jobs(progress: DispatcherProgress) -> Iterator[JobProgress]:
    return (job for batch in progress.batches for job in batch.jobs_progress)


def _is_failed(job: JobProgress) -> bool:
    return job.latest is not None and job.latest.status is Status.FAILURE


def _has_failure(progress: DispatcherProgress) -> bool:
    """Whether the run has a failure to answer for.

    A batch's own ``FAILURE`` counts, since a workflow can fail with no tracked job failing. An *error*
    does not: an unestablished result reads as incomplete, so the heading never claims a failure with
    nothing to show for it.
    """
    return progress.failed > 0 or any(batch.status is Status.FAILURE for batch in progress.batches)


def _unavailable_count(progress: DispatcherProgress) -> int:
    """How many results could not be established, batch-level and job-level together."""
    return len(_unavailable_entries(progress))


def _job_label(job: JobProgress) -> str:
    return f"{job.job.target} / {job.job.environment} / {job.job.platform}"
