# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('reload', short_help='Restart the Agent to detect environment changes')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.pass_obj
def reload_command(app: Application, *, intg_name: str, environment: str):
    """
    Restart the Agent to detect environment changes.
    """
    from ddev.e2e.agent import get_agent_interface
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import DEFAULT_AGENT_TYPE, E2EMetadata

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    metadata = env_data.read_metadata()
    agent_type = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)
    agent = get_agent_interface(agent_type)(app.platform, integration, environment, metadata, env_data.config_file)

    try:
        agent.restart()
    except Exception as e:
        app.abort(str(e))

    app.display_success(f'Config reloaded: [link={env_data.config_file}]{env_data.config_file}[/]')
