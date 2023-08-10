# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Create changelog entries')
@click.argument('entry_type', required=False)
@click.argument('targets', nargs=-1, required=False)
@click.option(
    '--message',
    '-m',
    help='The changelog text, defaulting to the PR title followed by the most recent commit message',
)
@click.pass_obj
def new(app: Application, entry_type: str | None, targets: tuple[str], message: str | None):
    """
    Create changelog entries.
    """
    from ddev.release.constants import ENTRY_TYPES

    derive_message = message is None
    latest_commit = app.repo.git.latest_commit
    pr = app.github.get_pull_request(latest_commit.sha)
    if pr is not None:
        pr_number = pr.number
        if message is None:
            message = pr.title
    else:
        pr_number = app.github.get_next_issue_number()
        if message is None:
            message = latest_commit.subject

    if entry_type is not None:
        entry_type = entry_type.capitalize()
        if entry_type not in ENTRY_TYPES:
            app.abort(f'Unknown entry type: {entry_type}')
    else:
        entry_type = click.prompt('Entry type?', type=click.Choice(ENTRY_TYPES, case_sensitive=False))

    expected_suffix = f' (#{pr_number})'
    entry = f'* {message.rstrip()}{expected_suffix}'
    if derive_message and (new_entry := click.edit(entry)) is not None:
        entry = new_entry
    entry = entry.strip()

    entry_priority = ENTRY_TYPES.index(entry_type)
    edited = 0

    for target in app.repo.integrations.iter_changed_code(targets):
        changelog = target.path / 'CHANGELOG.md'
        lines = changelog.read_text().splitlines()

        unreleased = False
        current_entry_type: str | None = None
        i = 0
        for i, line in enumerate(lines):
            if line == '## Unreleased':
                unreleased = True
                continue
            elif unreleased and line.startswith('## '):
                break
            elif line.startswith('***'):
                # e.g. ***Added***:
                current_entry_type = line[3:-4]

                try:
                    current_entry_priority = ENTRY_TYPES.index(current_entry_type)
                except ValueError:
                    app.abort(
                        f'{changelog.relative_to(app.repo.path)}, line {i}: unknown entry type {current_entry_type}'
                    )

                if current_entry_priority > entry_priority:
                    break

        if current_entry_type is None or current_entry_type != entry_type:
            for line in reversed(
                (
                    f'***{entry_type}***:',
                    '',
                    entry,
                    '',
                )
            ):
                lines.insert(i, line)
        else:
            lines.insert(i - 1, entry)

        lines.append('')
        changelog.write_text('\n'.join(lines))
        edited += 1

    app.display_success(f'Added {edited} changelog entr{"ies" if edited > 1 else "y"}')
