# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import click
import pyperclip
from six import string_types

from ....utils import dir_exists, file_exists, path_join
from ...e2e import E2E_SUPPORTED_TYPES, derive_interface, start_environment, stop_environment
from ...testing import get_available_tox_envs
from ...utils import get_tox_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Start an environment')
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
def start(ctx, check, env, agent, dev, base, env_vars):
    """Start an environment."""
    if not file_exists(get_tox_file(check)):
        abort('`{}` is not a testable check.'.format(check))

    base_package = None
    if base:
        core_dir = os.path.expanduser(ctx.obj.get('core', ''))
        if not dir_exists(core_dir):
            if core_dir:
                abort('`{}` directory does not exist.'.format(core_dir))
            else:
                abort('`core` config setting does not exist.')

        base_package = path_join(core_dir, 'datadog_checks_base')
        if not dir_exists(base_package):
            abort('`datadog_checks_base` directory does not exist.')

    envs = get_available_tox_envs(check, e2e_only=True)

    if env not in envs:
        echo_failure('`{}` is not an available environment.'.format(env))
        echo_info('See what is available via `ddev env ls {}`.'.format(check))
        abort()

    api_key = ctx.obj['dd_api_key']
    if api_key is None:
        echo_warning(
            'Environment variable DD_API_KEY does not exist; a well-formatted '
            'fake API key will be used instead. You can also set the API key '
            'by doing `ddev config set dd_api_key`.'
        )

    echo_waiting('Setting up environment `{}`... '.format(env), nl=False)
    config, metadata, error = start_environment(check, env)

    if error:
        echo_failure('failed!')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort(error)
    echo_success('success!')

    env_type = metadata['env_type']
    use_jmx = metadata.get('use_jmx', False)

    # Support legacy config where agent5 and agent6 were strings
    agent_ver = ctx.obj.get('agent{}'.format(agent), agent)
    if isinstance(agent_ver, string_types):
        agent_build = agent_ver
        if agent_ver != agent:
            echo_warning(
                'Agent fields missing from ddev config, please update to the latest config via '
                '`ddev config update`, falling back to latest docker image...'
            )
    else:
        agent_build = agent_ver.get(env_type, env_type)

    if not isinstance(agent_ver, string_types) and use_jmx:
        agent_build = '{}-jmx'.format(agent_build)

    interface = derive_interface(env_type)
    if interface is None:
        echo_failure('`{}` is an unsupported environment type.'.format(env_type))
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort()

    if env_type not in E2E_SUPPORTED_TYPES and agent.isdigit():
        echo_failure('Configuration for default Agents are only for Docker. You must specify the full build.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort()

    environment = interface(check, env, base_package, config, env_vars, metadata, agent_build, api_key)

    echo_waiting('Updating `{}`... '.format(agent_build), nl=False)
    environment.update_agent()
    echo_success('success!')

    echo_waiting('Detecting the major version... ', nl=False)
    environment.detect_agent_version()
    echo_info('Agent {} detected'.format(environment.agent_version))

    echo_waiting('Writing configuration for `{}`... '.format(env), nl=False)
    environment.write_config()
    echo_success('success!')

    echo_waiting('Starting the Agent... ', nl=False)
    result = environment.start_agent()
    if result.code:
        click.echo()
        echo_info(result.stdout + result.stderr)
        echo_failure('An error occurred.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        environment.remove_config()
        abort()
    echo_success('success!')

    start_commands = metadata.get('start_commands', [])
    if start_commands:
        echo_waiting('Running extra start-up commands... ', nl=False)

        for command in start_commands:
            result = environment.exec_command(command, capture=True)
            if result.code:
                click.echo()
                echo_info(result.stdout + result.stderr)
                echo_failure('An error occurred.')
                echo_waiting('Stopping the environment...')
                stop_environment(check, env, metadata=metadata)
                echo_waiting('Stopping the Agent...')
                environment.stop_agent()
                environment.remove_config()
                abort()

        echo_success('success!')

    if base and not dev:
        dev = True
        echo_info(
            'Will install the development version of the check too so the base package can import it (in editable mode)'
        )

    editable_warning = (
        '\nEnv will started with an editable check install for the {} package. '
        'This check will remain in an editable install after '
        'the environment is torn down. Would you like to proceed?'
    )

    if base:
        echo_waiting('Upgrading the base package to the development version... ', nl=False)
        if environment.ENV_TYPE == 'local' and not click.confirm(editable_warning.format('base')):
            echo_success('skipping')
        else:
            environment.update_base_package()
            echo_success('success!')

    if dev:
        echo_waiting('Upgrading `{}` check to the development version... '.format(check), nl=False)
        if environment.ENV_TYPE == 'local' and not click.confirm(editable_warning.format(environment.check)):
            echo_success('skipping')
        else:
            environment.update_check()
            echo_success('success!')

    click.echo()

    try:
        pyperclip.copy(environment.config_file)
    except Exception:
        config_message = 'Config file: '
    else:
        config_message = 'Config file (copied to your clipboard): '

    echo_success(config_message, nl=False)
    echo_info(environment.config_file)

    echo_success('To run this check, do: ', nl=False)
    echo_info('ddev env check {} {}'.format(check, env))

    echo_success('To stop this check, do: ', nl=False)
    if ctx.obj['repo_choice'] == 'extras' and not ctx.obj.get('repo') == 'extras':
        echo_info('ddev -e env stop {} {}'.format(check, env))
    else:
        echo_info('ddev env stop {} {}'.format(check, env))
