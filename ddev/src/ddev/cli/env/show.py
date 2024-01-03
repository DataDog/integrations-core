# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('show', short_help='Show active or available environments')
@click.argument('intg_name', required=False, metavar='INTEGRATION')
@click.argument('environment', required=False)
@click.option('--ascii', 'force_ascii', is_flag=True, help='Whether or not to only use ASCII characters')
@click.pass_obj
def show(app: Application, *, intg_name: str | None, environment: str | None, force_ascii: bool):
    """
    Show active or available environments.
    """
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import DEFAULT_AGENT_TYPE, E2EMetadata

    storage = EnvDataStorage(app.data_dir)

    # Display all active environments
    if not intg_name:
        for active_integration in storage.get_integrations():
            integration = app.repo.integrations.get(active_integration)
            envs = storage.get_environments(integration.name)

            columns: dict[str, dict[int, str]] = {'Name': {}, 'Agent type': {}}
            for i, name in enumerate(envs):
                env_data = storage.get(integration.name, name)
                metadata = env_data.read_metadata()

                columns['Name'][i] = name
                columns['Agent type'][i] = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)

            app.display_table(active_integration, columns, show_lines=True, force_ascii=force_ascii)
    # Display active and available environments for a specific integration
    elif not environment:
        import json
        import sys

        integration = app.repo.integrations.get(intg_name)
        active_envs = storage.get_environments(integration.name)

        active_columns: dict[str, dict[int, str]] = {'Name': {}, 'Agent type': {}}
        for i, name in enumerate(active_envs):
            env_data = storage.get(integration.name, name)
            metadata = env_data.read_metadata()

            active_columns['Name'][i] = name
            active_columns['Agent type'][i] = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)

        with integration.path.as_cwd():
            environments = json.loads(
                app.platform.check_command_output([sys.executable, '-m', 'hatch', 'env', 'show', '--json'])
            )

        available_columns: dict[str, dict[int, str]] = {'Name': {}}
        for i, (name, data) in enumerate(environments.items()):
            if not data.get('e2e-env') or name in active_envs:
                continue

            available_columns['Name'][i] = name

        app.display_table('Active', active_columns, show_lines=True, force_ascii=force_ascii)
        app.display_table('Available', available_columns, show_lines=True, force_ascii=force_ascii)
    # Display information about a specific environment
    else:
        from ddev.e2e.agent import get_agent_interface

        integration = app.repo.integrations.get(intg_name)
        env_data = storage.get(integration.name, environment)

        if not env_data.exists():
            app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

        metadata = env_data.read_metadata()
        agent_type = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)
        agent = get_agent_interface(agent_type)(app.platform, integration, environment, metadata, env_data.config_file)

        app.display_pair('Agent type', agent_type)
        app.display_pair('Agent ID', agent.get_id())
