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
    summary_line,
)
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_errors import GitHubBodyTooLongError

if TYPE_CHECKING:
    from collections.abc import Callable

    from ddev.cli.ci.tests.messages import UpdatePRComment
    from ddev.utils.github_async import AsyncGitHubClient

# Editing the tracked comment can fail because it is not ours to edit (403) or no longer exists
# (404). Neither improves on retry, but both are recoverable by writing a comment we do own.
UNUSABLE_COMMENT_STATUSES = (403, 404)

# Enough passes for everything a failed write can change about the next one: two steps down the
# comment tiers, plus giving up on a comment we may not edit, which can repeat because the
# replacement can itself be refused. One more than the sum, for the pass that lands.
MAX_WRITE_PASSES = 5


@dataclass(frozen=True)
class RunReporterOptions:
    """Configuration for a ``TaskRunReporter``.

    ``pr_number`` is ``None`` for the runs that have no pull request to comment on — a push to
    ``master``, the nightly schedule, and merge-queue runs. Those render to the log and to
    ``latest_body``.
    """

    owner: str
    repo: str
    pr_number: int | None


class TaskRunReporter(AsyncProcessor["UpdatePRComment"]):
    """Reports on a Dispatcher run, by projecting its ``DispatcherProgress`` snapshots onto one report.

    That report goes to a pull-request comment when the run has a pull request, and otherwise only to
    ``latest_body``, for the orchestrator to publish to the GitHub Actions run summary.

    A serialized projection that renders the newest snapshot and ignores stale revisions, so the report
    cannot regress. Ordering holds within one Dispatcher execution, which workflow concurrency
    guarantees is the only one running. Terminal consumer: it emits no further messages.

    **Failing to write the comment never fails the run.** The problem is recorded in
    ``pr_comment_failed`` and the report kept in ``latest_body``, for the orchestrator to publish.
    Transient failures are not retried here — that is the GitHub client's job.

    ``COMMENT_MARKER`` finds the comment, so a later run edits it rather than adding another. It does
    not prove ownership, though, so an edit GitHub refuses means "not our comment".
    """

    def __init__(self, name: str, client: AsyncGitHubClient, options: RunReporterOptions):
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

        Retained whether or not it reached GitHub, and the only report a run without a pull request has.
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

            # Retained even when the write failed: this is the newest report we have, and losing the
            # comment must not lose the results. The revision advances with it, so a later snapshot
            # cannot be overtaken by an earlier one still in flight.
            self._latest_body = body
            self._latest_revision = message.revision

    async def _write(self, pr_number: int, message: UpdatePRComment, body: str, log_extra: dict[str, object]) -> bool:
        """Write *body* to the comment, stepping down the tiers if it is too long. Did it land?

        Not a retry loop: a pass continues only after changing what the next one does — a smaller tier,
        or forgetting a comment GitHub will not let us edit — and stops otherwise. Both ways of learning
        a body is too long arrive as ``GitHubBodyTooLongError``, so there is one thing to catch.
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

        Returns whether anything was forgotten, meaning the next pass should create instead. The marker
        only identifies a comment, so the one it points at may belong to whoever pasted it.
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

    A snapshot with nothing to shed renders the compact tier byte-identical to the full one, and
    resending a body GitHub just refused cannot succeed, so the ladder skips it rather than spending a
    request to find out.
    """
    for index in range(tier + 1, len(tiers)):
        body = tiers[index]()
        if body != current:
            return index, body
    return None
