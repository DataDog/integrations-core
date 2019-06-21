# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e import create_interface, get_configured_envs
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command('reload', context_settings=CONTEXT_SETTINGS, short_help='Restart an Agent to detect environment changes')
@click.argument('check')
@click.argument('env', required=False)
def reload_env(check, env):
    """Restart an Agent to detect environment changes."""
    envs = get_configured_envs(check)
    if not envs:
        echo_failure('No active environments found for `{}`.'.format(check))
        echo_info('See what is available to start via `ddev env ls {}`.'.format(check))
        abort()

    if not env:
        if len(envs) > 1:
            echo_failure('Multiple active environments found for `{}`, please specify one.'.format(check))
            echo_info('See what is active via `ddev env ls`.')
            abort()

        env = envs[0]

    if env not in envs:
        echo_failure('`{}` is not an active environment.'.format(env))
        echo_info('See what is active via `ddev env ls`.')
        abort()

    environment = create_interface(check, env)

    result = environment.restart_agent()

    if result.code:
        abort(result.stdout + result.stderr, code=result.code)
    else:
        echo_success('Successfully reloaded environment `{}`!'.format(env))
