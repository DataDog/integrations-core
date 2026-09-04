# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Where a CI run gets the changes it must test.

A pull request reads its diff from the API because the merge base it would need locally is not in
the checkout: the target branch has no local ref, and under `workflow_run` the head commit is
absent too.
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
    """Return what *commit* itself contributed, comparing it with its first parent."""
    try:
        return git.changed_files(f"{commit}^1", commit)
    except OSError as error:
        raise ChangeResolutionError(
            f"Could not compare {commit} with its parent: {error}\n"
            "The checkout needs the parent commit, which `fetch-depth: 2` provides."
        ) from error
    except ValueError as error:
        raise ChangeResolutionError(f"Could not read the diff of {commit}: {error}") from error


async def changes_in_pull_request(
    client: AsyncGitHubClient, owner: str, repo: str, pull_number: int, expected_total: int
) -> list[ChangedFile]:
    """Return the files a pull request changes, read from the API.

    The endpoint stops at 3000 files without reporting that it did, so a total that disagrees with
    `expected_total` (`changed_files` on the pull request) aborts rather than planning a subset.
    A run with nothing to compare never reaches here, so the total is always a count to check.
    """
    files: list[PullRequestFile] = []
    async for page in client.list_pull_request_files(owner, repo, pull_number):
        files.extend(page.data)

    if len(files) != expected_total:
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
