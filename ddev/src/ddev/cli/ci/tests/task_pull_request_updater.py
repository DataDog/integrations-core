# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import asyncio
import logging

from ddev.cli.ci.tests._pr_comment import COMMENT_MARKER, format_pr_comment
from ddev.cli.ci.tests.messages import UpdatePRComment
from ddev.event_bus.orchestrator import AsyncProcessor
from ddev.utils.github_async import AsyncGitHubClient


class TaskPullRequestUpdater(AsyncProcessor[UpdatePRComment]):
    """
    Reads ``UpdatePRComment`` messages and creates or updates a single PR comment with the latest
    state of every finished workflow. The comment id is tracked in-memory; on first use the task scans
    existing PR comments for ``COMMENT_MARKER`` so dispatcher re-runs reuse the same comment.

    This task is a terminal consumer — it makes GitHub API calls but emits no further messages.
    """

    def __init__(self, name: str, client: AsyncGitHubClient, owner: str, repo: str, pr_number: int) -> None:
        super().__init__(name)
        self._client = client
        self._owner = owner
        self._repo = repo
        self._pr_number = pr_number
        self._comment_id: int | None = None
        self._lock = asyncio.Lock()
        self._logger = logging.getLogger(f"{__name__}.{name}")

    async def process_message(self, message: UpdatePRComment) -> None:
        body = format_pr_comment(message)
        log_extra = {"pr_number": self._pr_number, "done": message.done}

        async with self._lock:
            comment_id = await self._resolve_comment_id()
            if comment_id is not None:
                await self._client.update_issue_comment(self._owner, self._repo, comment_id, body)
                self._logger.info("PR comment updated", extra={**log_extra, "comment_id": comment_id})
            else:
                created = await self._client.create_issue_comment(self._owner, self._repo, self._pr_number, body)
                self._comment_id = created.data.id
                self._logger.info("PR comment created", extra={**log_extra, "comment_id": self._comment_id})

    async def _resolve_comment_id(self) -> int | None:
        """Return the comment id to edit: the tracked one, else an existing marked comment."""
        if self._comment_id is not None:
            return self._comment_id
        async for page in self._client.list_issue_comments(self._owner, self._repo, self._pr_number):
            for comment in page.data:
                if comment.body.startswith(COMMENT_MARKER):
                    self._comment_id = comment.id
                    return comment.id
        return None
