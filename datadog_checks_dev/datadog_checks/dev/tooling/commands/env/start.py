# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import time

import click
import pyperclip

from ....ci import running_on_ci
from ....fs import dir_exists, file_exists, path_join
from ....utils import ON_WINDOWS
from ...e2e import E2E_SUPPORTED_TYPES, derive_interface, start_environment, stop_environment
from ...e2e.agent import DEFAULT_PYTHON_VERSION, DEFAULT_SAMPLING_COLLECTION_INTERVAL
from ...git import get_current_branch
from ...testing import complete_envs, get_available_tox_envs, get_tox_env_python_version
from ...utils import complete_testable_checks, get_tox_file
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Start an environment')
@click.argument('check', autocompletion=complete_testable_checks)
@click.argument('env', autocompletion=complete_envs)
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
@click.option('--org-name', '-o', help='The org to use for data submission.')
@click.option('--profile-memory', '-pm', is_flag=True, help='Whether to collect metrics about memory usage')
@click.option('--dogstatsd', is_flag=True, help='Enable dogstatsd port on agent')
@click.pass_context
def start(ctx, check, env, agent, python, dev, base, env_vars, org_name, profile_memory, dogstatsd):
    """Start an environment."""
    if not file_exists(get_tox_file(check)):
        abort(f'`{check}` is not a testable check.')

    on_ci = running_on_ci()

    base_package = None
    if base:
        core_dir = os.path.expanduser(ctx.obj.get('core') or ctx.obj.get('repos', {}).get('core', ''))
        if not dir_exists(core_dir):
            if core_dir:
                abort(f'`{core_dir}` directory does not exist.')
            else:
                abort('`core` config setting does not exist.')

        base_package = path_join(core_dir, 'datadog_checks_base')
        if not dir_exists(base_package):
            abort('`datadog_checks_base` directory does not exist.')

    envs = get_available_tox_envs(check, e2e_only=True)

    if env not in envs:
        echo_failure(f'`{env}` is not an available environment.')
        echo_info('Available environments for {}:\n    {}'.format(check, '\n    '.join(envs)))
        echo_info(f'You can also use `ddev env ls {check}` to see available environments.')
        abort()

    env_python_version = get_tox_env_python_version(env)
    if not python:
        # Make the tox environment Python specifier influence the Agent
        python = env_python_version or DEFAULT_PYTHON_VERSION
    elif env_python_version and env_python_version != int(python):
        echo_warning(
            'The local environment `{}` does not match the expected Python. The Agent will use Python {}. '
            'To influence the Agent Python version, use the `-py/--python` option.'.format(env, python)
        )

    if not org_name:
        org_name = ctx.obj['org']
    if org_name not in ctx.obj['orgs']:
        echo_failure(f'Org `{org_name}` is not defined in your config.')
        abort()

    org = ctx.obj['orgs'].get(org_name, {})

    if profile_memory and python < 3:
        profile_memory = False
        echo_warning('Collecting metrics about memory usage is only supported on Python 3+.')

    api_key = org.get('api_key') or ctx.obj['dd_api_key']
    if api_key is None:
        echo_warning(
            'Environment variable DD_API_KEY does not exist; a well-formatted '
            'fake API key will be used instead. You can also set the API key '
            'by doing `ddev config set dd_api_key`.'
        )

    dd_url = org.get('dd_url')
    log_url = org.get('log_url')

    if profile_memory and not api_key:
        profile_memory = False
        echo_warning('No API key is set; collecting metrics about memory usage will be disabled.')

    if not dev and ctx.obj['repo_choice'] != 'core':
        echo_warning('Be sure to run environment with --dev for extras or custom integrations.')

    echo_waiting(f'Setting up environment `{env}`... ', nl=False)
    config, metadata, error = start_environment(check, env)

    if error:
        if 'does not support this platform' in error:
            echo_warning(error)
            abort(code=0)
        else:
            echo_failure('failed!')
            echo_waiting('Stopping the environment...')
            stop_environment(check, env, metadata=metadata)
            abort(error)
    echo_success('success!')

    env_type = metadata['env_type']

    # TODO: remove this legacy fallback lookup in any future major version bump
    legacy_fallback = os.path.expanduser(ctx.obj.get('agent', ''))
    if os.path.isdir(legacy_fallback):
        legacy_fallback = ''

    agent_ver = agent or os.getenv('DDEV_E2E_AGENT', legacy_fallback)
    agent_build = ctx.obj.get('agents', {}).get(
        agent_ver,
        # TODO: remove this legacy fallback lookup in any future major version bump
        ctx.obj.get(f'agent{agent_ver}', agent_ver),
    )
    if isinstance(agent_build, dict):
        agent_build = agent_build.get(env_type, env_type)

    if agent_build == 'datadog/agent:6':
        echo_warning('The Docker image for Agent 6 only ships with Python 2, will use that instead.')
        python = 2

    interface = derive_interface(env_type)
    if interface is None:
        echo_failure(f'`{env_type}` is an unsupported environment type.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort()

    if env_type not in E2E_SUPPORTED_TYPES and agent_ver.isdigit():
        echo_failure('Configuration for default Agents are only for Docker. You must specify the full build.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort()

    env_vars = dict(ev.split('=', 1) for ev in env_vars)
    for key, value in metadata.get('env_vars', {}).items():
        env_vars.setdefault(key, value)

    if dogstatsd:
        env_vars['DD_DOGSTATSD_NON_LOCAL_TRAFFIC'] = 'true'
        env_vars['DD_DOGSTATSD_METRICS_STATS_ENABLE'] = 'true'

    if profile_memory:
        plat = platform.system()
        try:
            branch = get_current_branch()
        except Exception:
            branch = 'unknown'
            echo_warning(f'Unable to detect the current Git branch, defaulting to `{branch}`.')

        env_vars['DD_TRACEMALLOC_DEBUG'] = '1'
        env_vars['DD_TRACEMALLOC_INCLUDE'] = check

        if on_ci:
            env_vars.setdefault('DD_AGGREGATOR_STOP_TIMEOUT', '10')
            env_vars.setdefault('DD_FORWARDER_STOP_TIMEOUT', '10')

        instances = config
        if isinstance(config, dict):
            instances = config.get('instances', [config])

        for instance in instances:
            instance['__memory_profiling_tags'] = [
                f'platform:{plat}',
                f'env:{env}',
                f'branch:{branch}',
            ]

            if on_ci:
                instance['min_collection_interval'] = metadata.get(
                    'sampling_collection_interval', DEFAULT_SAMPLING_COLLECTION_INTERVAL
                )

    environment = interface(
        check,
        env,
        base_package,
        config,
        env_vars,
        metadata,
        agent_build,
        api_key,
        dd_url,
        log_url,
        python,
        not bool(agent),
        dogstatsd,
    )

    echo_waiting(f'Updating `{environment.agent_build}`... ', nl=False)
    environment.update_agent()
    echo_success('success!')

    echo_waiting('Detecting the major version... ', nl=False)
    environment.detect_agent_version()
    echo_info(f'Agent {environment.agent_version} detected')

    echo_waiting(f'Writing configuration for `{env}`... ', nl=False)
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

    if ON_WINDOWS and python < 3:
        time.sleep(10)

    echo_success('success!')

    start_commands = metadata.get('start_commands', [])
    post_install_commands = metadata.get('post_install_commands', [])

    # for example, to install some tools inside container:
    # export DDEV_AGENT_START_COMMAND="bash -c 'apt update && apt install -y vim less'"
    extra_commands = os.getenv('DDEV_AGENT_START_COMMAND', None)
    if extra_commands:
        start_commands.append(extra_commands)

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
        echo_waiting(f'Upgrading `{check}` check to the development version... ', nl=False)
        if environment.ENV_TYPE == 'local' and not click.confirm(editable_warning.format(environment.check)):
            echo_success('skipping')
        else:
            environment.update_check()
            echo_success('success!')

    if post_install_commands:
        echo_waiting('Running extra post-install commands... ', nl=False)

        for command in post_install_commands:
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

    if dev or base or start_commands or post_install_commands:
        echo_waiting('Reloading the environment to reflect changes... ', nl=False)
        result = environment.restart_agent()

        if result.code:
            click.echo()
            echo_info(result.stdout + result.stderr)
            echo_failure('An error occurred.')
            echo_waiting('Stopping the environment...')
            stop_environment(check, env, metadata=metadata)
            echo_waiting('Stopping the Agent...')
            environment.stop_agent()
            environment.remove_config()
        else:
            echo_success('success!')

    # Ensure this happens after all time-consuming steps
    if profile_memory and on_ci:
        environment.metadata['sampling_start_time'] = time.time()

        echo_waiting('Updating metadata... ', nl=False)
        environment.write_config()
        echo_success('success!')

    click.echo()

    try:
        pyperclip.copy(environment.config_file)
    except Exception:
        config_message = 'Config file: '
    else:
        config_message = 'Config file (copied to your clipboard): '

    echo_success('To edit config file, do: ', nl=False)
    echo_info(f'ddev env edit {check} {env}')

    echo_success(config_message, nl=False)
    echo_info(environment.config_file)

    echo_success('To run this check, do: ', nl=False)
    echo_info(f'ddev env check {check} {env}')

    echo_success('To stop this check, do: ', nl=False)
    if ctx.obj['repo_choice'] == 'extras' and not ctx.obj.get('repo') == 'extras':
        echo_info(f'ddev -e env stop {check} {env}')
    else:
        echo_info(f'ddev env stop {check} {env}')
