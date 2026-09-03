# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Where a CI run gets the changes it must test.

The source depends on the trigger, because the objects each one leaves in the checkout differ. A
push compares against the commit's first parent, which is one object away on the branch already
checked out. A pull request needs the merge base of two diverged histories, and the checkout it runs
in has neither the target branch as a local ref nor, under `workflow_run`, the head commit at all,
so it reads the diff from the API instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.utils.git import ChangedFile, ChangeType

if TYPE_CHECKING:
    from ddev.utils.git import GitRepository
    from ddev.utils.github_async import AsyncGitHubClient
    from ddev.utils.github_async.models import PullRequestFile


class ChangeResolutionError(Exception):
    """Raised when the changes a run is responsible for cannot be established."""


# `unchanged` is reachable only on a paginated diff GitHub truncated, and a type change reads as a
# modification, so both fall back to MODIFIED rather than dropping the path.
CHANGE_TYPES = {
    "added": ChangeType.ADDED,
    "removed": ChangeType.DELETED,
    "modified": ChangeType.MODIFIED,
    "renamed": ChangeType.RENAMED,
    "copied": ChangeType.COPIED,
    "changed": ChangeType.MODIFIED,
    "unchanged": ChangeType.MODIFIED,
}


def changes_in_commit(git: GitRepository, commit: str) -> list[ChangedFile]:
    """Return what *commit* itself contributed, comparing it with its first parent.

    Only the parent is needed, so a checkout two commits deep is enough and no request is made.
    """
    try:
        return git.changed_files(f"{commit}^1", commit)
    except OSError as error:
        raise ChangeResolutionError(
            f"Could not compare {commit} with its parent: {error}\n"
            "The checkout needs the parent commit, which `fetch-depth: 2` provides."
        ) from error


async def changes_in_pull_request(
    client: AsyncGitHubClient, owner: str, repo: str, pull_number: int, expected_total: int | None
) -> list[ChangedFile]:
    """Return the files a pull request changes, read from the API.

    `expected_total` is `changed_files` on the pull request. The endpoint stops at 3000 files
    without saying so, and a short list plans a subset of the targets and still reports success, so
    a count that disagrees aborts the run instead.
    """
    files: list[PullRequestFile] = []
    async for page in client.list_pull_request_files(owner, repo, pull_number):
        files.extend(page.data)

    if expected_total is not None and len(files) != expected_total:
        raise ChangeResolutionError(
            f"Pull request {pull_number} reports {expected_total} changed files but the API listed "
            f"{len(files)}. Planning from an incomplete list would leave part of the change untested."
        )

    return [
        ChangedFile(
            change_type=CHANGE_TYPES.get(changed.status, ChangeType.MODIFIED),
            path=changed.filename,
            previous_path=changed.previous_filename,
        )
        for changed in files
    ]
