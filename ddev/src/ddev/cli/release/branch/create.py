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
    app.repo.git.run('checkout', '-B', branch_name)
    app.display_success("Done.")

    app.display_waiting("Updating the .gitlab/build_agent.yaml file...")
    update_build_agent_yaml(app, branch_name)
    app.display_success("Done.")

    app.display_waiting("Adding and committing the changes...")
    app.repo.git.run('add', '.gitlab/build_agent.yaml')
    app.repo.git.run('commit', '-m', f"Update build_agent.yaml to use agent branch: {branch_name}")
    app.display_success("Done.")

    app.display_waiting(f"Pushing the release branch `{branch_name}`...")
    app.repo.git.run('push', 'origin', branch_name)
    app.display_success("Done.")

    app.display_waiting(f"Creating the `backport/{branch_name}` label on GitHub...")
    app.github.create_label(f'backport/{branch_name}', GITHUB_LABEL_COLOR)
    app.display_success("Done.")

    app.display_success("All done.")


def update_build_agent_yaml(app: Application, branch_name: str) -> None:
    """
    Update the .gitlab/build_agent.yaml file to use the correct agent branch for release builds.

    Args:
        branch_name: The release branch name (e.g., '7.45.x')
    """
    from ddev.utils.fs import Path

    build_agent_yaml = Path('.gitlab/build_agent.yaml')

    if not build_agent_yaml.exists():
        app.display_warning(f'Warning: {build_agent_yaml} not found')
        return

    # Read the current content
    with open(build_agent_yaml, 'r') as f:
        content = f.read()

    # Update the build-agent-manual-release job to use the correct agent branch
    # Find the line with 'branch: main' and replace it
    old_pattern = r'(\s+branch:\s+)main'

    def replacement(match):
        return match.group(1) + branch_name

    if re.search(old_pattern, content):
        updated_content = re.sub(old_pattern, replacement, content)

        # Write the updated content back
        with open(build_agent_yaml, 'w') as f:
            f.write(updated_content)

        app.display_success(f'Updated build_agent.yaml file to use Agent branch: {branch_name}')
    else:
        app.display_warning(f'Warning: Could not find branch pattern to update in {build_agent_yaml}')
