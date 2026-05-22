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


@click.command('generate-lab', short_help='Generate an integrations-core E2E framework lab with AI')
@click.argument('integration')
@click.pass_obj
def generate_lab(
    app: Application,
    integration: str,
) -> None:
    """Generate integrations-core E2E framework lab artifacts for INTEGRATION."""

    if not os.environ.get('ANTHROPIC_API_KEY'):
        app.abort('ANTHROPIC_API_KEY must be set before running `ddev ai generate-lab`.')

    try:
        intg = app.repo.integrations.get(integration)
    except OSError as e:
        app.abort(str(e))

    app.display_waiting(f'Generating integrations-core E2E framework lab for `{integration}`...')
    try:
        result = prepare_and_run_e2e_lab_flow(
            integration=integration,
            integration_path=intg.path,
            anthropic_client=anthropic.AsyncAnthropic(),
        )
    except Exception as e:
        app.abort(str(e))

    app.display_success('E2E framework lab generation finished.')
    app.display_pair('Lab path', str(result.lab_path))
    app.display_pair('Checkpoints', str(result.checkpoint_path))
    app.display_info(_render_next_steps(integration, result.lab_path), highlight=False)


def _render_next_steps(integration: str, lab_path: Path) -> str:
    return f"""
Next steps:

  find {lab_path} -maxdepth 3 -type f
  cat {lab_path / 'lab.yaml'}
  cat {lab_path / 'README.md'}

Future runtime bridge commands will use these lab artifacts to deploy `{integration}` through the Agent E2E framework.
""".strip()
