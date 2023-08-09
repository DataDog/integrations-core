# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Fix changelog entries')
@click.pass_obj
def fix(app: Application):
    """
    Fix changelog entries.
    """
    from ddev.utils.scripts.check_pr import get_changelog_errors

    latest_commit = app.repo.git.latest_commit
    pr = app.github.get_pull_request(latest_commit.sha)
    if pr is not None:
        git_diff = app.github.get_diff(pr)
        pr_number = pr.number
    else:
        git_diff = app.repo.git.capture('diff', 'origin/master...')
        pr_number = app.github.get_next_issue_number()

    expected_suffix = f' (#{pr_number})'
    fixed = 0
    for path, line_number, _ in get_changelog_errors(git_diff, expected_suffix):
        if line_number == 1:
            continue

        changelog = app.repo.path / path
        lines = changelog.read_text().splitlines(keepends=True)
        index = line_number - 1
        original_line = lines[index]
        new_line = original_line.rstrip()
        if new_line.endswith(expected_suffix):
            continue

        lines[index] = f'{new_line}{expected_suffix}{original_line[len(new_line) :]}'
        changelog.write_text(''.join(lines))
        fixed += 1

    if not fixed:
        app.display_info('No changelog entries need fixing')
    else:
        app.display_success(f'Fixed {fixed} changelog entr{"ies" if fixed > 1 else "y"}')
