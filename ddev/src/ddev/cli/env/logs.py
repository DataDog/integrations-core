# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('logs', short_help='Show logs for the Agent')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.pass_obj
def logs(app: Application, *, intg_name: str, environment: str):
    """Show backend-specific diagnostics for the Agent."""
    from ddev.e2e.agent import create_agent
    from ddev.e2e.config import EnvDataStorage

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    metadata = env_data.read_metadata()
    agent = create_agent(app, integration, environment, metadata, env_data.config_file)

    try:
        agent.show_logs()
    except Exception as e:
        app.abort(str(e))
