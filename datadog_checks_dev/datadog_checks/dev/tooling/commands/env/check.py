# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e import create_interface, get_configured_envs
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success


@click.command('check', context_settings=CONTEXT_SETTINGS, short_help='Run an Agent check')
@click.argument('check')
@click.argument('env', required=False)
@click.option(
    '--rate', '-r', is_flag=True, help='Compute rates by running the check twice with a pause between each run'
)
@click.option('--times', '-t', type=click.INT, help='Number of times to run the check')
@click.option('--pause', type=click.INT, help='Number of milliseconds to pause between multiple check runs')
@click.option(
    '--delay',
    '-d',
    type=click.INT,
    help='Delay in milliseconds between running the check and grabbing what was collected',
)
@click.option('--log-level', '-l', help='Set the log level (default `off`)')
@click.option('--json', 'as_json', is_flag=True, help='Format the aggregator and check runner output as JSON')
@click.option(
    '--breakpoint',
    '-b',
    'break_point',
    type=click.INT,
    help='Line number to start a PDB session (0: first line, -1: last line)',
)
def check_run(check, env, rate, times, pause, delay, log_level, as_json, break_point):
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

    environment.run_check(
        rate=rate, times=times, pause=pause, delay=delay, log_level=log_level, as_json=as_json, break_point=break_point
    )
    echo_success('Note: ', nl=False)
    echo_info('If some metrics are missing, you may want to try again with the -r / --rate flag.')
