# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application

BRANCH_NAME_PATTERN = r"^\d+\.\d+\.x$"
BRANCH_NAME_REGEX = re.compile(BRANCH_NAME_PATTERN)
GITHUB_LABEL_COLOR = '5319e7'


@click.command
@click.pass_obj
@click.argument('branch_name')
def create(app: Application, branch_name):
    r"""
    Create a branch for a release of the Agent.

    BRANCH_NAME should match this pattern:
    ^\d+\.\d+\.x$`, for example `7.52.x`.

    This command will also create the `backport/<BRANCH_NAME>` label in GitHub for this release branch.
    """

    if not BRANCH_NAME_REGEX.match(branch_name):
        app.abort(f'Invalid branch name: {branch_name}. Branch name must match the pattern {BRANCH_NAME_PATTERN}')

    app.display_waiting("Checking out the master branch...")
    app.repo.git.run('checkout', 'master')
    app.display_success("Done.")

    app.display_waiting("Updating the master branch...")
    app.repo.git.run('pull', 'origin', 'master')
    app.display_success("Done.")

    app.display_waiting(f"Creating the release branch `{branch_name}`...")
    app.repo.git.run('checkout', '-b', branch_name)
    app.display_success("Done.")

    app.display_waiting(f"Pushing the release branch `{branch_name}`...")
    app.repo.git.run('push', 'origin', branch_name)
    app.display_success("Done.")

    app.display_waiting(f"Creating the `backport/{branch_name}` label on GitHub...")
    app.github.create_label(f'backport/{branch_name}', GITHUB_LABEL_COLOR)
    app.display_success("Done.")

    app.display_success("All done.")
