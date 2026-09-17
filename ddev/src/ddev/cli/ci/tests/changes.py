# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Where a CI run gets the changes it must test: a first-parent comparison against the checkout,
which is a pull request's merge commit or the tested commit itself."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ddev.utils.git import ChangedFile

if TYPE_CHECKING:
    from ddev.utils.git import GitRepository


class ChangeResolutionError(Exception):
    """Raised when the changes a run is responsible for cannot be established."""


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
