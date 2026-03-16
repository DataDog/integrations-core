# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click
from packaging.version import Version

if TYPE_CHECKING:
    from ddev.cli.application import Application

BRANCH_NAME_PATTERN = r"^\d+\.\d+\.x$"
BRANCH_NAME_REGEX = re.compile(BRANCH_NAME_PATTERN)
GITHUB_LABEL_COLOR = '5319e7'
DATADOG_AGENT_REPO_URL = 'https://github.com/DataDog/datadog-agent.git'


@click.command
@click.pass_obj
@click.argument('branch_name', required=False)
def create(app: Application, branch_name: str | None):
    r"""
    Create a branch for a release of the Agent.

    BRANCH_NAME should match this pattern:
    ^\d+\.\d+\.x$`, for example `7.52.x`.

    If BRANCH_NAME is not provided, the command will suggest the next version based on existing branches.

    This command will also create the `backport/<BRANCH_NAME>` label in GitHub for this release branch.
    """

    if branch_name is None:
        branch_name = click.prompt(
            'What branch name should we create? (hit ENTER to accept suggestion)',
            type=str,
            default=suggest_next_branch(app),
        )
    assert branch_name is not None

    if not BRANCH_NAME_REGEX.match(branch_name):
        app.abort(f'Invalid branch name: {branch_name}. Branch name must match the pattern {BRANCH_NAME_PATTERN}')

    if not click.confirm(f'Create and push release branch: {branch_name}?'):
        app.abort('Did not get confirmation, aborting. Did not create or push the branch.')

    app.display_waiting("Checking out the master branch...")
    app.repo.git.run('checkout', 'master')
    app.display_success("Done.")

    app.display_waiting("Updating the master branch...")
    app.repo.git.run('pull', 'origin', 'master')
    app.display_success("Done.")

    app.display_waiting(f"Creating the release branch `{branch_name}`...")
    app.repo.git.run('checkout', '-B', branch_name)
    app.display_success("Done.")

    app.display_waiting("Checking and updating the .gitlab/build_agent.yaml file...")
    yaml_updated = ensure_build_agent_yaml_updated(app, branch_name)
    app.display_success("Done.")

    if yaml_updated:
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


def suggest_next_branch(app: Application) -> str:
    app.display_waiting("Fetching remote branches...")
    app.repo.git.run('fetch', 'origin')

    output = app.repo.git.capture('branch', '-r', '--sort=-version:refname', '--list', 'origin/7.*.x')
    branches = [line.strip().replace('origin/', '') for line in output.splitlines() if line.strip()]
    valid_branches = [b for b in branches if BRANCH_NAME_REGEX.match(b)]

    if not valid_branches:
        return '7.0.x'

    major = Version(valid_branches[0].replace('.x', '.0')).major
    minors = sorted(Version(b.replace('.x', '.0')).minor for b in valid_branches)

    for i in range(len(minors) - 1):
        if minors[i + 1] - minors[i] > 1:
            missing = minors[i] + 1
            suggestion = f'{major}.{missing}.x'
            app.display_warning(
                f'Gap detected: {major}.{minors[i]}.x is followed by {major}.{minors[i + 1]}.x. '
                f'Suggesting {suggestion} to fill the gap.'
            )
            return suggestion

    return f'{major}.{minors[-1] + 1}.x'


def ensure_build_agent_yaml_updated(app: Application, branch_name: str) -> bool:
    """
    Ensure build_agent.yaml points to the correct agent branch for release builds.

    This function:
    1. Checks if the file still points to 'main' (needs update)
    2. Checks if the agent branch exists in datadog-agent repository
    3. Updates the file if both conditions are met

    Args:
        branch_name: The release branch name (e.g., '7.45.x')

    Returns:
        True if the file was updated, False otherwise.
    """
    from ddev.utils.fs import Path

    build_agent_yaml = Path('.gitlab/build_agent.yaml')

    if not build_agent_yaml.exists():
        app.display_warning(f'Warning: {build_agent_yaml} not found')
        return False

    # Read the current content
    with open(build_agent_yaml, 'r') as f:
        content = f.read()

    # Check if file still points to main (needs update)
    old_pattern = r'(\s+branch:\s+)main'
    if not re.search(old_pattern, content):
        # Already updated to a release branch, nothing to do
        return False

    # Check if the agent branch exists in datadog-agent repository using git ls-remote
    app.display_waiting(f'Checking if branch `{branch_name}` exists in datadog-agent...')
    ls_remote_output = app.repo.git.capture('ls-remote', '--heads', DATADOG_AGENT_REPO_URL, branch_name)
    if not ls_remote_output.strip():
        app.display_warning(
            f"Agent branch `{branch_name}` does not exist yet in datadog-agent. "
            f"Keeping build_agent.yaml pointing to 'main'. "
            f"The `update-build-agent-yaml` workflow will create a PR to update the file "
            f"once the agent branch is created."
        )
        return False

    # Agent branch exists, update the file
    def replacement(match):
        return match.group(1) + branch_name

    updated_content = re.sub(old_pattern, replacement, content)

    with open(build_agent_yaml, 'w') as f:
        f.write(updated_content)

    app.display_success(f'Updated build_agent.yaml file to use Agent branch: {branch_name}')
    return True
