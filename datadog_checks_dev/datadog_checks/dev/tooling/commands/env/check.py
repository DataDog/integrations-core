# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import click

from ....utils import read_file
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
@click.option('--table', 'as_table', is_flag=True, help='Format the aggregator and check runner output as tabular')
@click.option(
    '--breakpoint',
    '-b',
    'break_point',
    type=click.INT,
    help='Line number to start a PDB session (0: first line, -1: last line)',
)
@click.option('--config', 'config_file', help='Path to a JSON check configuration to use')
@click.option('--jmx-list', 'jmx_list', help='JMX metrics listing method')
def check_run(check, env, rate, times, pause, delay, log_level, as_json, as_table, break_point, config_file, jmx_list):
    """Run an Agent check."""
    envs = get_configured_envs(check)
    if not envs:
        echo_failure(f'No active environments found for `{check}`.')
        echo_info(f'See what is available to start via `ddev env ls {check}`.')
        abort()

    if not env:
        if len(envs) > 1:
            echo_failure(f'Multiple active environments found for `{check}`, please specify one.')
            echo_info('See what is active via `ddev env ls`.')
            abort()

        env = envs[0]

    if env not in envs:
        echo_failure(f'`{env}` is not an active environment.')
        echo_info('See what is active via `ddev env ls`.')
        abort()

    environment = create_interface(check, env)
    check_args = dict(
        rate=rate,
        times=times,
        pause=pause,
        delay=delay,
        log_level=log_level,
        as_json=as_json,
        as_table=as_table,
        break_point=break_point,
        jmx_list=jmx_list,
    )

    if config_file:
        config = json.loads(read_file(config_file))
        with environment.use_config(config):
            environment.run_check(**check_args)
    else:
        environment.run_check(**check_args)

        if not rate and not as_json:
            echo_success('Note: ', nl=False)
            echo_info(
                'If some metrics are missing, you may want to try again with the -r / --rate flag '
                'for a classic integration.'
            )
