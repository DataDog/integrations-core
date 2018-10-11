# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..utils import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success
from ...e2e import create_interface, get_configured_envs


@click.command(
    'check',
    context_settings=CONTEXT_SETTINGS,
    short_help='Run an Agent check'
)
@click.argument('check')
@click.argument('env', required=False)
@click.option('--rate', '-r', is_flag=True)
def check_run(check, env, rate):
    """Run an Agent check."""
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

    environment.run_check(rate=rate)
    echo_success('Note: ', nl=False)
    echo_info('If some metrics are missing, you may want to try again with the -r / --rate flag.')
