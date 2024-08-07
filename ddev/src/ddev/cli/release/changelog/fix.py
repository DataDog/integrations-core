# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command
@click.pass_obj
def fix(app: Application):
    """
    Fix changelog entries.

    This command is only needed if you are manually writing to the changelog.
    For instance for marketplace and extras integrations.
    Don't use this in integrations-core because the changelogs there are generated automatically.

    The first line of every new changelog entry must include the PR number in which the change
    occurred. This command will apply this suffix to manually added entries if it is missing.
    """
    from ddev.utils.scripts.check_pr import changelog_entry_suffix, get_noncore_repo_changelog_errors

    latest_commit = app.repo.git.latest_commit()
    pr = app.github.get_pull_request(latest_commit.sha)
    if pr is not None:
        if 'changelog/no-changelog' in pr.labels:
            app.display_warning('No changelog entries required (changelog/no-changelog label found)')
            return

        git_diff = app.github.get_diff(pr)
        pr_number = pr.number
        pr_url = pr.html_url
    else:
        git_diff = app.repo.git.capture('diff', 'origin/master...')
        pr_number = app.github.get_next_issue_number()
        pr_url = f'https://github.com/{app.github.repo_id}/pull/{pr_number}'

    expected_suffix = changelog_entry_suffix(pr_number, pr_url)
    fixed = 0
    for path, line_number, _ in get_noncore_repo_changelog_errors(git_diff, expected_suffix):
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
