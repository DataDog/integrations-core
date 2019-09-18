# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .... import EnvVars
from ...e2e import create_interface, get_configured_envs
from ...e2e.agent import DEFAULT_PYTHON_VERSION
from ...testing import get_tox_envs
from ..console import CONTEXT_SETTINGS, echo_info, echo_warning
from ..test import test as test_command
from .start import start
from .stop import stop


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Test an environment')
@click.argument('checks', nargs=-1)
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
@click.option(
    '--python',
    '-py',
    type=click.INT,
    help='The version of Python to use. Defaults to {} if no tox Python is specified.'.format(DEFAULT_PYTHON_VERSION),
)
@click.option('--dev/--prod', default=None, help='Whether to use the latest version of a check or what is shipped')
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
@click.option('--new-env', '-ne', is_flag=True, help='Execute setup and tear down actions')
@click.pass_context
def test(ctx, checks, agent, python, dev, base, env_vars, new_env):
    """Test an environment."""
    check_envs = get_tox_envs(checks, e2e_tests_only=True)
    tests_ran = False

    # If no checks are specified it means we're testing what has changed compared
    # to master, probably on CI rather than during local development. In this case,
    # ensure environments and Agents are spun up and down.
    if not checks:
        new_env = True

    # Default to testing the local development version.
    if dev is None:
        dev = True

    for check, envs in check_envs:
        if not envs:
            echo_warning('No end-to-end environments found for `{}`'.format(check))
            continue

        config_envs = get_configured_envs(check)

        # For performance reasons we're generating what to test on the fly and therefore
        # need a way to tell if anything ran since we don't know anything upfront.
        tests_ran = True

        for env in envs:
            if new_env:
                ctx.invoke(
                    start, check=check, env=env, agent=agent, python=python, dev=dev, base=base, env_vars=env_vars
                )
            elif env not in config_envs:
                continue

            environment = create_interface(check, env)
            persisted_env_vars = environment.metadata.get('env_vars', {})

            try:
                with EnvVars(persisted_env_vars):
                    ctx.invoke(
                        test_command,
                        checks=['{}:{}'.format(check, env)],
                        e2e=True,
                        passenv=' '.join(persisted_env_vars) if persisted_env_vars else None,
                    )
            finally:
                if new_env:
                    ctx.invoke(stop, check=check, env=env)

    if not tests_ran:
        echo_info('Nothing to test!')
