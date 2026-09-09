# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for where a CI run gets the changes it must test."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_commit, changes_in_pull_request
from ddev.utils.git import ChangedFile, ChangeType
from ddev.utils.github_async import GitHubResponse
from ddev.utils.github_async.models import PullRequestFile


class RecordingGit:
    """Stand-in for `GitRepository` that records the comparison it was asked for."""

    def __init__(self, changed: tuple[ChangedFile, ...] = (), error: Exception | None = None):
        self.changed = list(changed)
        self.error = error
        self.calls: list[tuple[str, str | None]] = []

    def changed_files(self, base: str = "origin/master", head: str | None = None) -> list[ChangedFile]:
        self.calls.append((base, head))
        if self.error is not None:
            raise self.error
        return list(self.changed)


def file_page(*files: PullRequestFile) -> GitHubResponse[list[PullRequestFile]]:
    return GitHubResponse[list[PullRequestFile]].model_validate({"data": list(files), "headers": {}})


class FakeFilesClient:
    """Stand-in for the client, yielding the pages it was built with."""

    def __init__(self, *pages: GitHubResponse[list[PullRequestFile]]):
        self.pages = pages
        self.calls: list[tuple[str, str, int]] = []

    async def list_pull_request_files(self, owner: str, repo: str, pull_number: int):
        self.calls.append((owner, repo, pull_number))
        for page in self.pages:
            yield page


def test_a_commit_is_compared_with_its_first_parent():
    changed_file = ChangedFile(ChangeType.MODIFIED, "foo/bar.py")
    git = RecordingGit((changed_file,))

    assert changes_in_commit(git, "abc123") == [changed_file]
    assert git.calls == [("abc123^1", "abc123")]


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        pytest.param(OSError("fatal: ambiguous argument 'abc123^1'"), "fetch-depth: 2", id="parent-missing"),
        pytest.param(ValueError("Malformed diff line: 'M'"), "Could not read the diff", id="unparsable-diff"),
    ],
)
def test_a_comparison_git_cannot_answer_is_reported_as_a_change_resolution_failure(error: Exception, expected: str):
    """Both reach the CLI as a message: the depth-1 checkout that causes the first is the common
    case and the message has to point at it, and neither should surface as a traceback.
    """
    git = RecordingGit(error=error)

    with pytest.raises(ChangeResolutionError, match=expected):
        changes_in_commit(git, "abc123")


async def test_a_pull_request_reads_every_page_of_its_diff():
    """Stopping early would plan a subset of the targets and still report success."""
    client = FakeFilesClient(
        file_page(PullRequestFile(filename="first.py", status="modified")),
        file_page(PullRequestFile(filename="second.py", status="added")),
    )

    changed = await changes_in_pull_request(client, "DataDog", "integrations-core", 25082, 2)

    assert [file.path for file in changed] == ["first.py", "second.py"]
    assert [file.change_type for file in changed] == [ChangeType.MODIFIED, ChangeType.ADDED]
    assert client.calls == [("DataDog", "integrations-core", 25082)]


async def test_a_truncated_diff_aborts_rather_than_planning_a_subset():
    """The endpoint truncates without saying so, so the count is the only thing that can catch it."""
    client = FakeFilesClient(file_page(PullRequestFile(filename="only.py", status="modified")))

    with pytest.raises(ChangeResolutionError, match="reports 2 changed files but the API listed 1"):
        await changes_in_pull_request(client, "DataDog", "integrations-core", 25082, 2)


async def test_a_rename_selects_the_target_it_moved_away_from():
    """`affected_paths` returns the source only for a RENAMED change, so mapping a rename to
    anything else stops selecting the target that used to own the file.
    """
    client = FakeFilesClient(
        file_page(
            PullRequestFile(filename="disk/new.py", status="renamed", previous_filename="postgres/old.py"),
        )
    )

    changed = await changes_in_pull_request(client, "DataDog", "integrations-core", 1, 1)

    assert changed[0].affected_paths == ("disk/new.py", "postgres/old.py")
