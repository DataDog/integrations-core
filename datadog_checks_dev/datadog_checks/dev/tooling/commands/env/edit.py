# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from datadog_checks.dev.tooling.e2e.config import locate_config_file

from ....fs import file_exists
from ...testing import complete_envs
from ...utils import complete_testable_checks, get_tox_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Edit config file')
@click.argument('check', autocompletion=complete_testable_checks)
@click.argument('env', autocompletion=complete_envs)
@click.pass_context
def edit(ctx, check, env):
    """Start an environment."""
    if not file_exists(get_tox_file(check)):
        abort(f'`{check}` is not a testable check.')

    config_file = locate_config_file(check, env)
    print(config_file)
    try:
        click.edit(filename=config_file)
    except click.ClickException as e:
        echo_failure(f'Failed to open `{config_file}` in editor. Error: {e}')
