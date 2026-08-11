# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Renders a ``DispatcherProgress`` snapshot into the body of the single Dispatcher PR comment.

Pure functions: no I/O, no GitHub models, no state. Everything branches on ``ExecutionState``,
``Status`` and ``ProgressError``, never on prose, so the comment is a projection of the aggregate
rather than a second source of truth.

The layout follows the Datadog CI Visibility PR comment: ``<code>`` chips for identifiers, a table
for the batch list, ``<details>`` for anything long, and a ``<sub>`` footer. Badge images are
deliberately absent — those are SVGs on a host we do not publish to — so emoji carry the state.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.progress import ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ddev.cli.ci.tests.progress import (
        BatchProgress,
        DispatcherProgress,
        JobAttemptProgress,
        JobProgress,
    )

# Hidden first line of every Dispatcher comment. It brands the comment and is how the updater finds
# an existing one to edit, so nothing else may write it.
COMMENT_MARKER = "<!-- ddev-dispatcher-tests -->"

# Self-imposed ceiling, not a platform value: GitHub rejects a body over 65,536 characters with
# "422 ... body is too long (maximum is 65536 characters)". The limit is documented nowhere but that
# error message, so the headroom here is deliberate.
COMMENT_CHARACTER_BUDGET = 50_000

# Width of the text progress bar, in cells.
PROGRESS_BAR_WIDTH = 24

# Blocks are joined by a blank line, so each one costs two characters beyond its own length.
SECTION_SEPARATOR = 2

# Room held back in every section for its own "N more not shown" line, so truncating a section can
# never itself be what silently drops the notice that truncation happened.
OVERFLOW_RESERVE = 160

PROGRESS_ERROR_TEXT = {
    ProgressError.TIMED_OUT: "timed out before results were gathered",
    ProgressError.NO_JOB_RESULTS: "the workflow reported no job results",
    ProgressError.NO_ARTIFACTS: "no artifacts were downloaded for this job",
}

# Said in both the alert and the footer, so a reader who skips one still learns the comment is live.
FOOTER_RUNNING_NOTE = "This comment updates automatically as each batch finishes."

STATUS_CHIP = {
    Status.SUCCESS: "✅ passed",
    Status.FAILURE: "❌ failed",
    Status.SKIPPED: "⏭️ skipped",
}


def render_comment(progress: DispatcherProgress) -> str:
    """Render the full comment body for *progress*, trimmed to ``COMMENT_CHARACTER_BUDGET``.

    The snapshot is the whole input. The message's ``revision`` is deliberately not rendered: it is
    internal ordering metadata, meaningless to the person reading the pull request, and the gatherer
    already logs it for diagnosis.
    """
    header = _header(progress)
    footer = _footer(progress)

    # The header and footer always survive; the detail sections compete for what is left. Two
    # newlines join every block, so each section costs its own length plus that separator.
    remaining = COMMENT_CHARACTER_BUDGET - len(header) - len(footer) - 4
    sections = []
    for build in (_failures, _unavailable, _retried):
        section = build(progress, remaining - SECTION_SEPARATOR)
        if section is None:
            continue
        sections.append(section)
        remaining -= len(section) + SECTION_SEPARATOR

    return "\n\n".join([header, *sections, footer])


def render_minimal_comment(progress: DispatcherProgress) -> str:
    """Render only the header and footer: the fallback when GitHub rejects a body as too long.

    Character budgeting is not a proof — GitHub's own accounting is not a plain character count — so
    a terse comment that posts beats a rich one that does not.
    """
    return "\n\n".join([_header(progress), _footer(progress)])


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


def _header(progress: DispatcherProgress) -> str:
    """Marker, heading, in-progress alert and totals: the part that must never be truncated."""
    blocks = [COMMENT_MARKER, _heading(progress)]
    alert = _alert(progress)
    if alert is not None:
        blocks.append(alert)
    blocks.append(_totals(progress))
    blocks.append(_batch_table(progress))
    return "\n\n".join(blocks)


def _heading(progress: DispatcherProgress) -> str:
    if not progress.done:
        return "## 🔄 Dispatcher tests · in progress"
    if _has_failure(progress):
        return "## ❌ Dispatcher tests · failed"
    return "## ✅ Dispatcher tests · passed"


def _alert(progress: DispatcherProgress) -> str | None:
    """A native GitHub alert, so an unfinished run cannot be mistaken for a final one at a glance."""
    if not progress.done:
        return f"> [!NOTE]\n> **Tests are still running.** {_outstanding(progress)}\n> {FOOTER_RUNNING_NOTE}"
    if _has_failure(progress):
        return "> [!CAUTION]\n> **Dispatcher tests failed.** See the failures below."
    return None


def _outstanding(progress: DispatcherProgress) -> str:
    """What is left to do, counted in batches rather than jobs.

    A retrying batch has every job reported — its latest attempts failed — while the batch itself is
    still running, so a pending-jobs count alone can read as ``0`` on a run that is far from done.
    Batches are the unit that actually finishes, so they are what the alert leads with.
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
    # Retrying is not called out at the batch level: a rerun is Dispatcher's own business, and from
    # the reader's side the batch is simply not finished yet. Which jobs were retried, and how often,
    # is reported per job where it is actionable.
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
        cost = len(entry) + (SECTION_SEPARATOR if kept else 0)
        if cost > budget:
            return kept, len(entries) - index
        kept.append(entry)
        budget -= cost
    return kept, 0


def _overflow_note(dropped: int, noun: str) -> str:
    plural = "s" if dropped > 1 else ""
    return f"_{dropped} more {noun}{plural} not shown — the comment reached its size limit._"


def _failures(progress: DispatcherProgress, budget: int) -> str | None:
    entries = []
    for job in _jobs(progress):
        attempt = job.latest
        if attempt is None or attempt.status is not Status.FAILURE:
            continue
        entries.append(_failed_job_entry(job, attempt))
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
    kept, dropped = _pack(entries, budget - len(heading) - len(wrapper) - OVERFLOW_RESERVE)
    if dropped:
        kept.append(_overflow_note(dropped, "failed job"))

    body = "\n\n".join(kept)
    return f"{heading}\n\n<blockquote><div>\n\n{body}\n\n</div></blockquote>"


def _failed_job_entry(job: JobProgress, attempt: JobAttemptProgress) -> str:
    link = f' &nbsp; <a href="{html.escape(attempt.job_url, quote=True)}">view job</a>' if attempt.job_url else ""
    entry = f"<code> {html.escape(_job_label(job))} </code>{link}"

    # ``<code>`` rather than a Markdown code span: ``html.escape`` does not escape backticks, and a
    # test id may contain one (pytest puts parametrised values straight into the name). A backtick
    # inside a span would close it early and let the rest of the name render as markup.
    failed_tests = attempt.failed_tests
    if failed_tests:
        items = "\n".join(f"- <code>{html.escape(f'{case.classname}::{case.name}')}</code>" for case in failed_tests)
        summary = f"{len(failed_tests)} failed test{'s' if len(failed_tests) > 1 else ''}"
    elif attempt.failed_steps:
        items = "\n".join(f"- <code>{html.escape(step)}</code>" for step in attempt.failed_steps)
        summary = f"{len(attempt.failed_steps)} failed step{'s' if len(attempt.failed_steps) > 1 else ''}"
    else:
        return f"{entry}\n<sub>No test-level failure was reported for this job.</sub>"

    return f"{entry}\n<details open>\n<summary>{summary}</summary>\n\n{items}\n\n</details>"


def _unavailable(progress: DispatcherProgress, budget: int) -> str | None:
    """Batches and jobs whose result could not be established — never rendered as success."""
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
    return _list_section("### ⚠️ Unavailable results", entries, budget, "unavailable result")


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
    kept, dropped = _pack(entries, budget - len(heading) - SECTION_SEPARATOR - OVERFLOW_RESERVE)
    if dropped:
        kept.append(_overflow_note(dropped, noun))
    return f"{heading}\n\n" + "\n".join(kept)


# ---------------------------------------------------------------------------
# Footer and shared helpers
# ---------------------------------------------------------------------------


def _footer(progress: DispatcherProgress) -> str:
    note = "✅ Final result — Dispatcher has finished." if progress.done else f"⏳ {FOOTER_RUNNING_NOTE}"
    return f"<sub>\n{note}\n</sub>"


def _jobs(progress: DispatcherProgress) -> Iterator[JobProgress]:
    return (job for batch in progress.batches for job in batch.jobs_progress)


def _is_failed(job: JobProgress) -> bool:
    return job.latest is not None and job.latest.status is Status.FAILURE


def _has_failure(progress: DispatcherProgress) -> bool:
    """Whether the run has anything to answer for.

    A batch's own ``FAILURE`` status and a batch error both count on their own: a workflow can fail,
    or its results can be unavailable, without any tracked job reporting a failure.
    """
    return progress.failed > 0 or any(
        batch.status is Status.FAILURE or batch.error is not None for batch in progress.batches
    )


def _job_label(job: JobProgress) -> str:
    return f"{job.job.target} / {job.job.environment} / {job.job.platform}"
