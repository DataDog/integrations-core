# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Input validation and git-ref checks for `ddev release test-agent`."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ddev.cli.release.test_agent.dispatch import WORKFLOW_LINUX, WORKFLOW_WINDOWS

if TYPE_CHECKING:
    from ddev.cli.application import Application

BRANCH_PATTERN = r'^\d+\.\d+\.x$'
TAG_PATTERN = r'^\d+\.\d+\.\d+(-rc\.\d+)?$'

WORKFLOW_FILES = [
    f'.github/workflows/{WORKFLOW_LINUX}',
    f'.github/workflows/{WORKFLOW_WINDOWS}',
]

# git error fragments that mean "ref exists but file is not in that tree" — i.e. the workflow
# really isn't on this branch/tag, as opposed to the ref itself being unreachable locally.
GIT_FILE_MISSING_FRAGMENTS = (
    'exists on disk',
    'does not exist',
    'no such path',
)
GIT_REF_MISSING_FRAGMENTS = (
    'invalid object name',
    'unknown revision',
    'bad revision',
    'ambiguous argument',
)


def validate_input(app: Application, branch: str | None, tag: str | None) -> tuple[str | None, str | None]:
    """Normalize and validate inputs, returning (branch, tag) with exactly one set."""
    if bool(branch) == bool(tag):
        app.abort('Exactly one of --branch or --tag must be provided.')

    if branch is not None and not re.match(BRANCH_PATTERN, branch):
        app.abort(f'Invalid branch: {branch!r}. Must match {BRANCH_PATTERN}.')

    if tag is not None:
        normalized = tag.removeprefix('v')
        if not re.match(TAG_PATTERN, normalized):
            app.abort(f'Invalid tag: {tag!r}. Must match {TAG_PATTERN}.')
        tag = normalized

    return branch, tag


def verify_ref_exists(app: Application, *, branch: str | None, tag: str | None) -> None:
    """Confirm the ref is published on origin via `git ls-remote`."""
    if branch is not None:
        kind, value, flag = 'branch', branch, '--heads'
    else:
        assert tag is not None
        kind, value, flag = 'tag', tag, '--tags'

    output = app.repo.git.capture('ls-remote', flag, 'origin', value)
    if not output.strip():
        app.abort(f'{kind.capitalize()} `{value}` not found on origin.')


def verify_workflows_present_on_ref(app: Application, *, branch: str | None, tag: str | None) -> None:
    """Confirm both workflow files exist at the target ref.

    `git show <ref>:<path>` only resolves against local refs, so a branch the user has not yet
    fetched will not be found under its bare name. For branches we read `origin/<branch>` to
    consult the remote-tracking ref; for tags we use the tag name directly. Either way, the
    git error text is inspected to distinguish "file missing from the tree" from "ref not
    local" so the abort message points at the real problem.
    """
    if branch is not None:
        local_ref = f'origin/{branch}'
        fetch_hint = f'Run `git fetch origin {branch}` and try again.'
    else:
        assert tag is not None
        local_ref = tag
        fetch_hint = f'Run `git fetch origin tag {tag}` and try again.'

    missing: list[str] = []
    for path in WORKFLOW_FILES:
        try:
            app.repo.git.show_file(path, local_ref)
        except OSError as e:
            msg = str(e).lower()
            if any(fragment in msg for fragment in GIT_FILE_MISSING_FRAGMENTS):
                missing.append(path)
            elif any(fragment in msg for fragment in GIT_REF_MISSING_FRAGMENTS):
                app.abort(f'Ref `{local_ref}` is not in your local clone. {fetch_hint} (git error: {e})')
            else:
                app.abort(f'Failed to read `{path}` from `{local_ref}`: {e}')

    if missing:
        app.abort(
            f'Ref `{local_ref}` is missing required workflow file(s): {", ".join(missing)}. '
            'Pick a newer ref that includes both `test-agent.yml` and `test-agent-windows.yml`.'
        )
