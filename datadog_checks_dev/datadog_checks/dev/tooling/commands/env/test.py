# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from tempfile import NamedTemporaryFile

import click

from ...e2e import check_environment, stop_environment
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_success, echo_waiting
from .start import start


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Test an environment')
@click.argument('check')
@click.argument('env')
@click.option(
    '--agent',
    '-a',
    default='6',
    help=(
        'The agent build to use e.g. a Docker image like `datadog/agent:6.5.2`. For '
        'Docker environments you can use an integer corresponding to fields in the '
        'config (agent5, agent6, etc.)'
    ),
)
@click.option('--dev/--prod', help='Whether to use the latest version of a check or what is shipped')
@click.option('--base', is_flag=True, help='Whether to use the latest version of the base check or what is shipped')
@click.option(
    '--env-vars',
    '-e',
    multiple=True,
    help=(
        'ENV Variable that should be passed to the Agent container. '
        'Ex: -e DD_URL=app.datadoghq.com -e DD_API_KEY=123456'
    ),
)
@click.pass_context
def test(ctx, check, env, agent, dev, base, env_vars):
    """Run a check test against an environment."""
    environment = ctx.forward(start)

    environment.wait_agent_ready()

    check_file = NamedTemporaryFile()
    try:
        echo_waiting('Running check command... ', nl=False)
        check_result = environment.run_check(as_json=True, capture=True)
        if check_result.code:
            click.echo(check_result.stderr)
            echo_failure('failed!')
        else:
            echo_success('success!')
            check_output = json.loads(check_result.stdout.split('=== JSON ===', 1)[1])
            json.dump(check_output, check_file)
            check_file.flush()
            check_environment(check, env, check_file.name)
    finally:
        check_file.close()
        echo_waiting('Stopping the Agent... ', nl=False)
        environment.stop_agent()
        echo_success('success!')

        echo_waiting('Removing configuration files... ', nl=False)
        environment.remove_config()
        echo_success('success!')

        echo_waiting('Stopping the environment... ', nl=False)
        _, _, error = stop_environment(check, env, metadata=environment.metadata)
        if error:
            echo_failure('failed!')
            abort(error)
        echo_success('success!')
