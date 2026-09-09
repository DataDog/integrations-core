# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

import httpx

from ddev.cli.ci.tests.pr_comment import (
    COMMENT_MARKER,
    render_comment,
    render_compact_comment,
    render_minimal_comment,
    render_shutdown_notice,
    summary_line,
)
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.event_bus.shutdown import ShutdownRequest
from ddev.monitoring import ComponentMonitor
from ddev.utils.github_errors import GitHubBodyTooLongError

if TYPE_CHECKING:
    from ddev.cli.ci.tests.messages import UpdatePRComment
    from ddev.cli.ci.tests.progress import DispatcherProgress
    from ddev.utils.github_async import AsyncGitHubClient

# Replace comments that cannot be edited or no longer exist.
UNUSABLE_COMMENT_STATUSES = (403, 404)

# Allow size fallbacks and comment replacement without retrying indefinitely.
MAX_WRITE_PASSES = 5
# Includes lock acquisition and all terminal write attempts.
SHUTDOWN_WRITE_TIMEOUT = 4.0


class CommentRenderer(Protocol):
    """Renders a whole report from a snapshot. Every tier takes the same arguments."""

    def __call__(self, progress: DispatcherProgress, *, shutdown: ShutdownRequest | None = None) -> str: ...


# Smaller renderings to fall back on, largest first, when a body is refused for being too long.
# Whether one differs from the tier above it depends on the snapshot, so each is compared once rendered.
FALLBACK_TIERS: tuple[CommentRenderer, ...] = (render_compact_comment, render_minimal_comment)


@dataclass(frozen=True)
class RunReporterOptions:
    """Report destination. Without a PR number, reports are retained locally."""

    owner: str
    repo: str
    pr_number: int | None


class TaskRunReporter(AsyncProcessor["UpdatePRComment"]):
    """Render progress snapshots and publish the newest revision to one PR comment.

    Retain the report in ``latest_body``, even without a PR or after a failed write.
    Record publication failures in ``pr_comment_failed``. Writes are serialized
    and stale revisions are ignored within this instance.
    """

    def __init__(
        self,
        name: str,
        client: AsyncGitHubClient,
        options: RunReporterOptions,
        *,
        monitor: ComponentMonitor | None = None,
    ):
        super().__init__(name)
        self._client = client
        self._options = options
        self._comment_id: int | None = None
        # Exclude rejected comments from subsequent marker lookups.
        self._unusable_comment_ids: set[int] = set()
        # The initial plan has revision 0.
        self._latest_revision = -1
        self._latest_body: str | None = None
        self._latest_progress: DispatcherProgress | None = None
        self._pr_comment_failed = False
        self._final_report_published = False
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")
        self.monitor = monitor

    @property
    def latest_body(self) -> str | None:
        """The latest rendered report, retained regardless of publication success."""
        return self._latest_body

    @property
    def pr_comment_failed(self) -> bool:
        """Whether the newest report failed to reach its pull-request comment."""
        return self._pr_comment_failed

    @property
    def final_report_published(self) -> bool:
        """Whether the final report was published, or retained when no PR exists."""
        return self._final_report_published

    async def process_message(self, message: UpdatePRComment):
        # Rendering is pure, so it happens outside the lock.
        body = render_comment(message.progress)
        log_extra: dict[str, object] = {"revision": message.revision, "done": message.progress.done}

        # Serialize revision checks and writes so older updates cannot overwrite newer ones.
        async with self._lock:
            if message.revision <= self._latest_revision:
                self._logger.info(
                    "Stale UpdatePRComment ignored (latest rendered is %s)", self._latest_revision, extra=log_extra
                )
                return

            # Retain the report before any write that could fail or be interrupted.
            self._latest_body = body
            self._latest_progress = message.progress
            self._latest_revision = message.revision

            pr_number = self._options.pr_number
            if pr_number is None:
                self._logger.info("No pull request to update: %s", summary_line(message.progress), extra=log_extra)
                published = True
            else:
                self._pr_comment_failed = True
                published = await self._write(pr_number, body, message.progress, log_extra)
                self._pr_comment_failed = not published

            if message.progress.done and published:
                self._final_report_published = True

    async def publish_shutdown(self, request: ShutdownRequest) -> None:
        """Publish a terminal report within one deadline, including lock acquisition.

        Timing out before acquiring the lock leaves the retained report unchanged.
        """
        async with asyncio.timeout(SHUTDOWN_WRITE_TIMEOUT), self._lock:
            progress = self._latest_progress
            body = render_shutdown_notice(request) if progress is None else render_comment(progress, shutdown=request)
            log_extra: dict[str, object] = {"revision": self._latest_revision, "shutdown": request.kind.value}
            self._latest_body = body
            # Reject all subsequent progress revisions, even if this write fails.
            self._latest_revision = sys.maxsize

            pr_number = self._options.pr_number
            if pr_number is None:
                self._logger.warning("Run %s; no pull request to report it on", request.kind.value, extra=log_extra)
                return

            self._pr_comment_failed = True
            published = await self._write(pr_number, body, progress, log_extra, shutdown=request)
            self._pr_comment_failed = not published
            if published:
                self._logger.info("Run reported as %s", request.kind.value, extra=log_extra)

    async def _write(
        self,
        pr_number: int,
        body: str,
        progress: DispatcherProgress | None,
        log_extra: dict[str, object],
        *,
        shutdown: ShutdownRequest | None = None,
    ) -> bool:
        """Return whether publication succeeded, using smaller bodies or a replacement comment.

        The GitHub client handles transient retries.
        """
        rendered = body
        # Render fallback tiers only when needed, skipping duplicate bodies.
        tiers = (render(progress, shutdown=shutdown) for render in FALLBACK_TIERS) if progress is not None else iter(())
        for _ in range(MAX_WRITE_PASSES):
            try:
                await self._submit(pr_number, rendered)
            except GitHubBodyTooLongError as error:
                smaller = next((candidate for candidate in tiers if candidate != rendered), None)
                if smaller is None:
                    self._logger.error("PR comment too long at every tier: %s", error, extra=log_extra)
                    return False
                rendered = smaller
                self._logger.warning(
                    "PR comment body too long (%s); retrying with a smaller one (%s bytes)",
                    error,
                    len(rendered),
                    extra=log_extra,
                )
            except httpx.HTTPError as error:
                if self._forget_unusable_comment(error, log_extra):
                    # The next pass creates a comment we own, rather than re-editing one we do not.
                    continue
                self._logger.error("PR comment write failed: %s", error, extra=log_extra)
                return False
            else:
                self._logger.info(
                    "PR comment written", extra={**log_extra, "comment_id": self._comment_id, "bytes": len(rendered)}
                )
                return True

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
                # A quoted marker must not identify someone else's reply as our report.
                if comment.body.startswith(COMMENT_MARKER) and comment.id not in self._unusable_comment_ids:
                    self._comment_id = comment.id
                    return comment.id
        return None

    def _forget_unusable_comment(self, error: httpx.HTTPError, log_extra: dict[str, object]) -> bool:
        """Discard an inaccessible comment and return whether to try a replacement."""
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
