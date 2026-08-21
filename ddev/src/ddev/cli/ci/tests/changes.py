# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Selection of the commits a CI run compares to find what it must test."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.utils.git import ChangedFile, GitRepository


class CIContext(enum.Enum):
    """The comparison context that determines which revisions are diffed."""

    PULL_REQUEST = enum.auto()
    DEFAULT_BRANCH = enum.auto()


def get_changed_files(
    git: GitRepository,
    tested_commit: str,
    *,
    context: CIContext,
    target_branch: str | None = None,
) -> list[ChangedFile]:
    """Return the changes the tested commit is responsible for.

    A pull request is compared with the merge base of its target branch, so unrelated commits
    landing on that branch meanwhile do not count as changes. On the default branch the comparison
    is against the tested commit's first parent, which is the commit's own contribution.
    """
    if context is CIContext.PULL_REQUEST:
        if not target_branch:
            raise ValueError("A target branch is required to compare a pull request against its merge base")
        base = target_branch
    else:
        base = f"{tested_commit}^1"

    return git.changed_files(base, tested_commit)
