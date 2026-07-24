# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Comparison-base selection and changed-file acquisition for Dispatcher planning.

Git execution is injected through a :class:`GitProvider` so production can issue real
commands while tests provide representative ``git diff --name-status`` output.
"""

from __future__ import annotations

import enum
import subprocess
from dataclasses import dataclass
from typing import Protocol


class CIContext(enum.Enum):
    """The comparison context that determines which revisions are diffed."""

    PULL_REQUEST = enum.auto()
    DEFAULT_BRANCH = enum.auto()


class ChangeType(enum.Enum):
    """The kind of change reported by ``git diff --name-status``.

    Values are the literal git status letters so a status code maps directly onto a member;
    they carry meaning and therefore are not ``enum.auto()``.
    """

    ADDED = "A"
    MODIFIED = "M"
    DELETED = "D"
    RENAMED = "R"
    COPIED = "C"


# Single-path statuses map directly; a type change (``T``) is a modification of an existing
# path, and any other single-path status is treated as a modification so no changed path is lost.
SINGLE_PATH_CHANGE_TYPES = {
    "A": ChangeType.ADDED,
    "M": ChangeType.MODIFIED,
    "D": ChangeType.DELETED,
    "T": ChangeType.MODIFIED,
}


@dataclass(frozen=True)
class ChangedFile:
    """A single normalized change record.

    For renames and copies, ``path`` is the destination and ``previous_path`` is the source.
    """

    change_type: ChangeType
    path: str
    previous_path: str | None = None


class GitProvider(Protocol):
    """A callable boundary that runs ``git`` with the given arguments and returns stdout."""

    def __call__(self, *args: str) -> str: ...


class SubprocessGitProvider:
    """Production :class:`GitProvider` that shells out to the real ``git`` executable."""

    def __call__(self, *args: str) -> str:
        try:
            process = subprocess.run(
                ["git", *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise OSError(f"{str(e)[:-1]}:\n{e.output}") from None

        return process.stdout


def is_git_warning_line(line: str) -> bool:
    """Return whether a diff line is an ignorable Git warning rather than a change record."""
    return line.startswith("warning: ") or "original line endings" in line


def parse_name_status(output: str) -> list[ChangedFile]:
    """Normalize ``git diff --name-status`` output into deterministic change records.

    Each record line is tab separated: ``<status>\\t<path>`` for additions/modifications/
    deletions/type-changes and ``<status>\\t<source>\\t<destination>`` for renames and copies
    (whose status carries a similarity score, e.g. ``R100``). A non-warning line that does not
    have the field count its status requires is malformed and raises rather than being dropped,
    so an unparseable diff never silently hides a changed path.
    """
    changed: list[ChangedFile] = []
    seen: set[str] = set()
    for line in output.splitlines():
        if not line or is_git_warning_line(line):
            continue

        fields = line.split("\t")
        status = fields[0][:1].upper()
        if status in ("R", "C"):
            if len(fields) < 3:
                raise ValueError(f"Malformed rename/copy diff line: {line!r}")
            change_type = ChangeType.RENAMED if status == "R" else ChangeType.COPIED
            record = ChangedFile(change_type=change_type, path=fields[2], previous_path=fields[1])
        else:
            if len(fields) < 2:
                raise ValueError(f"Malformed diff line: {line!r}")
            change_type = SINGLE_PATH_CHANGE_TYPES.get(status, ChangeType.MODIFIED)
            record = ChangedFile(change_type=change_type, path=fields[1])

        if record.path in seen:
            continue
        seen.add(record.path)
        changed.append(record)

    return changed


def get_changed_files(
    tested_commit: str,
    *,
    context: CIContext,
    target_branch: str | None,
    git: GitProvider,
) -> list[ChangedFile]:
    """Acquire the changed files for the tested commit through the injected Git boundary.

    In a pull request the tested commit is compared with the merge base of the target
    branch; on the default branch it is compared with the tested commit's first parent.
    """
    if context is CIContext.PULL_REQUEST:
        if not target_branch:
            raise ValueError("A target branch is required to compare a pull request against its merge base")
        output = git("diff", "--name-status", f"{target_branch}...{tested_commit}")
    else:
        output = git("diff", "--name-status", f"{tested_commit}^1", tested_commit)

    return parse_name_status(output)
