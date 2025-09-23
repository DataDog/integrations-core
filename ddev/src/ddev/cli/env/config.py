# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.group(short_help='Manage the config file')
def config():
    pass


@config.command(short_help='Edit the config file with your default editor')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.pass_obj
def edit(app: Application, *, intg_name: str, environment: str):
    """
    Edit the config file with your default editor.
    """
    from ddev.e2e.config import EnvDataStorage

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    click.edit(filename=str(env_data.config_file))


@config.command(short_help='Open the config location in your file manager')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.pass_obj
def explore(app: Application, *, intg_name: str, environment: str):
    """
    Open the config location in your file manager.
    """
    from ddev.e2e.config import EnvDataStorage

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    click.launch(str(env_data.config_file), locate=True)


@config.command(short_help='Show the location of the config file')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.pass_obj
def find(app: Application, *, intg_name: str, environment: str):
    """
    Show the location of the config file.
    """
    from ddev.e2e.config import EnvDataStorage

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    app.output(f'[link={env_data.config_file}]{env_data.config_file}[/]')


@config.command(short_help='Show the contents of the config file')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.pass_obj
def show(app: Application, *, intg_name: str, environment: str):
    """
    Show the contents of the config file.
    """
    from ddev.e2e.config import EnvDataStorage

    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)

    if not env_data.exists():
        app.abort(f'Environment `{environment}` for integration `{integration.name}` is not running')

    from rich.syntax import Syntax

    text = env_data.config_file.read_text().rstrip()
    app.output(Syntax(text, 'yaml', background_color='default'))
