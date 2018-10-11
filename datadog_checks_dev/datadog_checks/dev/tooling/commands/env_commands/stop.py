# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ..utils import CONTEXT_SETTINGS, DEFAULT_INDENT, abort, echo_failure, echo_info, echo_success, echo_waiting
from ...e2e import create_interface, get_configured_checks, get_configured_envs, stop_environment


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Stop environments'
)
@click.argument('check')
@click.argument('env', required=False)
def stop(check, env):
    """Stop environments."""
    all_checks = check == 'all'
    checks = get_configured_checks() if all_checks else [check]

    if all_checks:
        env_indent = DEFAULT_INDENT
        status_indent = DEFAULT_INDENT * 2
    else:
        env_indent = None
        status_indent = DEFAULT_INDENT

    for check in checks:
        if all_checks:
            envs = get_configured_envs(check)
            if envs:
                echo_success('{}:'.format(check))
        else:
            envs = [env] if env else get_configured_envs(check)

        for env in envs:
            echo_info('{}:'.format(env), indent=env_indent)
            environment = create_interface(check, env)

            echo_waiting('Stopping the Agent... ', nl=False, indent=status_indent)
            environment.stop_agent()
            echo_success('success!')

            echo_waiting('Removing configuration files... ', nl=False, indent=status_indent)
            environment.remove_config()
            echo_success('success!')

            echo_waiting('Stopping the environment... ', nl=False, indent=status_indent)
            _, _, error = stop_environment(check, env)
            if error:
                echo_failure('failed!')
                abort(error)
            echo_success('success!')
