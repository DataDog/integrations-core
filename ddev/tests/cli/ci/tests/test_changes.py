# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Tests for the comparison a CI run diffs to find what it must test."""

from __future__ import annotations

import pytest

from ddev.cli.ci.tests.changes import CIContext, get_changed_files
from ddev.utils.git import ChangedFile, ChangeType


class RecordingGit:
    """Stand-in for `GitRepository` that records the comparison it was asked for."""

    def __init__(self, changed=()):
        self.changed = list(changed)
        self.calls: list[tuple[str, str | None]] = []

    def changed_files(self, base="origin/master", head=None):
        self.calls.append((base, head))
        return list(self.changed)


@pytest.mark.parametrize(
    ("context", "target_branch", "expected_call"),
    [
        pytest.param(CIContext.PULL_REQUEST, "origin/master", ("origin/master", "abc123"), id="pull-request"),
        pytest.param(CIContext.DEFAULT_BRANCH, None, ("abc123^1", "abc123"), id="default-branch"),
    ],
)
def test_get_changed_files_uses_the_right_comparison(context, target_branch, expected_call):
    changed_file = ChangedFile(ChangeType.MODIFIED, "foo/bar.py")
    git = RecordingGit([changed_file])

    changed = get_changed_files(git, "abc123", context=context, target_branch=target_branch)

    assert git.calls == [expected_call]
    assert changed == [changed_file]


def test_get_changed_files_pull_request_requires_target_branch():
    with pytest.raises(ValueError, match="target branch is required"):
        get_changed_files(RecordingGit(), "abc123", context=CIContext.PULL_REQUEST, target_branch=None)
