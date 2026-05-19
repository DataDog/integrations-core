# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

from ddev.utils.fs import Path

if TYPE_CHECKING:
    from ddev.cli.application import Application


POC_AGENT_BRANCH = 'add-milvus-e2e-scenario'
SUPPORTED_LABS = {'milvus'}


@click.group(short_help='Manage remote integration labs')
def lab() -> None:
    """Manage remote integration labs."""


@lab.command(short_help='Create a remote integration lab')
@click.argument('integration')
@click.option('--stack-name', help='Pulumi stack name to pass to the Agent E2E scenario.')
@click.option('--use-fakeintake', is_flag=True, help='Deploy fakeintake and point the Agent at it.')
@click.option('--agent-version', help='Agent image tag to pass to the Agent E2E scenario.')
@click.option('--full-image-path', help='Full Agent image path to pass to the Agent E2E scenario.')
@click.option(
    '--agent-env',
    multiple=True,
    help='Extra Agent environment variable to pass through, for example DD_LOG_LEVEL=debug.',
)
@click.option(
    '--agent-repo',
    type=click.Path(file_okay=False, path_type=Path),
    help='Path to a datadog-agent checkout. Defaults to the configured `repos.agent` path.',
)
@click.option(
    '--agent-branch',
    default=POC_AGENT_BRANCH,
    show_default=True,
    help='datadog-agent branch that contains the lab scenario POC.',
)
@click.option('--skip-branch-check', is_flag=True, help='Do not verify the datadog-agent checkout branch.')
@click.pass_obj
def create(
    app: Application,
    *,
    integration: str,
    stack_name: str | None,
    use_fakeintake: bool,
    agent_version: str | None,
    full_image_path: str | None,
    agent_env: tuple[str, ...],
    agent_repo: Path | None,
    agent_branch: str,
    skip_branch_check: bool,
) -> None:
    """Create a remote integration lab by delegating to the Agent E2E framework."""
    command = _base_agent_e2e_command('create', integration)
    if stack_name:
        command.append(f'--stack-name={stack_name}')
    if use_fakeintake:
        command.append('--use-fakeintake')
    if agent_version:
        command.append(f'--agent-version={agent_version}')
    if full_image_path:
        command.append(f'--full-image-path={full_image_path}')
    for env_var in agent_env:
        command.append(f'--agent-env={env_var}')

    _run_agent_e2e_command(app, command, agent_repo, agent_branch, skip_branch_check)


@lab.command(short_help='Destroy a remote integration lab')
@click.argument('integration')
@click.option('--stack-name', help='Pulumi stack name to pass to the Agent E2E scenario.')
@click.option(
    '--agent-repo',
    type=click.Path(file_okay=False, path_type=Path),
    help='Path to a datadog-agent checkout. Defaults to the configured `repos.agent` path.',
)
@click.option(
    '--agent-branch',
    default=POC_AGENT_BRANCH,
    show_default=True,
    help='datadog-agent branch that contains the lab scenario POC.',
)
@click.option('--skip-branch-check', is_flag=True, help='Do not verify the datadog-agent checkout branch.')
@click.pass_obj
def destroy(
    app: Application,
    *,
    integration: str,
    stack_name: str | None,
    agent_repo: Path | None,
    agent_branch: str,
    skip_branch_check: bool,
) -> None:
    """Destroy a remote integration lab by delegating to the Agent E2E framework."""
    command = _base_agent_e2e_command('destroy', integration)
    if stack_name:
        command.append(f'--stack-name={stack_name}')

    _run_agent_e2e_command(app, command, agent_repo, agent_branch, skip_branch_check)


def _base_agent_e2e_command(action: str, integration: str) -> list[str]:
    normalized_integration = integration.lower().replace('_', '-')
    if normalized_integration not in SUPPORTED_LABS:
        supported = ', '.join(sorted(SUPPORTED_LABS))
        raise click.ClickException(f'Unsupported lab {integration!r}. This POC supports: {supported}')

    return ['dda', 'inv', f'aws.{action}-{normalized_integration}']


def _run_agent_e2e_command(
    app: Application,
    command: list[str],
    agent_repo: Path | None,
    agent_branch: str,
    skip_branch_check: bool,
) -> None:
    resolved_agent_repo = _resolve_agent_repo(app, agent_repo)
    if not skip_branch_check:
        _check_agent_branch(app, resolved_agent_repo, agent_branch)

    app.display_info(f'Running in {resolved_agent_repo}: {" ".join(command)}')
    process = app.platform.run_command(command, cwd=str(resolved_agent_repo))
    if process.returncode:
        app.abort(code=process.returncode)


def _resolve_agent_repo(app: Application, agent_repo: Path | None) -> Path:
    resolved_agent_repo = agent_repo or Path(app.config.repos['agent']).expand()
    if not resolved_agent_repo.is_dir():
        app.abort(
            f'datadog-agent checkout not found at `{resolved_agent_repo}`. '
            'Pass --agent-repo or configure [repos].agent.'
        )
    return resolved_agent_repo


def _check_agent_branch(app: Application, agent_repo: Path, expected_branch: str) -> None:
    process = app.platform.run_command(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=str(agent_repo),
        capture_output=True,
        text=True,
    )
    if process.returncode:
        app.abort(f'Unable to determine datadog-agent branch at `{agent_repo}`.')

    current_branch = process.stdout.strip()
    if current_branch != expected_branch:
        app.abort(
            f'This POC expects datadog-agent branch `{expected_branch}`, but `{agent_repo}` is on '
            f'`{current_branch}`. Run `git -C {agent_repo} fetch origin {expected_branch}` then '
            f'`git -C {agent_repo} checkout {expected_branch}`, or pass --skip-branch-check.'
        )
