# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import click
import pyperclip

from ..utils import (
    CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning
)
from ...e2e import derive_interface, start_environment, stop_environment
from ...test import get_available_tox_envs
from ...utils import get_tox_file
from ....utils import file_exists


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Start an environment'
)
@click.argument('check')
@click.argument('env')
@click.option(
    '--agent', '-a', default='6',
    help=(
        'The agent build to use e.g. a Docker image like `datadog/agent:6.5.2`. For '
        'Docker environments you can use an integer corresponding to fields in the '
        'config (agent5, agent6, etc.)'
    )
)
@click.option('--dev/--prod', help='Whether to use the latest version of a check or what is shipped')
@click.pass_context
def start(ctx, check, env, agent, dev):
    """Start an environment."""
    if not file_exists(get_tox_file(check)):
        abort('`{}` is not a testable check.'.format(check))

    envs = get_available_tox_envs(check, e2e_only=True)

    if env not in envs:
        echo_failure('`{}` is not an available environment.'.format(env))
        echo_info('See what is available via `ddev env ls {}`.'.format(check))
        abort()

    agent_build = ctx.obj.get('agent{}'.format(agent), agent)
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
        stop_environment(check, env)
        abort(error)
    echo_success('success!')

    env_type = metadata['env_type']
    interface = derive_interface(env_type)
    if interface is None:
        echo_failure('`{}` is an unsupported environment type.'.format(env_type))
        echo_waiting('Stopping the environment...')
        stop_environment(check, env)
        abort()

    if env_type != 'docker' and agent.isdigit():
        echo_failure('Configuration for default Agents are only for Docker. You must specify the full build.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env)
        abort()

    environment = interface(check, env, config, metadata, agent_build, api_key)

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
        stop_environment(check, env)
        environment.remove_config()
        abort()
    echo_success('success!')

    if dev:
        echo_waiting('Upgrading `{}` check to the development version... '.format(check), nl=False)
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
    echo_info('ddev env stop {} {}'.format(check, env))
