# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e.config import locate_config_file
from ...testing import complete_active_checks, complete_configured_envs
from ...utils import is_testable_check
from ..console import CONTEXT_SETTINGS, abort, echo_failure


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Edit config file using default editor')
@click.argument('check', shell_complete=complete_active_checks)
@click.argument('env', shell_complete=complete_configured_envs)
@click.option('--editor', '-e', help='Editor to use')
@click.pass_context
def edit(ctx, check, env, editor):
    """Start an environment."""
    if not is_testable_check(check):
        abort(f'`{check}` is not a testable check.')

    config_file = locate_config_file(check, env)
    try:
        click.edit(editor=editor, filename=config_file, extension='.yaml')
    except click.ClickException as e:
        echo_failure(f'Failed to open `{config_file}` in editor. Error: {e}')
