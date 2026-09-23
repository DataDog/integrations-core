# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Render progress and optional shutdown context as the shared Dispatcher PR report.

The layout is integration-first: it answers "did my integration break" before "which batch ran it",
so failures are grouped into one disclosure per integration rather than one entry per failed job.

Within a group the unit is the target, and a target's job link is the reader's way into the run that
failed. So every affected target keeps a line of its own with its own link, and the structure does
not change with the number of targets or integrations — only `DetailLevel` changes it, and only
because the body would otherwise not fit.

The footer adds the commit, workflow URL, and run logs link from the environment.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from ddev.cli.ci.tests.dispatcher_logging import get_dispatcher_logs_url
from ddev.cli.ci.tests.progress import ExecutionState, ProgressError
from ddev.cli.ci.tests.status import Status
from ddev.event_bus.shutdown import ShutdownKind, ShutdownRequest
from ddev.utils.github_actions import get_commit_sha, get_workflow_run_url
from ddev.utils.github_async import COMMENT_BODY_LIMIT

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from ddev.cli.ci.tests.progress import (
        BatchProgress,
        DispatcherProgress,
        JobAttemptProgress,
        JobProgress,
    )

# Hidden first line of every Dispatcher comment. It brands the comment and is how the run reporter finds
# an existing one to edit, so nothing else may write it.
COMMENT_MARKER = "<!-- ddev-dispatcher-tests -->"

# 1x1 solid-colour pixels the bar is drawn from, pinned to master: a fork's raw URL has no such file
# until it rebases. See `.github/assets/README.md`.
PROGRESS_BAR_ASSETS = "https://raw.githubusercontent.com/DataDog/integrations-core/master/.github/assets"

# Rendered size of the whole bar, in pixels.
PROGRESS_BAR_WIDTH = 240
PROGRESS_BAR_HEIGHT = 10

PROGRESS_BAR_SEGMENTS = ("passed", "failed", "skipped", "pending")

# Terminal but unfinished, which no other state in a report expresses: the rest derive from `done`.
# A shutdown kind overrides progress.done in a terminal report.
CANCELLED_HEADING = "## 🚫 Dispatcher tests: cancelled"
FAILED_HEADING = "## 🛑 Dispatcher tests: stopped"
TIMED_OUT_HEADING = "## 🛑 Dispatcher tests: timed out"
SHUTDOWN_HEADINGS = {
    ShutdownKind.CANCELLED: CANCELLED_HEADING,
    ShutdownKind.FAILED: FAILED_HEADING,
    ShutdownKind.TIMED_OUT: TIMED_OUT_HEADING,
}
# One short sentence per terminal state. How cancellation propagates and what had been gathered by
# then are Dispatcher's business; the reader needs to know the run ended early, and the report below
# is already whatever it managed to collect.
SHUTDOWN_ALERTS = {
    ShutdownKind.CANCELLED: "The Dispatcher run and its unfinished batches were cancelled.",
    ShutdownKind.TIMED_OUT: "Dispatcher timed out before completion.",
}
# Said instead for a fatal error, the one terminal state that carries something to report.
FAILED_ALERT_LEAD = "Dispatcher stopped before completion:"
# One line is the whole budget for a terminal reason: a traceback would be noise in a comment, and an
# unbounded error string could crowd out the results it is meant to qualify.
SHUTDOWN_REASON_LIMIT = 512

# Said in every report while Dispatcher runs in shadow mode: it does not decide merges yet, so its
# result must not be mistaken for the merge signal.
SHADOW_NOTICE = "> **Dispatcher beta: informational only**\n> Existing CI remains the merge signal."

# Blocks are joined by a blank line, so each one costs two bytes beyond its own length. Newlines are
# one byte in UTF-8, so this is the same number in either unit.
SECTION_SEPARATOR = 2

# Room held back for the truncation notice before any target row competes for the budget, so the one
# line admitting that rows were dropped can never itself be what the dropping removes.
TRUNCATION_RESERVE = 160

# How far below GitHub's own limit the last tier packs. That tier is reached either because the
# report does not fit or because GitHub refused a body this module measured as fitting — its limit is
# stated in characters and measured here in bytes, so the two can disagree. Packing to the same
# number would hand the reporter back the body it was just refused.
REJECTION_HEADROOM = 4096

# What a reader investigating a failure needs from a collection problem: which stage failed to hand
# over what, in their vocabulary rather than the gatherer's.
PROGRESS_ERROR_TEXT = {
    ProgressError.TIMED_OUT: "timed out",
    ProgressError.NO_JOB_RESULTS: "test results could not be collected",
    ProgressError.NO_ARTIFACTS: "artifacts could not be downloaded",
}

# A batch that failed somewhere no target's job covers: a setup step, an upload, the workflow itself.
BATCH_FAILURE_TEXT = "failed outside its integration test jobs"

# Introduces the one group-level list there is. Only tests that failed in every single target of the
# group go under it, so any target's failures are this list plus that target's own additional ones.
COMMON_TESTS_LEAD = "Tests failed in every target:"

# The alert explains that unfinished results keep updating; the footer links to the run.
ALERT_RUNNING_NOTE = "This comment updates automatically."

# Prepended to the run summary when the pull-request comment could not be written. The run summary is
# then the only place the result exists, so it says so rather than looking like the intended surface.
RUN_SUMMARY_COMMENT_FAILED_NOTE = (
    "> [!WARNING]\n"
    "> **The pull request comment could not be updated.** This summary is the full report.\n"
    "> See the workflow logs for why the comment write failed."
)

# Emoji-only chips: the batch strip is one line, so a batch's state has to fit in one glyph.
STATUS_CHIP = {
    Status.SUCCESS: "✅",
    Status.FAILURE: "❌",
    Status.SKIPPED: "⏭️",
}


class DetailLevel(Enum):
    """How much of each target's diagnosis a report carries, largest first.

    The only thing that moves a report down this ladder is the byte limit, and it moves the whole
    report at once: a reader must never be left guessing whether an integration without test names
    had none or merely rendered after one that kept them. A target's job link is what the reader came
    for, so the names go first and the links go last.
    """

    FULL = auto()
    COMPACT = auto()
    TRUNCATED = auto()


def _size(text: str) -> int:
    """UTF-8 byte length: the unit the client's guard measures, so the budget measures it too."""
    return len(text.encode("utf-8"))


def _plural(count: int, noun: str, *, suffix: str = "s") -> str:
    return f"{count} {noun}{suffix if count != 1 else ''}"


def _code(text: str) -> str:
    """A Markdown code span around arbitrary text, fenced wide enough to survive its own backticks.

    Test ids and workflow step names come from outside. A single-backtick span would end early on the
    first backtick in one and let the rest of it render as markup, so the fence is always longer than
    the longest run inside it. HTML in a code span renders as literal text, so nothing else is needed.
    """
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    # A span may neither open nor close on a backtick; one space of padding is stripped on render.
    padding = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{padding}{text}{padding}{fence}"


def render_comment(
    progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None, now: datetime | None = None
) -> str:
    """The report, at the most detail that fits GitHub's limit.

    The tiers are walked here rather than only on a rejection, so local measurement and a refusal
    from GitHub degrade through the same structure instead of through two. The message's `revision`
    is deliberately not rendered: internal ordering metadata, already logged. `now` fixes the
    footer's log-link window, so tiers from one snapshot render identically.
    """
    body = _render(progress, DetailLevel.FULL, shutdown=shutdown, now=now)
    for level in (DetailLevel.COMPACT, DetailLevel.TRUNCATED):
        if _size(body) <= COMMENT_BODY_LIMIT:
            return body
        body = _render(progress, level, shutdown=shutdown, now=now)
    # The last tier packs its rows against the real budget, so it fits by construction.
    return body


def render_compact_comment(
    progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None, now: datetime | None = None
) -> str:
    """Every target keeps its row and its link, and no failure is named. For the rejection path."""
    return _render(progress, DetailLevel.COMPACT, shutdown=shutdown, now=now)


def render_truncated_comment(
    progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None, now: datetime | None = None
) -> str:
    """As many linked target rows as the budget holds, and a notice counting the rest."""
    return _render(progress, DetailLevel.TRUNCATED, shutdown=shutdown, now=now)


def _render(
    progress: DispatcherProgress,
    level: DetailLevel,
    *,
    shutdown: ShutdownRequest | None = None,
    now: datetime | None = None,
) -> str:
    """Assemble one report: the header, the affected integrations, then the footer.

    Every state uses this order. A section is absent when it has nothing to report and never moves,
    so a queued run and a failed one differ in what they say rather than in where they say it.
    """
    header = _header(progress, shutdown=shutdown)
    footer = _footer(progress, shutdown=shutdown, now=now)

    # The header and footer always survive; only the affected integrations are budgeted, and only the
    # last tier spends that budget. Two newlines join every block, so each costs its own separator.
    limit = COMMENT_BODY_LIMIT - (REJECTION_HEADROOM if level is DetailLevel.TRUNCATED else 0)
    remaining = limit - _size(header) - _size(footer) - 2 * SECTION_SEPARATOR
    affected = _affected(progress, remaining, level=level)
    blocks = [header, footer] if affected is None else [header, affected, footer]
    return "\n\n".join(blocks)


def render_shutdown_notice(request: ShutdownRequest, *, now: datetime | None = None) -> str:
    """Render a terminal notice when no progress snapshot exists."""
    blocks = [COMMENT_MARKER, SHUTDOWN_HEADINGS[request.kind], SHADOW_NOTICE, _shutdown_alert(request)]
    blocks.append(_footer(None, shutdown=request, now=now))
    return "\n\n".join(blocks)


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


def summary_line(progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None) -> str:
    """Summarize progress and its terminal state for logs."""
    if shutdown is None:
        state = "complete" if progress.done else "in progress"
    else:
        state = f"stopped ({shutdown.kind.value})"
    return (
        f"Dispatcher tests {state}: {progress.complete}/{progress.total} jobs, "
        f"{progress.passed} passed, {progress.failed} failed, {progress.skipped} skipped"
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------


def _header(progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None) -> str:
    """Marker, heading, notice, alert, totals and the batch strip: never truncated."""
    blocks = [COMMENT_MARKER, _heading(progress, shutdown=shutdown), SHADOW_NOTICE]
    alert = _alert(progress, shutdown=shutdown)
    if alert is not None:
        blocks.append(alert)
    blocks.append(_totals(progress))
    blocks.append(_batch_strip(progress))
    return "\n\n".join(blocks)


def _heading(progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None) -> str:
    """The run's outcome in one line. A failure outranks an uncollected result, which outranks a pass."""
    if shutdown is not None:
        return SHUTDOWN_HEADINGS[shutdown.kind]
    if not progress.done:
        return "## 🔄 Dispatcher tests: in progress"
    if _has_failure(progress):
        return "## ❌ Dispatcher tests: failed"
    if any(_uncollected_counts(progress)):
        return "## ⚠️ Dispatcher tests: results incomplete"
    return "## ✅ Dispatcher tests: passed"


def _alert(progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None) -> str | None:
    """A native GitHub alert, so an unfinished run cannot be mistaken for a final one at a glance.

    A terminal failure is counted in integrations, because that is the unit the failures below are
    grouped into, and only the integrations that really failed are counted: a group holding nothing
    but uncollected results is rendered as a warning, so counting it here would contradict the body.
    A workflow that passed while its reports went missing is a report-completeness problem rather
    than a test failure, so it gets its own sentence in its own unit.
    """
    if shutdown is not None:
        return _shutdown_alert(shutdown)
    if not progress.done:
        phase = "Tests finished; collecting results." if _collecting_results(progress) else "Tests are still running."
        return f"> [!NOTE]\n> **{phase}** {_outstanding(progress)} {ALERT_RUNNING_NOTE}"

    uncollected = _uncollected_sentences(progress)
    if _has_failure(progress):
        groups = sum(1 for group in _failure_groups(progress) if group.failed)
        if groups:
            lead = f"**{_plural(groups, 'integration')} failed.** {progress.failed} of {progress.total} jobs failed."
        else:
            # A batch's workflow failed with nothing failing inside it: there is no integration to
            # name. A job count would read as "0 of N jobs failed", so the body is where to look.
            lead = "**Dispatcher tests failed.** See the failures below."
        return f"> [!CAUTION]\n> {' '.join([lead, *uncollected])}"

    if uncollected:
        # Deliberately not a CAUTION: nothing failed, and there is no failures section to send anyone to.
        return f"> [!WARNING]\n> {' '.join(['**Results are incomplete.**', *uncollected])}"
    return None


def _collecting_results(progress: DispatcherProgress) -> bool:
    return any(batch.state is ExecutionState.ARTIFACT_DOWNLOAD for batch in progress.batches) and all(
        batch.state in (ExecutionState.ARTIFACT_DOWNLOAD, ExecutionState.FINISHED) for batch in progress.batches
    )


def _uncollected_counts(progress: DispatcherProgress) -> tuple[int, int]:
    """Targets, then batches, whose results Dispatcher could not collect.

    Counted apart and never summed: a target is one configuration of one integration and a batch is a
    whole workflow, so a single number spanning both would describe nothing a reader could act on.
    """
    targets = sum(1 for job in _jobs(progress) if job.latest is not None and job.latest.error is not None)
    # The same rule the batch notes use, so the header cannot count a problem the rows below explain.
    batches = sum(1 for batch in progress.batches if batch.error is not None and not _batch_error_is_explained(batch))
    return targets, batches


def _uncollected_sentences(progress: DispatcherProgress) -> list[str]:
    """What could not be collected, one sentence per unit, in the reader's terms."""
    targets, batches = _uncollected_counts(progress)
    sentences = []
    if targets:
        sentences.append(f"Dispatcher could not collect test results for {_plural(targets, 'target')}.")
    if batches:
        sentences.append(f"Dispatcher could not collect results for {_plural(batches, 'batch', suffix='es')}.")
    return sentences


def _outstanding(progress: DispatcherProgress) -> str:
    """What is left to do, counted in batches because they are the unit that actually finishes.

    A retrying batch has every job reported while the batch runs on, so a pending-jobs count alone can
    read as `0` on a run that is far from done.
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
    """The bar, and the counts behind it as a paragraph of its own.

    A zero is left out rather than printed: a queued run reads as "855 pending", not as three zeroes
    with the pending count hidden at the end of them.
    """
    counts = []
    if progress.passed:
        counts.append(f"✅ {progress.passed} passed")
    if progress.failed:
        counts.append(f"❌ {progress.failed} failed")
    if progress.skipped:
        counts.append(f"⏭️ {progress.skipped} skipped")
    pending = progress.total - progress.complete
    if pending:
        counts.append(f"⏳ {pending} pending")
    # Only worth saying once the run is over, and only when it is the whole truth: alongside results
    # that never arrived, "nothing failed" is what a reader would remember and it would be wrong.
    if progress.done and not _has_failure(progress) and not any(_uncollected_counts(progress)):
        counts.append("nothing failed")

    # A non-breaking space, so Markdown does not collapse the gap after the bar.
    jobs = f"{_progress_bar(progress)}&nbsp; **{progress.complete}/{progress.total} jobs**"
    return f"{jobs}\n\n{' · '.join(counts)}" if counts else jobs


def _progress_bar(progress: DispatcherProgress) -> str:
    """One image per segment, scaled by `width`, and nothing at all when no job was planned."""
    pending = progress.total - progress.complete
    # Every job in a retrying batch has reported, so `complete == total` is reachable while the run is
    # unfinished, and a full bar there would contradict the heading next to it.
    if not progress.done and not pending and not _collecting_results(progress):
        pending = 1

    counts = (progress.passed, progress.failed, progress.skipped, pending)
    total = max(progress.total, sum(counts))
    if total <= 0:
        return ""

    # No whitespace between the tags: markdown renders it as a gap in the middle of the bar.
    return "".join(
        f'<img src="{PROGRESS_BAR_ASSETS}/progress-{segment}.png" '
        f'width="{width}" height="{PROGRESS_BAR_HEIGHT}" alt="">'
        for segment, width in zip(PROGRESS_BAR_SEGMENTS, _segment_widths(counts, total), strict=True)
        if width
    )


def _segment_widths(counts: tuple[int, ...], total: int) -> list[int]:
    """Pixel width per segment, summing to exactly `PROGRESS_BAR_WIDTH`."""
    widths = [round(PROGRESS_BAR_WIDTH * count / total) for count in counts]
    # A segment rounded down to nothing would erase a result, such as one failure among hundreds.
    for index, count in enumerate(counts):
        if count and not widths[index]:
            widths[index] = 1

    # That floor and the rounding both drift, so the widest segment absorbs the difference.
    drift = PROGRESS_BAR_WIDTH - sum(widths)
    if drift:
        widest = widths.index(max(widths))
        widths[widest] = max(1, widths[widest] + drift)
    return widths


def _batch_strip(progress: DispatcherProgress) -> str:
    """Every batch on one line, including the ones that have not started.

    Batch state is secondary to the failures below it, so it gets a line rather than a table: a reader
    who wants a batch wants its link, and a reader who wants a failure wants it out of the way.
    """
    if not progress.batches:
        return "_No batches were planned._"

    entries = []
    for batch in progress.batches:
        done = sum(job.complete for job in batch.jobs_progress)
        entries.append(f"{_batch_chip(batch)} {_batch_link(batch)} {done}/{len(batch.jobs_progress)}")

    strip = f"Batches · {' · '.join(entries)}"
    # Said once at the end rather than against each batch: before dispatch it is true of all of them.
    if any(batch.workflow_url is None for batch in progress.batches):
        strip += " — *links available after dispatch*"
    return strip


def _batch_link(batch: BatchProgress) -> str:
    """The batch id, linked to its workflow run once there is one to link to."""
    if batch.workflow_url is None:
        return _code(batch.batch_id)
    return f"[{batch.batch_id}]({batch.workflow_url})"


def _batch_chip(batch: BatchProgress) -> str:
    """The batch's state, in one glyph.

    `status` is taken verbatim, never re-derived from `jobs_progress`: it is the workflow's own
    conclusion, so a batch can be failed while every job inside it passed (a setup or upload step).
    Rolling the jobs up here would render that batch as passed and hide a real failure.
    """
    if batch.state is ExecutionState.ARTIFACT_DOWNLOAD:
        return "📥"
    if batch.state is ExecutionState.FINISHED:
        chip = STATUS_CHIP.get(batch.status) if batch.status is not None else None
        return chip if chip is not None else "❔"
    # A rerun is Dispatcher's own business, so at the batch level it is simply unfinished work. Which
    # jobs were retried is reported per job, where it is actionable.
    if batch.state in (ExecutionState.RUNNING, ExecutionState.RETRYING):
        return "🔄"
    return "⏳"


# ---------------------------------------------------------------------------
# Affected integrations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FailedTarget:
    """One of an integration's targets that failed or whose results could not be collected.

    The batch travels with the job because a group spans batches: an integration's targets are
    partitioned across them, and the batch is what a reader needs in order to open the right run.
    """

    job: JobProgress
    attempt: JobAttemptProgress
    batch_id: str


@dataclass(frozen=True)
class FailureGroup:
    """Every affected target of one integration, whichever way it was affected."""

    integration: str
    targets: tuple[FailedTarget, ...]

    @property
    def failed_targets(self) -> tuple[FailedTarget, ...]:
        """The targets that actually failed.

        A target that failed and also lost its reports belongs here and nowhere else: its own row
        carries the collection problem, so counting it in both would inflate the group.
        """
        return tuple(target for target in self.targets if target.attempt.status is Status.FAILURE)

    @property
    def unavailable_targets(self) -> tuple[FailedTarget, ...]:
        """The targets that did not fail and whose results never arrived either."""
        return tuple(target for target in self.targets if target.attempt.status is not Status.FAILURE)

    @property
    def failed(self) -> bool:
        """Whether anything here actually failed, as opposed to never reporting a result.

        A group holds both kinds, so the two must not be conflated: a job can conclude `success`
        and still carry an error, because its status is the workflow's conclusion while its error
        says whether the Dispatcher managed to collect its results afterwards. Counting such a
        target as a failure claims the integration is broken on evidence that never arrived.
        """
        return bool(self.failed_targets)


def _failure_groups(progress: DispatcherProgress) -> list[FailureGroup]:
    """One group per integration with something to answer for, worst first.

    An uncollected result joins its integration's group rather than getting a section of its own: it
    is the same question ("is this integration broken?") with the answer missing, and splitting the
    two sent a reader to two places to find out about one integration.
    """
    grouped: dict[str, list[FailedTarget]] = {}
    for batch, job in _jobs_with_batches(progress):
        attempt = job.latest
        if attempt is None or (attempt.status is not Status.FAILURE and attempt.error is None):
            continue
        grouped.setdefault(job.job.target, []).append(FailedTarget(job, attempt, batch.batch_id))

    groups = [FailureGroup(integration, tuple(targets)) for integration, targets in grouped.items()]
    # Real failures first, then most affected targets, then by name so two runs of the same shape
    # render the same way. Groups holding only uncollected results sort last: they are not
    # actionable, so they must never displace a failure from the rows a truncated report keeps.
    groups.sort(key=lambda group: (not group.failed, -len(group.targets), group.integration))
    return groups


def _affected(progress: DispatcherProgress, budget: int, *, level: DetailLevel) -> str | None:
    """The affected integrations, then whatever went wrong outside any one of them."""
    groups = _failure_groups(progress)
    notes = _batch_notes(progress)
    if not groups and not notes:
        return None

    if level is DetailLevel.TRUNCATED:
        # The notes are the only account of a problem no target row carries, and the notice the only
        # account of the rows that were dropped, so both are paid for before a row competes for
        # anything. A body that dropped either would read as complete while it was not.
        reserved = sum(_size(note) + SECTION_SEPARATOR for note in notes) + TRUNCATION_RESERVE
        blocks = _truncated_groups(groups, budget - reserved)
    else:
        blocks = [_disclosure(group, _group_body(group, level=level)) for group in groups]

    return "\n\n".join([*blocks, *notes])


def _truncated_groups(groups: list[FailureGroup], budget: int) -> list[str]:
    """As many linked target rows as *budget* holds, taken in order, and a notice counting the rest.

    Rows are what the budget is spent on, because the link on each one is the report's primary
    information. A group renders only once one of its rows is kept, so its markup is never what
    displaced another integration's row.
    """
    shown = 0
    blocks = []
    for group in groups:
        # The disclosure's own markup is charged to the first row that survives inside it.
        overhead = _size(_disclosure(group, "")) + SECTION_SEPARATOR
        kept: list[str] = []
        for row in _target_rows(group, level=DetailLevel.TRUNCATED):
            cost = _size(row) + (1 if kept else overhead)
            if cost > budget:
                break
            kept.append(row)
            budget -= cost
        if not kept:
            break
        blocks.append(_disclosure(group, "\n".join(kept)))
        shown += len(kept)

    total = sum(len(group.targets) for group in groups)
    if shown == total:
        return blocks

    notice = (
        f"Showing {shown} of {total} affected targets. Open the failed batch links for the remaining {total - shown}."
    )
    return [notice, *blocks]


def _disclosure(group: FailureGroup, body: str) -> str:
    """The group's summary, and whichever of its rows *body* holds.

    The blank line after `</summary>` is load-bearing: without it GitHub does not parse the Markdown
    inside the disclosure, and the rows render as one run-on line of literal text.
    """
    summary = f"{_group_chip(group)} <code>{html.escape(group.integration)}</code>: {_group_counts(group)}"
    return f"<details>\n<summary>{summary}</summary>\n\n{body}\n\n</details>"


def _group_chip(group: FailureGroup) -> str:
    """A group with a real failure is a failure; one with only missing results is a warning."""
    return "❌" if group.failed else "⚠️"


def _group_counts(group: FailureGroup) -> str:
    """The group's outcomes, each in the unit it is actually in.

    Not a test count: a test count over a group whose targets failed differently says nothing about
    any one of them, and it would put a number nobody navigates by where the outcome belongs.
    """
    failed = len(group.failed_targets)
    unavailable = len(group.unavailable_targets)
    if failed and unavailable:
        return f"{_plural(failed, 'failed target')}, {_plural(unavailable, 'result')} unavailable"
    if failed:
        return _plural(failed, "failed target")
    return f"{'results' if unavailable > 1 else 'result'} unavailable for {_plural(unavailable, 'target')}"


def _group_body(group: FailureGroup, *, level: DetailLevel) -> str:
    """A row per affected target, and the tests every one of them failed, where there are any."""
    paragraphs = ["\n".join(_target_rows(group, level=level))]
    if level is DetailLevel.FULL and (common := _common_tests(group)):
        paragraphs.append("\n".join([COMMON_TESTS_LEAD, *[f"- {_code(test)}" for test in common]]))
    return "\n\n".join(paragraphs)


def _target_rows(group: FailureGroup, *, level: DetailLevel) -> list[str]:
    """One row per target, in the order the batches reported them.

    Never folded onto a shared line, whatever the count: the link on a row is how a reader opens the
    run that failed, and a group of thirty targets is exactly the case where they need it most.
    """
    common = _common_tests(group) if level is DetailLevel.FULL else []
    return [_target_row(target, common=common, level=level) for target in group.targets]


def _target_row(target: FailedTarget, *, common: list[str], level: DetailLevel) -> str:
    """One target: its link, its batch, what happened to it, and the names that explain it."""
    head, listed = _target_detail(target, common=common, level=level)
    if target.attempt.error is not None:
        # Said against the target rather than once for the whole group: a reason detached from the
        # links it applies to leaves a reader matching up two lists.
        error = PROGRESS_ERROR_TEXT[target.attempt.error]
        head = f"{head} · {error}" if head else error

    row = f"- {_target_link(target)} · {target.batch_id}"
    if head:
        row += f" · {head}"
    return "\n".join([row, *listed])


def _target_detail(target: FailedTarget, *, common: list[str], level: DetailLevel) -> tuple[str | None, list[str]]:
    """What explains this target: the phrase for its own row, and the names listed beneath it.

    Its own failures, never the group's: a name under a target is a claim that this target failed it.
    Whatever the whole group shares is subtracted here and said once below every row instead, and
    what remains is labelled additional, because a remainder of one would otherwise read as the
    target's only failure. Below the first level the names go and only the kind of failure is left,
    which is what a row needs in order to say more than that something happened.
    """
    named = level is DetailLevel.FULL
    if tests := _target_tests(target):
        if not named:
            return "tests failed", []
        remaining = [test for test in tests if test not in common]
        if not remaining:
            return None, []
        if common:
            return _plural(len(remaining), "additional failed test"), _sub_bullets(remaining)
        if len(remaining) == 1:
            return f"test {_code(remaining[0])}", []
        return _plural(len(remaining), "failed test"), _sub_bullets(remaining)

    # Only when no test explains the target: the step that ran a failing test says nothing the test
    # does not, and the step that collected artifacts says nothing about the integration.
    if steps := list(target.attempt.failed_steps):
        if not named:
            return "workflow step failed", []
        if len(steps) == 1:
            return f"step {_code(steps[0])}", []
        return _plural(len(steps), "failed step"), _sub_bullets(steps)
    return None, []


def _sub_bullets(names: list[str]) -> list[str]:
    """Names indented under the row they belong to, so the association survives the nesting."""
    return [f"  - {_code(name)}" for name in names]


def _common_tests(group: FailureGroup) -> list[str]:
    """The tests that failed in every one of the group's targets, when it is honest to say so.

    The one list allowed above the target level, and only because it is lossless: any target's
    failures are this list plus that target's own additional ones. It takes two targets to have
    something in common, and established reports from all of them to claim every target failed
    something — a target that lost its artifacts or failed a step has no test list to intersect, so
    the whole group keeps its tests where they are.
    """
    if len(group.targets) < 2:
        return []

    per_target = []
    for target in group.targets:
        tests = _target_tests(target)
        if target.attempt.error is not None or not tests:
            return []
        per_target.append(tests)

    shared = set(per_target[0]).intersection(*per_target[1:])
    # First-seen order, so two runs of the same shape list them the same way.
    return [test for test in per_target[0] if test in shared]


def _target_link(target: FailedTarget) -> str:
    label = _code(_target_label(target.job))
    return f"[{label}]({target.attempt.job_url})" if target.attempt.job_url else label


def _target_tests(target: FailedTarget) -> list[str]:
    """This target's failed tests as fully qualified ids, in report order."""
    return [f"{case.classname}::{case.name}" for case in target.attempt.failed_tests]


def _batch_notes(progress: DispatcherProgress) -> list[str]:
    """What went wrong at the batch level, which no target's row can account for."""
    notes = []
    for batch in progress.batches:
        # A batch whose workflow failed with nothing failing inside it is a real failure with nothing
        # to group; saying so beats a silent omission.
        if (
            batch.status is Status.FAILURE
            and all(job.complete for job in batch.jobs_progress)
            and not any(_is_failed(job) for job in batch.jobs_progress)
        ):
            notes.append(f"❌ {_batch_note_link(batch)}: {BATCH_FAILURE_TEXT}")
        if batch.error is not None and not _batch_error_is_explained(batch):
            notes.append(f"⚠️ {_batch_note_link(batch)}: {PROGRESS_ERROR_TEXT[batch.error]}")
    return notes


def _batch_error_is_explained(batch: BatchProgress) -> bool:
    """Whether a target of this batch already reports the batch's own collection problem.

    One problem, one explanation: that is the same event seen at two levels, and the target's row
    carries a job link, so the row is the account that survives. A *different* problem is not the
    same event, so a batch that timed out is still news when a target of it lost its artifacts.
    """
    return any(job.latest is not None and job.latest.error is batch.error for job in batch.jobs_progress)


def _batch_note_link(batch: BatchProgress) -> str:
    """The batch a note is about, linked to its run: the note is where a reader acts on it."""
    label = _code(batch.batch_id)
    return f"[{label}]({batch.workflow_url})" if batch.workflow_url is not None else label


# ---------------------------------------------------------------------------
# Footer and shared helpers
# ---------------------------------------------------------------------------


def _shutdown_alert(request: ShutdownRequest) -> str:
    """Say that the run ended early, in one line."""
    if request.kind is ShutdownKind.FAILED:
        return f"> [!CAUTION]\n> {FAILED_ALERT_LEAD} {_shutdown_reason(request)}."
    return f"> [!CAUTION]\n> {SHUTDOWN_ALERTS[request.kind]}"


def _shutdown_reason(request: ShutdownRequest) -> str:
    """Render a bounded reason as literal Markdown, including embedded backticks."""
    reason = " ".join(str(request.error).split())
    if len(reason) > SHUTDOWN_REASON_LIMIT:
        reason = reason[: SHUTDOWN_REASON_LIMIT - 3].rstrip() + "..."
    return _code(reason)


def _footer(
    progress: DispatcherProgress | None,
    *,
    shutdown: ShutdownRequest | None = None,
    now: datetime | None = None,
) -> str:
    """Whether this is the last word, and where the run that produced it lives.

    No status emoji on a finished run: the outcome is the heading's job, and a ✅ here read as "all
    good" on a run that had failed. What a reader cannot get anywhere else in the comment is which
    commit was tested and where Dispatcher itself ran, so that is what this says.
    """
    if shutdown is not None:
        note = f"Dispatcher {shutdown.kind.value}"
    elif progress is None or not progress.done:
        note = "⏳ Dispatcher running"
    else:
        note = "Dispatcher finished"
    if sha := get_commit_sha():
        note += f" on {_code(sha)}"
    # Links to where the run can be inspected, each omitted when the environment cannot identify it.
    links = []
    if run_url := get_workflow_run_url():
        links.append(f"[GitHub Run]({run_url})")
    if logs_url := get_dispatcher_logs_url(
        terminal=shutdown is not None or (progress is not None and progress.done), now=now
    ):
        links.append(f"[Dispatcher Logs]({logs_url})")
    if links:
        note += f" — {' · '.join(links)}"
    return f"<sub>{note}.</sub>"


def _jobs(progress: DispatcherProgress) -> Iterator[JobProgress]:
    return (job for batch in progress.batches for job in batch.jobs_progress)


def _jobs_with_batches(progress: DispatcherProgress) -> Iterator[tuple[BatchProgress, JobProgress]]:
    return ((batch, job) for batch in progress.batches for job in batch.jobs_progress)


def _is_failed(job: JobProgress) -> bool:
    return job.latest is not None and job.latest.status is Status.FAILURE


def _has_failure(progress: DispatcherProgress) -> bool:
    """Whether the run has a failure to answer for.

    A batch's own `FAILURE` counts, since a workflow can fail with nothing inside it failing. An
    *error* does not: an uncollected result reads as incomplete, so the heading never claims a
    failure with nothing to show for it.
    """
    return progress.failed > 0 or any(batch.status is Status.FAILURE for batch in progress.batches)


def _target_label(job: JobProgress) -> str:
    """A target within its integration: the integration's own name is the group it sits in.

    A target that defines no environments contributes no segment rather than an empty one, so the
    label never opens with a stray separator.
    """
    parts = [part for part in (job.job.environment, str(job.job.platform)) if part]
    # Only the base package variant separates a replica from its ordinary job.
    if job.job.minimum_base_package:
        parts.append("minimum base package")
    return " / ".join(parts)
