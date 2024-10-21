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
@click.option('--message', '-m', help='The changelog text')
@click.pass_obj
def new(app: Application, entry_type: str | None, targets: tuple[str], message: str | None):
    """
    This creates new changelog entries in Markdown format.

    If the ENTRY_TYPE is not specified, you will be prompted.

    The `--message` option can be used to specify the changelog text. If this is not supplied, an editor
    will be opened for you to manually write the entry. The changelog text that is opened defaults to
    the PR title, followed by the most recent commit subject. If that is sufficient, then you may close
    the editor tab immediately.

    By default, changelog entries will be created for all integrations that have changed code. To create
    entries only for specific targets, you may pass them as additional arguments after the entry type.
    """
    from datadog_checks.dev.tooling.commands.release.changelog import towncrier

    create_command = None

    edited = 0
    for check in app.repo.integrations.iter_changed_code(targets):
        if not create_command:
            create_command = __get_create_command(app, entry_type, message)

        towncrier(check.path, *create_command)
        edited += 1

    if not edited:
        app.display_info('No changelog entries to create')
    else:
        app.display_success(f'Added {edited} changelog entr{"ies" if edited > 1 else "y"}')


def __get_create_command(app, entry_type, message):
    from ddev.release.constants import ENTRY_TYPES

    latest_commit = app.repo.git.latest_commit()
    pr = app.github.get_pull_request(latest_commit.sha)
    if pr is not None:
        pr_number = pr.number
        message_based_on_git = pr.title
    else:
        pr_number = app.github.get_next_issue_number()
        message_based_on_git = latest_commit.subject

    if entry_type is None:
        entry_type = click.prompt('Entry type?', type=click.Choice(ENTRY_TYPES, case_sensitive=False))
    elif entry_type not in ENTRY_TYPES:
        app.abort(f'Unknown entry type: {entry_type}')

    return [
        'create',
        '--content',
        message or click.edit(text=message_based_on_git, require_save=False) or message_based_on_git,
        f'{pr_number}.{entry_type}',
    ]
