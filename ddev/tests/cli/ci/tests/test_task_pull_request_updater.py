# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the TaskPullRequestUpdater processor."""

from __future__ import annotations

import asyncio

import pytest

from ddev.cli.ci.tests._pr_comment import COMMENT_MARKER
from ddev.cli.ci.tests.messages import FailedCheck, UpdatePRComment, WorkflowStatus
from ddev.cli.ci.tests.task_pull_request_updater import TaskPullRequestUpdater
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import IssueComment


class _FakeGitHubClient:
    """Records comment calls and returns canned IssueComment responses."""

    def __init__(
        self,
        existing: list[IssueComment] | None = None,
        pages: list[list[IssueComment]] | None = None,
    ) -> None:
        self.pages = pages if pages is not None else [existing or []]
        self.created: list[dict] = []
        self.updated: list[dict] = []
        self.list_calls = 0
        self.pages_fetched = 0
        self._next_id = 1000

    async def list_issue_comments(self, owner, repo, issue_number, per_page=100, timeout=None):
        self.list_calls += 1
        for page in self.pages:
            self.pages_fetched += 1
            yield GitHubResponse[list[IssueComment]].model_validate({"data": page, "headers": {}})

    async def create_issue_comment(self, owner, repo, issue_number, body, timeout=None):
        self._next_id += 1
        self.created.append({"issue_number": issue_number, "body": body, "id": self._next_id})
        return GitHubResponse[IssueComment].model_validate(
            {"data": IssueComment(id=self._next_id, body=body), "headers": {}}
        )

    async def update_issue_comment(self, owner, repo, comment_id, body, timeout=None):
        self.updated.append({"comment_id": comment_id, "body": body})
        return GitHubResponse[IssueComment].model_validate(
            {"data": IssueComment(id=comment_id, body=body), "headers": {}}
        )


def _comment(id: int, body: str) -> IssueComment:
    return IssueComment(id=id, body=body)


def _message(done: bool = False, failed: bool = False) -> UpdatePRComment:
    checks = [FailedCheck(name="ntp", url="u", environment="py3.13", error="boom")] if failed else []
    status = WorkflowStatus(url="u", id=1, success_count=1, failed_count=len(checks), failed_checks=checks)
    return UpdatePRComment(id="batch", done=done, workflows=[status])


def _make_updater(client: _FakeGitHubClient) -> TaskPullRequestUpdater:
    updater = TaskPullRequestUpdater("pr-updater", client, "DataDog", "integrations-core", 123)
    updater.queue = asyncio.Queue()
    return updater


@pytest.mark.asyncio
async def test_first_message_creates_comment() -> None:
    client = _FakeGitHubClient()
    updater = _make_updater(client)

    await updater.process_message(_message())

    assert len(client.created) == 1
    assert client.created[0]["issue_number"] == 123
    assert client.created[0]["body"].startswith(COMMENT_MARKER)
    assert not client.updated
    assert updater._comment_id == client.created[0]["id"]


@pytest.mark.asyncio
async def test_second_message_updates_same_comment() -> None:
    client = _FakeGitHubClient()
    updater = _make_updater(client)

    await updater.process_message(_message())
    await updater.process_message(_message(done=True))

    assert len(client.created) == 1
    assert len(client.updated) == 1
    assert client.updated[0]["comment_id"] == client.created[0]["id"]
    # The tracked id short-circuits the list lookup on the second message.
    assert client.list_calls == 1


@pytest.mark.asyncio
async def test_marker_fallback_adopts_existing_comment() -> None:
    client = _FakeGitHubClient(existing=[_comment(7, "unrelated"), _comment(42, f"{COMMENT_MARKER}\nold")])
    updater = _make_updater(client)

    await updater.process_message(_message())

    assert not client.created
    assert len(client.updated) == 1
    assert client.updated[0]["comment_id"] == 42


@pytest.mark.asyncio
async def test_marker_found_on_later_page() -> None:
    client = _FakeGitHubClient(
        pages=[
            [_comment(idx, "unrelated") for idx in range(1, 4)],
            [_comment(7, "noise"), _comment(42, f"{COMMENT_MARKER}\nold")],
        ]
    )
    updater = _make_updater(client)

    await updater.process_message(_message())

    # The marker lives on the second page; it must still be found instead of posting a duplicate.
    assert not client.created
    assert len(client.updated) == 1
    assert client.updated[0]["comment_id"] == 42
    assert client.pages_fetched == 2


@pytest.mark.asyncio
async def test_marker_search_stops_at_first_match() -> None:
    client = _FakeGitHubClient(
        pages=[
            [_comment(42, f"{COMMENT_MARKER}\nold")],
            [_comment(99, f"{COMMENT_MARKER}\nstale")],
        ]
    )
    updater = _make_updater(client)

    await updater.process_message(_message())

    # Found on page one — the second page is never fetched.
    assert client.updated[0]["comment_id"] == 42
    assert client.pages_fetched == 1


@pytest.mark.asyncio
async def test_done_body_differs_from_ongoing() -> None:
    client = _FakeGitHubClient()
    updater = _make_updater(client)

    await updater.process_message(_message(done=False))
    await updater.process_message(_message(done=True))

    assert "_running_" in client.created[0]["body"]
    assert "_complete_" in client.updated[0]["body"]
