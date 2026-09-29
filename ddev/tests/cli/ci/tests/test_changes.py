# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for where a CI run gets the changes it must test."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.changes import ChangeResolutionError, changes_in_commit
from ddev.utils.git import ChangedFile, ChangeType


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
