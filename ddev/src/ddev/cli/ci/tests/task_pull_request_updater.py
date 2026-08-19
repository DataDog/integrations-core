# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from ddev.cli.ci.tests.pr_comment import (
    COMMENT_MARKER,
    render_comment,
    render_compact_comment,
    render_minimal_comment,
    render_run_summary,
    summary_line,
)
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_actions import write_step_summary
from ddev.utils.github_errors import GitHubBodyTooLongError

if TYPE_CHECKING:
    from collections.abc import Callable

    from ddev.cli.ci.tests.messages import UpdatePRComment
    from ddev.utils.github_async import AsyncGitHubClient

# Editing the tracked comment can fail because it is not ours to edit (403) or no longer exists
# (404). Neither improves on retry, but both are recoverable by writing a comment we do own.
UNUSABLE_COMMENT_STATUSES = (403, 404)

# Enough passes for everything a failed write can change about the next one: two steps down the
# comment tiers, and giving up on a comment we may not edit. The latter can repeat, because the
# comment we create to replace the first can itself be refused, so the cap is what stops that
# becoming a loop. One more than the sum, for the pass that finally lands.
MAX_WRITE_PASSES = 5


@dataclass(frozen=True)
class PullRequestUpdaterOptions:
    """Configuration for a ``TaskPullRequestUpdater``.

    ``pr_number`` is ``None`` for the runs that have no pull request to comment on — a push to
    ``master``, the nightly schedule, and merge-queue runs. Those report to the run summary only.
    """

    owner: str
    repo: str
    pr_number: int | None


class TaskPullRequestUpdater(AsyncProcessor["UpdatePRComment"]):
    """Projects ``DispatcherProgress`` snapshots onto one pull-request comment and the run summary.

    A serialized, stateless projection: it consumes no runner messages, merges no deltas, computes
    no retries, and calls no GitHub API beyond the single comment it owns. It renders the newest
    snapshot and ignores stale revisions, so neither surface can regress.

    Two destinations for one report. The pull-request comment is optional — there is no pull request
    on a ``master`` push, the nightly schedule, or a merge-queue run — while the run summary is
    written on every run once the last batch finishes, so opening the workflow always shows the final
    result. ``latest_body`` keeps the newest rendered report for the caller to persist as a workflow
    output.

    Because the run summary always reports, **failing to write the comment never fails the run**. A
    reporting problem is logged, recorded, and announced at the top of the run summary; it does not
    cost anyone the test results. Transient failures are not retried here either: retrying is the
    GitHub client's job, so that one retry strategy covers every caller.

    The comment is found or created once, by ``COMMENT_MARKER``, so a later Dispatcher run on the
    same pull request edits the existing comment instead of adding another. The marker identifies the
    comment but does not prove we own it — anyone can paste it, and quoting our comment copies it —
    so an edit that GitHub refuses is treated as "not our comment" and recovered from, rather than
    trusted and retried.

    Ordering is guaranteed within one Dispatcher execution, which the design assumes is the only one
    running: "One active Dispatcher execution per PR is a hard precondition enforced by workflow
    concurrency." Two concurrent executions would each keep their own revision counter and could
    still fight over the comment; coordinating them is deliberately out of scope.

    This is a terminal consumer: it emits no further messages.
    """

    def __init__(self, name: str, client: AsyncGitHubClient, options: PullRequestUpdaterOptions):
        super().__init__(name)
        self._client = client
        self._options = options
        self._comment_id: int | None = None
        # Comments GitHub refused to let us edit. Forgetting the id alone is not enough: the marker
        # lookup would find the same comment again on the next attempt and retry the same refusal.
        self._unusable_comment_ids: set[int] = set()
        # Revisions start at 0 (the initial plan), so nothing can have been rendered yet.
        self._latest_revision = -1
        self._latest_body: str | None = None
        self._pr_comment_failed = False
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    @property
    def latest_body(self) -> str | None:
        """The newest report rendered, or ``None`` if no snapshot has arrived yet.

        Retained whether or not it reached GitHub, so the caller can persist it as a workflow output
        for later steps to publish. For a run with no pull request this is the only report there is.
        """
        return self._latest_body

    @property
    def pr_comment_failed(self) -> bool:
        """Whether the newest report failed to reach its pull-request comment."""
        return self._pr_comment_failed

    async def process_message(self, message: UpdatePRComment):
        # Rendering is pure, so it happens outside the lock.
        body = render_comment(message.progress)
        log_extra = {"revision": message.revision, "done": message.progress.done}

        # The lock spans revision validation, the write and the retained report, all of which may
        # only move forwards. Batches finish concurrently, so without this a slow early revision
        # could overwrite a later one and make the report go backwards.
        async with self._lock:
            if message.revision <= self._latest_revision:
                self._logger.info(
                    "Stale UpdatePRComment ignored (latest rendered is %s)", self._latest_revision, extra=log_extra
                )
                return

            pr_number = self._options.pr_number
            if pr_number is None:
                self._logger.info("No pull request to update: %s", summary_line(message.progress), extra=log_extra)
            else:
                self._pr_comment_failed = not await self._write(pr_number, message, body, log_extra)

            # Retained even when the write failed: this is the newest report we have, and the run
            # summary below is about to report it regardless. The revision advances with it, so a
            # later snapshot cannot be overtaken by an earlier one that is still in flight.
            self._latest_body = body
            self._latest_revision = message.revision

            if message.progress.done:
                self._write_run_summary(body, log_extra)

    def _write_run_summary(self, body: str, log_extra: dict[str, object]):
        """Publish the final report to the run's job summary, the panel shown on the run page.

        Every run reports here, so a run with no pull request still has a result to open, and one
        whose comment could not be written still has somewhere that says so. A no-op outside GitHub
        Actions, and never a reason to fail: ``write_step_summary`` swallows an unwritable file.
        """
        write_step_summary(render_run_summary(body, pr_comment_failed=self._pr_comment_failed))
        self._logger.info("Run summary written", extra={**log_extra, "pr_comment_failed": self._pr_comment_failed})

    async def _write(self, pr_number: int, message: UpdatePRComment, body: str, log_extra: dict[str, object]) -> bool:
        """Write *body* to the comment, stepping down the tiers if it is too long. Did it land?

        Not a retry loop — a failure that a further pass cannot change stops immediately. Each pass
        continues only after changing what the next one will do: dropping to a smaller tier, or
        forgetting a comment GitHub will not let us edit so the next pass creates our own.

        The tiers are rendered lazily because shrinking is the exception. Both ways of learning a body
        is too long arrive as ``GitHubBodyTooLongError``: the client measures it before spending a
        request, and converts GitHub's own 422 into the same error. So there is one thing to catch and
        one action to take, and no 422 payload to parse here.

        Worth knowing which of the two actually drives this. The renderer budgets against the same
        limit the client enforces and truncates itself to fit, so the pre-flight measurement rarely
        fires. The tiers are really there for GitHub disagreeing -- refusing a body we measured as
        fitting, because its accounting is undocumented and not something we can reproduce locally.

        Losing the write does not fail the run. The report is retained and the run summary reports it
        with a note saying the comment could not be updated.
        """
        tiers: tuple[Callable[[], str], ...] = (
            lambda: body,
            lambda: render_compact_comment(message.progress),
            lambda: render_minimal_comment(message.progress),
        )
        tier, rendered = 0, body
        for _ in range(MAX_WRITE_PASSES):
            try:
                await self._submit(pr_number, rendered)
            except GitHubBodyTooLongError as error:
                smaller = _next_distinct_tier(tiers, tier, rendered)
                if smaller is None:
                    # Unreachable while the last tier drops the per-test detail and budgets the rest.
                    # Reported rather than asserted, because a wrong assumption here must not crash.
                    self._logger.error("PR comment too long at every tier: %s", error, extra=log_extra)
                    return False
                tier, rendered = smaller
                self._logger.warning("PR comment body too long (%s); retrying at tier %s", error, tier, extra=log_extra)
            except httpx.HTTPError as error:
                if self._forget_unusable_comment(error, log_extra):
                    # The next pass creates a comment we own, rather than re-editing one we do not.
                    continue
                self._logger.error("PR comment write failed: %s", error, extra=log_extra)
                return False
            else:
                self._logger.info(
                    "PR comment written", extra={**log_extra, "comment_id": self._comment_id, "tier": tier}
                )
                return True

        # Every pass was refused the comment it targeted, including ones we had just created, so
        # there is nothing left to recover to.
        self._logger.error("PR comment write found no comment it may edit", extra=log_extra)
        return False

    async def _submit(self, pr_number: int, body: str):
        """Create the comment on first use, then edit that same comment for every later revision."""
        comment_id = await self._resolve_comment_id(pr_number)
        if comment_id is not None:
            await self._client.update_issue_comment(self._options.owner, self._options.repo, comment_id, body)
            return

        created = await self._client.create_issue_comment(self._options.owner, self._options.repo, pr_number, body)
        self._comment_id = created.data.id

    async def _resolve_comment_id(self, pr_number: int) -> int | None:
        """The tracked comment, else an existing marked one from a previous Dispatcher run."""
        if self._comment_id is not None:
            return self._comment_id

        async for page in self._client.list_issue_comments(self._options.owner, self._options.repo, pr_number):
            for comment in page.data:
                # Only at the start: quoting our comment copies the marker into the quote, and that
                # copy belongs to whoever wrote the reply. A quote is prefixed with "> ", so anchoring
                # here rules it out. It still does not prove ownership — see the 403 recovery.
                if comment.body.startswith(COMMENT_MARKER) and comment.id not in self._unusable_comment_ids:
                    self._comment_id = comment.id
                    return comment.id
        return None

    def _forget_unusable_comment(self, error: httpx.HTTPError, log_extra: dict[str, object]) -> bool:
        """Drop the tracked comment when GitHub says we may not edit it, or it is gone.

        Returns whether anything was forgotten, meaning the next attempt should create instead. The
        marker only identifies a comment; a reviewer can paste it, so the comment it points at may
        belong to someone else. Without this the updater would retry that edit until it gave up, and
        the run would report nothing at all.
        """
        if self._comment_id is None or not isinstance(error, httpx.HTTPStatusError):
            return False
        if error.response.status_code not in UNUSABLE_COMMENT_STATUSES:
            return False

        self._logger.warning(
            "Cannot edit comment %s (%s); creating a new one",
            self._comment_id,
            error.response.status_code,
            extra=log_extra,
        )
        self._unusable_comment_ids.add(self._comment_id)
        self._comment_id = None
        return True


def _next_distinct_tier(tiers: tuple[Callable[[], str], ...], tier: int, current: str) -> tuple[int, str] | None:
    """The next tier that renders something different from *current*, or ``None`` if none does.

    Advancing blindly would waste a pass: a snapshot with no unavailable results and no retried jobs
    makes the compact tier byte-identical to the full one, and resending a body GitHub has just
    refused cannot succeed. So the ladder skips a tier that sheds nothing rather than spending a
    request to discover that.
    """
    for index in range(tier + 1, len(tiers)):
        body = tiers[index]()
        if body != current:
            return index, body
    return None
