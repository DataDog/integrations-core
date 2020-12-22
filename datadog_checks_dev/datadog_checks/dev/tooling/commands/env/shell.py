# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click

from ...e2e import create_interface, get_configured_envs
from ...testing import complete_active_checks, complete_configured_envs
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info


@click.command('shell', context_settings=CONTEXT_SETTINGS, short_help='Run a shell inside agent container')
@click.argument('check', autocompletion=complete_active_checks)
@click.argument('env', autocompletion=complete_configured_envs, required=False)
@click.option('-c', '--exec-command', help='Optionally execute command inside container, executes after any installs')
@click.option('-v', '--install-vim', is_flag=True, help='Optionally install editing/viewing tools vim and less')
@click.option('-i', '--install-tools', multiple=True, help='Optionally install custom tools')
def shell(check, env, exec_command, install_vim, install_tools):
    """Run a shell inside the Agent docker container."""
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

    if environment.ENV_TYPE == 'local':
        abort('Shell subcommand only available for docker e2e environments')

    if install_vim or install_tools:
        tools = list(install_tools)
        if install_vim:
            tools.extend(('less', 'vim'))
        echo_info(f'Installing helper tools: {", ".join(tools)}')
        environment.exec_command('/bin/bash -c "apt update && apt install -y {}"'.format(" ".join(tools)))

    if exec_command:
        echo_info(f'Executing command: {exec_command}...')
        environment.exec_command(f'/bin/bash -c "{exec_command}"')
        return

    result = environment.shell()

    if result.code:
        abort(result.stdout + result.stderr, code=result.code)
