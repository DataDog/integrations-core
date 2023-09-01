# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from .... import EnvVars
from ...e2e import create_interface, get_configured_envs
from ...e2e.agent import DEFAULT_PYTHON_VERSION
from ...testing import complete_active_checks, get_test_envs
from ..console import CONTEXT_SETTINGS, DEBUG_OUTPUT, echo_info, echo_warning
from ..test import test as test_command
from .start import base_option, dev_option, start
from .stop import stop


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Test an environment')
@click.argument('checks', shell_complete=complete_active_checks, nargs=-1)
@click.option(
    '--agent',
    '-a',
    help=(
        'The agent build to use e.g. a Docker image like `datadog/agent:latest`. You can '
        'also use the name of an agent defined in the `agents` configuration section.'
    ),
)
@click.option(
    '--python',
    '-py',
    type=click.INT,
    help=f'The version of Python to use. Defaults to {DEFAULT_PYTHON_VERSION} if no tox Python is specified.',
)
@dev_option
@base_option
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
@click.option('--profile-memory', '-pm', is_flag=True, help='Whether to collect metrics about memory usage')
@click.option('--junit', '-j', 'junit', is_flag=True, help='Generate junit reports')
@click.option('--ddtrace', is_flag=True, help='Run tests using dd-trace-py')
@click.option('--filter', '-k', 'test_filter', help='Only run tests matching given substring expression')
@click.option('--changed', is_flag=True, help='Only test changed checks')
@click.option('--debug', '-d', is_flag=True, help='Set the log level to debug')
@click.option(
    '--skip-failed-environments', '-sfe', is_flag=True, help='Skip environments that failed to start and continue'
)
@click.pass_context
def test(
    ctx,
    checks,
    agent,
    python,
    dev,
    base,
    env_vars,
    new_env,
    profile_memory,
    junit,
    ddtrace,
    test_filter,
    changed,
    debug,
    skip_failed_environments,
):
    """Test an environment."""
    check_envs = get_test_envs(checks, e2e_tests_only=True, changed_only=changed)
    tests_ran = False

    # If no checks or a subset of checks are specified it means we're testing what has changed compared
    # to master, probably on CI rather than during local development. In this case,
    # ensure environments and Agents are spun up and down.
    if not checks or changed:
        new_env = True

    # Default to testing the local development version.
    if dev is None:
        dev = True

    if profile_memory and not new_env:
        echo_warning('Ignoring --profile-memory, to utilize that you must also select --new-env')

    for check, envs in check_envs:
        if not envs:
            echo_warning(
                f'No end-to-end environments found for `{check}`. Make sure to add them to the {check}/hatch.toml file.'
            )
            continue

        config_envs = get_configured_envs(check)

        # For performance reasons we're generating what to test on the fly and therefore
        # need a way to tell if anything ran since we don't know anything upfront.
        tests_ran = True

        for env in envs:
            if new_env:
                try:
                    ctx.invoke(
                        start,
                        check=check,
                        env=env,
                        agent=agent,
                        python=python,
                        dev=dev,
                        base=base,
                        env_vars=env_vars,
                        profile_memory=profile_memory,
                    )
                except SystemExit:
                    if skip_failed_environments:
                        echo_warning(f"Skipping {env} environment because it failed to start.")
                        continue
                    raise
            elif env not in config_envs:
                continue

            environment = create_interface(check, env)
            persisted_env_vars = environment.metadata.get('env_vars', {})

            try:
                with EnvVars(persisted_env_vars):
                    ctx.invoke(
                        test_command,
                        checks=[f'{check}:{env}'],
                        debug=debug or DEBUG_OUTPUT,
                        e2e=True,
                        passenv=' '.join(persisted_env_vars) if persisted_env_vars else None,
                        junit=junit,
                        ddtrace=ddtrace,
                        test_filter=test_filter,
                        latest=env == 'latest',
                    )
            finally:
                if new_env:
                    ctx.invoke(stop, check=check, env=env)

    if not tests_ran:
        echo_info('Nothing to test!')
