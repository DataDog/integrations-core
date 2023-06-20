# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
import pluggy
from datadog_checks.dev.tooling.commands.create import create
from datadog_checks.dev.tooling.commands.dep import dep
from datadog_checks.dev.tooling.commands.run import run
from datadog_checks.dev.tooling.commands.test import test

from ddev._version import __version__
from ddev.cli.application import Application
from ddev.cli.ci import ci
from ddev.cli.clean import clean
from ddev.cli.config import config
from ddev.cli.docs import docs
from ddev.cli.env import env
from ddev.cli.meta import meta
from ddev.cli.release import release
from ddev.cli.status import status
from ddev.cli.validate import validate
from ddev.config.constants import AppEnvVars, ConfigEnvVars
from ddev.plugin import specs
from ddev.utils.ci import running_in_ci
from ddev.utils.fs import Path


@click.group(context_settings={'help_option_names': ['-h', '--help']}, invoke_without_command=True)
@click.option('--core', '-c', is_flag=True, help='Work on `integrations-core`.')
@click.option('--extras', '-e', is_flag=True, help='Work on `integrations-extras`.')
@click.option('--marketplace', '-m', is_flag=True, help='Work on `marketplace`.')
@click.option('--agent', '-a', is_flag=True, help='Work on `datadog-agent`.')
@click.option('--here', '-x', is_flag=True, help='Work on the current location.')
@click.option(
    '--color/--no-color',
    default=None,
    help='Whether or not to display colored output (default is auto-detection) [env vars: `DDEV_COLOR`/`NO_COLOR`]',
)
@click.option(
    '--interactive/--no-interactive',
    envvar=AppEnvVars.INTERACTIVE,
    default=None,
    help=(
        'Whether or not to allow features like prompts and progress bars (default is auto-detection) '
        '[env var: `DDEV_INTERACTIVE`]'
    ),
)
@click.option(
    '--verbose',
    '-v',
    envvar=AppEnvVars.VERBOSE,
    count=True,
    help='Increase verbosity (can be used additively) [env var: `DDEV_VERBOSE`]',
)
@click.option(
    '--quiet',
    '-q',
    envvar=AppEnvVars.QUIET,
    count=True,
    help='Decrease verbosity (can be used additively) [env var: `DDEV_QUIET`]',
)
@click.option(
    '--config',
    'config_file',
    envvar=ConfigEnvVars.CONFIG,
    help='The path to a custom config file to use [env var: `DDEV_CONFIG`]',
)
@click.version_option(version=__version__, prog_name='ddev')
@click.pass_context
def ddev(ctx: click.Context, core, extras, marketplace, agent, here, color, interactive, verbose, quiet, config_file):
    """
    \b
         _     _
      __| | __| | _____   __
     / _` |/ _` |/ _ \\ \\ / /
    | (_| | (_| |  __/\\ V /
     \\__,_|\\__,_|\\___| \\_/
    """
    if color is None:
        if os.environ.get(AppEnvVars.NO_COLOR) == '1':
            color = False
        elif os.environ.get(AppEnvVars.FORCE_COLOR) == '1':
            color = True

    if interactive is None:
        interactive = not running_in_ci()

    app = Application(ctx.exit, verbose - quiet, color, interactive)

    if config_file:
        app.config_file.path = Path(config_file).resolve()
        if not app.config_file.path.is_file():
            app.abort(f'The selected config file `{str(app.config_file.path)}` does not exist.')
    elif not app.config_file.path.is_file():
        if app.verbose:
            app.display_waiting('No config file found, creating one with default settings now...')

        try:
            app.config_file.restore()
            if app.verbose:
                app.display_success('Success! Please see `ddev config`.')
        except OSError:  # no cov
            app.abort(
                f'Unable to create config file located at `{str(app.config_file.path)}`. Please check your permissions.'
            )

    if not ctx.invoked_subcommand:
        app.display_info(ctx.get_help(), highlight=False)
        return

    # Persist app data for sub-commands
    ctx.obj = app

    try:
        app.config_file.load()
    except OSError as e:  # no cov
        app.abort(f'Error loading configuration: {e}')

    app.set_repo(core, extras, marketplace, agent, here)

    app.config.terminal.styles.parse_fields()
    errors = app.initialize_styles(app.config.terminal.styles.raw_data)
    if errors and color is not False and not app.quiet:  # no cov
        for error in errors:
            app.display_warning(error)

    # TODO: remove this when the old CLI is gone
    app.initialize_old_cli()


ddev.add_command(ci)
ddev.add_command(clean)
ddev.add_command(config)
ddev.add_command(create)
ddev.add_command(dep)
ddev.add_command(docs)
ddev.add_command(env)
ddev.add_command(meta)
ddev.add_command(release)
ddev.add_command(run)
ddev.add_command(status)
ddev.add_command(test)
ddev.add_command(validate)

__management_command = os.environ.get('PYAPP_COMMAND_NAME', '')
if __management_command:
    ddev.add_command(click.Command(name=__management_command, help='Manage this application'))


def main():  # no cov
    manager = pluggy.PluginManager('ddev')
    manager.add_hookspecs(specs)
    manager.load_setuptools_entrypoints('ddev')
    manager.hook.register_commands()

    try:
        return ddev(prog_name='ddev', windows_expand_args=False)
    except Exception:
        from rich.console import Console

        console = Console()
        console.print_exception(suppress=[click])
        return 1
