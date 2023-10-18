# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(
    short_help='Invoke the Agent', context_settings={'help_option_names': [], 'ignore_unknown_options': True}
)
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.argument('args', required=True, nargs=-1)
@click.option('--config-file', hidden=True)
@click.pass_obj
def agent(app: Application, *, intg_name: str, environment: str, args: tuple[str, ...], config_file: str | None):
    """
    Invoke the Agent.
    """
    import subprocess

    from ddev.e2e.agent import get_agent_interface
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import DEFAULT_AGENT_TYPE, E2EMetadata
    from ddev.utils.fs import Path

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    metadata = env_data.read_metadata()
    agent_type = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)
    agent = get_agent_interface(agent_type)(app.platform, integration, environment, metadata, env_data.config_file)

    full_args = list(args)
    trigger_run = False
    if full_args[0] == 'check':
        trigger_run = True

        # TODO: remove this when all invocations migrate to the actual command
        if len(full_args) > 2 and full_args[1] == '--jmx-list':
            full_args = ['jmx', 'list', full_args[2]]
        # Automatically inject the integration name if not passed
        elif len(full_args) == 1 or full_args[1].startswith('-'):
            full_args.insert(1, intg_name)

    if config_file is None or not trigger_run:
        try:
            agent.invoke(full_args)
        except subprocess.CalledProcessError as e:
            app.abort(code=e.returncode)

        return

    import json

    config = json.loads(Path(config_file).read_text())

    if not env_data.config_file.is_file():
        try:
            env_data.write_config(config)
            agent.invoke(full_args)
        finally:
            env_data.config_file.unlink()
    else:
        temp_config_file = env_data.config_file.parent / f'{env_data.config_file.name}.bak.example'
        env_data.config_file.replace(temp_config_file)
        try:
            env_data.write_config(config)
            agent.invoke(full_args)
        finally:
            temp_config_file.replace(env_data.config_file)
