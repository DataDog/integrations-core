# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Input validation, ref fetching, and workflow-file checks for `ddev release test-agent`.

The user picks either a release branch or a release tag. Downstream code needs to treat
those two paths differently (the fetch refspec, the local ref name for `git show`, the
version-resolution logic), but the type system has to know which one is in hand. Modelling
the choice as a sum type (`Branch | Tag`) — produced by `validate_input` after the
user-facing checks — keeps the branch/tag distinction explicit at every call site and
eliminates the type-narrowing `assert`s that would otherwise be needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application

BRANCH_PATTERN = r'^\d+\.\d+\.x$'
TAG_PATTERN = r'^\d+\.\d+\.\d+(-rc\.\d+)?$'

# The two workflow filenames the command targets. Defined here (the layer that runs first)
# rather than in `dispatch.py`, so the import graph flows validation -> dispatch and validation
# does not pull in dispatch's async/HTTP machinery at module-load time.
WORKFLOW_LINUX = 'test-agent.yml'
WORKFLOW_WINDOWS = 'test-agent-windows.yml'

WORKFLOW_FILES = [
    f'.github/workflows/{WORKFLOW_LINUX}',
    f'.github/workflows/{WORKFLOW_WINDOWS}',
]

# git error fragments that mean "ref exists but file is not in that tree" — i.e. the workflow
# really isn't on this branch/tag, as opposed to git failing for some other reason.
GIT_FILE_MISSING_FRAGMENTS = (
    'exists on disk',
    'does not exist',
    'no such path',
)

# git error fragments emitted when `git fetch` cannot resolve the named ref on origin.
GIT_FETCH_MISSING_FRAGMENTS = (
    "couldn't find remote ref",
    'no such ref',
)


@dataclass(frozen=True)
class Branch:
    """A validated release branch the user selected via `--branch`."""

    name: str


@dataclass(frozen=True)
class Tag:
    """A validated release tag the user selected via `--tag` (with any leading `v` stripped)."""

    name: str


ReleaseTarget = Branch | Tag


def validate_input(app: Application, branch: str | None, tag: str | None) -> ReleaseTarget:
    """Normalize and validate `--branch`/`--tag`, returning a typed `Branch` or `Tag`.

    Click can't enforce the mutually-exclusive constraint by itself, so this is the single
    point that does. Every downstream helper takes the resulting `ReleaseTarget` instead of
    two optional strings, which keeps the "exactly one is set" invariant in the type system
    rather than restated as `assert` at every call site.
    """
    if branch is not None and tag is not None:
        app.abort('Cannot use --branch and --tag together; pick one.')

    if branch is not None:
        if not re.match(BRANCH_PATTERN, branch):
            app.abort(f'Invalid branch: {branch!r}. Must match {BRANCH_PATTERN}.')
        return Branch(branch)

    if tag is not None:
        normalized = tag.removeprefix('v')
        if not re.match(TAG_PATTERN, normalized):
            app.abort(f'Invalid tag: {tag!r}. Must match {TAG_PATTERN}.')
        return Tag(normalized)

    app.abort('Exactly one of --branch or --tag must be provided.')


def local_ref_for(target: ReleaseTarget) -> str:
    """The local refname that `fetch_target` populates and that `git show` can read from."""
    if isinstance(target, Branch):
        return f'origin/{target.name}'
    return target.name


def fetch_target(app: Application, target: ReleaseTarget) -> None:
    """Fetch the user's release target from origin so `local_ref_for(target)` resolves locally.

    Combines the existence check (would otherwise be a `git ls-remote` probe) with the side
    effect of populating the local refs we need to read the workflow files. After this call,
    `git show origin/<branch>:<path>` or `git show <tag>:<path>` is guaranteed to find the
    target in the local clone.
    """
    if isinstance(target, Branch):
        kind = 'branch'
        refspec = f'+refs/heads/{target.name}:refs/remotes/origin/{target.name}'
    else:
        kind = 'tag'
        refspec = f'refs/tags/{target.name}:refs/tags/{target.name}'

    app.display_waiting(f'Fetching {kind} `{target.name}` from origin...')
    try:
        app.repo.git.run('fetch', '--quiet', '--depth=1', 'origin', refspec)
    except OSError as e:
        msg = str(e).lower()
        if any(fragment in msg for fragment in GIT_FETCH_MISSING_FRAGMENTS):
            app.abort(f'{kind.capitalize()} `{target.name}` not found on origin.')
        else:
            app.abort(f'Failed to fetch {kind} `{target.name}` from origin: {e}')


def verify_workflows_present_on_ref(app: Application, target: ReleaseTarget) -> None:
    """Confirm both workflow files exist at the target ref (which `fetch_target` made local)."""
    ref = local_ref_for(target)
    kind = 'branch' if isinstance(target, Branch) else 'tag'

    missing: list[str] = []
    for path in WORKFLOW_FILES:
        try:
            app.repo.git.show_file(path, ref)
        except OSError as e:
            msg = str(e).lower()
            if any(fragment in msg for fragment in GIT_FILE_MISSING_FRAGMENTS):
                missing.append(path)
            else:
                app.abort(f'Failed to read `{path}` from `{ref}`: {e}')

    if missing:
        app.abort(
            f'{kind.capitalize()} `{target.name}` is missing required workflow file(s): {", ".join(missing)}. '
            'Pick a newer ref that includes both `test-agent.yml` and `test-agent-windows.yml`.'
        )
