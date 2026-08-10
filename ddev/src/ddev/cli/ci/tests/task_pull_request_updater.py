# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from ddev.cli.ci.tests.pr_comment import COMMENT_MARKER, render_comment, render_minimal_comment, summary_line
from ddev.event_bus.exceptions import FatalProcessingError
from ddev.event_bus.orchestrator import AsyncProcessor

if TYPE_CHECKING:
    from ddev.cli.ci.tests.messages import UpdatePRComment
    from ddev.utils.github_async import AsyncGitHubClient

# GitHub rejects an over-long comment body with this status. It is not transient: resending the same
# body fails identically, so the only useful response is to send a smaller one.
BODY_TOO_LONG_STATUS = 422


@dataclass(frozen=True)
class PullRequestUpdaterOptions:
    """Configuration for a ``TaskPullRequestUpdater``.

    ``pr_number`` is ``None`` for the runs that have no pull request to comment on — a push to
    ``master``, the nightly schedule, and merge-queue runs. Those still render, to the log.
    """

    owner: str
    repo: str
    pr_number: int | None
    max_write_attempts: int = 3


class TaskPullRequestUpdater(AsyncProcessor["UpdatePRComment"]):
    """Projects ``DispatcherProgress`` snapshots onto one pull-request comment.

    A serialized, stateless projection: it consumes no runner messages, merges no deltas, computes
    no retries, and calls no GitHub API beyond the single comment it owns. It renders the newest
    snapshot and ignores stale revisions, so the comment can never regress.

    The comment is found or created once, by ``COMMENT_MARKER``, so a re-run of Dispatcher on the
    same pull request edits the existing comment instead of adding another.

    This is a terminal consumer: it emits no further messages.
    """

    def __init__(self, name: str, client: AsyncGitHubClient, options: PullRequestUpdaterOptions) -> None:
        super().__init__(name)
        self._client = client
        self._options = options
        self._comment_id: int | None = None
        # Revisions start at 0 (the initial plan), so nothing can have been rendered yet.
        self._latest_revision = -1
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: UpdatePRComment) -> None:
        # Rendering is pure, so it happens outside the lock.
        body = render_comment(message.progress, revision=message.revision)
        log_extra = {"revision": message.revision, "done": message.progress.done}

        pr_number = self._options.pr_number
        if pr_number is None:
            self._logger.info("No pull request to update: %s", summary_line(message.progress), extra=log_extra)
            return

        # The lock spans revision validation and the write, and the revision advances only after the
        # write lands. Batches finish concurrently, so without this a slow early revision could
        # overwrite a later one and make the comment go backwards.
        async with self._lock:
            if message.revision <= self._latest_revision:
                self._logger.info(
                    "Stale UpdatePRComment ignored (latest rendered is %s)", self._latest_revision, extra=log_extra
                )
                return

            if await self._write(pr_number, message, body, log_extra):
                self._latest_revision = message.revision

    async def _write(self, pr_number: int, message: UpdatePRComment, body: str, log_extra: dict[str, object]) -> bool:
        """Write *body* to the comment, retrying transient failures. Returns whether it landed.

        Losing an intermediate revision is acceptable — the next complete snapshot supersedes it —
        but losing the final one means the run reported nothing, which fails the command.
        """
        for attempt in range(1, self._options.max_write_attempts + 1):
            try:
                await self._submit(pr_number, body)
            except httpx.HTTPError as error:
                if _is_body_too_long(error):
                    # Not transient: the same body would be rejected again.
                    return await self._write_minimal(pr_number, message, log_extra)
                self._logger.warning(
                    "PR comment write failed (attempt %s of %s): %s",
                    attempt,
                    self._options.max_write_attempts,
                    error,
                    extra=log_extra,
                )
            else:
                self._logger.info("PR comment written", extra={**log_extra, "comment_id": self._comment_id})
                return True

        if message.progress.done:
            raise FatalProcessingError(
                f"Could not write the final Dispatcher PR comment after {self._options.max_write_attempts} attempts"
            )
        self._logger.error("Giving up on this revision; the next snapshot supersedes it", extra=log_extra)
        return False

    async def _write_minimal(self, pr_number: int, message: UpdatePRComment, log_extra: dict[str, object]) -> bool:
        """Retry once with a header-and-footer-only body after GitHub rejected the full one."""
        self._logger.warning("PR comment body rejected as too long; retrying without detail", extra=log_extra)
        try:
            await self._submit(pr_number, render_minimal_comment(message.progress, revision=message.revision))
        except httpx.HTTPError as error:
            self._logger.error("Minimal PR comment write also failed: %s", error, extra=log_extra)
            if message.progress.done:
                raise FatalProcessingError("Could not write the final Dispatcher PR comment") from error
            return False
        return True

    async def _submit(self, pr_number: int, body: str) -> None:
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
                # Only Dispatcher writes the marker, so matching it is enough to prove authorship.
                if COMMENT_MARKER in comment.body:
                    self._comment_id = comment.id
                    return comment.id
        return None


def _is_body_too_long(error: httpx.HTTPError) -> bool:
    """Whether *error* is GitHub rejecting the comment body for exceeding its length limit."""
    return isinstance(error, httpx.HTTPStatusError) and error.response.status_code == BODY_TOO_LONG_STATUS
