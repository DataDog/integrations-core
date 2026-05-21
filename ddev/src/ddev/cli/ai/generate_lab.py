# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import anthropic
import click

from ddev.ai.flows.e2e_framework_lab import prepare_and_run_e2e_lab_flow

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('generate-lab', short_help='Generate an Agent E2E framework lab with AI')
@click.argument('integration')
@click.option('--agent-repo', type=click.Path(path_type=Path), help='Override the local datadog-agent checkout.')
@click.option(
    '--worktree-parent', type=click.Path(path_type=Path), help='Override where the Agent worktree is created.'
)
@click.option('--branch-name', help='Override the generated Agent worktree branch name.')
@click.pass_obj
def generate_lab(
    app: Application,
    integration: str,
    agent_repo: Path | None,
    worktree_parent: Path | None,
    branch_name: str | None,
) -> None:
    """Generate Agent E2E framework lab artifacts for INTEGRATION."""

    if not os.environ.get('ANTHROPIC_API_KEY'):
        app.abort('ANTHROPIC_API_KEY must be set before running `ddev ai generate-lab`.')

    try:
        intg = app.repo.integrations.get(integration)
    except OSError as e:
        app.abort(str(e))

    if agent_repo is None:
        try:
            agent_repo = Path(app.config.repos['agent']).expanduser()
        except KeyError:
            app.abort('No `agent` repository is configured. Pass --agent-repo PATH or configure [repos].agent.')

    agent_repo = agent_repo.expanduser()
    if worktree_parent is None:
        worktree_parent = agent_repo.parent / 'datadog-agent-worktrees'
    else:
        worktree_parent = worktree_parent.expanduser()

    app.display_waiting(f'Generating Agent E2E framework lab for `{integration}`...')
    try:
        result = prepare_and_run_e2e_lab_flow(
            integration=integration,
            integration_path=intg.path,
            agent_repo_path=agent_repo,
            agent_worktree_parent=worktree_parent,
            branch_name=branch_name,
            anthropic_client=anthropic.AsyncAnthropic(),
        )
    except Exception as e:
        app.abort(str(e))

    app.display_success('Agent E2E framework lab generation finished.')
    app.display_pair('Agent worktree', str(result.worktree.path))
    app.display_pair('Branch', result.worktree.branch_name)
    app.display_pair('Checkpoints', str(result.checkpoint_path))
    app.display_info(_render_next_steps(integration, result.worktree.path), highlight=False)


def _render_next_steps(integration: str, worktree_path: Path) -> str:
    return f"""
Next steps:

  cd {worktree_path}
  git status
  find test/e2e-framework/components/datadog/apps/{integration} -maxdepth 3 -type f
  find test/e2e-framework/scenarios/aws/{integration} -maxdepth 2 -type f
  dda inv aws.create-{integration} --help
  dda inv aws.destroy-{integration} --help
  dda inv aws.connect-{integration} --help
""".strip()
