# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import time

import click

from ....ci import running_on_ci
from ....fs import dir_exists, path_join
from ....utils import ON_WINDOWS
from ...e2e import E2E_SUPPORTED_TYPES, derive_interface, start_environment, stop_environment
from ...e2e.agent import DEFAULT_PYTHON_VERSION, DEFAULT_SAMPLING_COLLECTION_INTERVAL
from ...git import get_current_branch
from ...testing import complete_envs, get_active_env_python_version, get_available_envs
from ...utils import complete_testable_checks, is_testable_check
from ..console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_waiting, echo_warning

dev_option = click.option(
    '--dev/--prod',
    default=None,
    help=(
        'By default we use version of the check that is shipped with the agent you are using.'
        'Pass --dev to explicitly enforce the local version. Also see the `--base` option.'
    ),
)
base_option = click.option(
    '--base',
    is_flag=True,
    help=(
        'Pass this flag to mount the local version of the base package. By default we use the version shipped '
        'with the agent. Note that passing the flag also mounts the local version of the check.\n\n'
        'More about the base package: https://datadoghq.dev/integrations-core/base/about/'
    ),
)


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Start an environment')
@click.argument('check', shell_complete=complete_testable_checks)
@click.argument('env', shell_complete=complete_envs)
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
@click.option('--org-name', '-o', help='The org to use for data submission.')
@click.option('--profile-memory', '-pm', is_flag=True, help='Whether to collect metrics about memory usage')
@click.option('--dogstatsd', is_flag=True, help='Enable dogstatsd port on agent')
@click.pass_context
def start(ctx, check, env, agent, python, dev, base, env_vars, org_name, profile_memory, dogstatsd):
    """Start an environment."""

    on_ci = running_on_ci()
    environment, metadata, python = _start_environment(
        ctx, base, check, env, python, org_name, profile_memory, agent, env_vars, dogstatsd, dev, on_ci
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
    _start_agent(environment, check, env, metadata, python)
    echo_success('success!')

    ran_start_commnad = _run_start_commands(metadata, environment, check, env)
    dev_or_base = _perform_updates(base, dev, environment, check)
    ran_post_install_commands = _run_post_install_commands(metadata, environment, check, env)

    if ran_start_commnad or dev_or_base or ran_post_install_commands:
        _reload(environment, check, env, metadata)

    # Ensure this happens after all time-consuming steps
    if profile_memory and on_ci:
        _start_sampling(environment)

    click.echo()

    echo_success('Config file: ', nl=False)
    echo_info(environment.config_file)

    echo_success('To edit config file, do: ', nl=False)
    echo_info(f'ddev env edit {check} {env}')

    echo_success('To reload the config file, do: ', nl=False)
    echo_info(f'ddev env reload {check} {env}')

    echo_success('To run this check, do: ', nl=False)
    echo_info(f'ddev env check {check} {env}')

    echo_success('To stop this check, do: ', nl=False)
    if ctx.obj['repo_choice'] == 'extras' and not ctx.obj.get('repo') == 'extras':
        echo_info(f'ddev -e env stop {check} {env}')
    else:
        echo_info(f'ddev env stop {check} {env}')


def _start_environment(ctx, base, check, env, python, org_name, profile_memory, agent, env_vars, dogstatsd, dev, on_ci):
    if not is_testable_check(check):
        abort(f'`{check}` is not a testable check.')

    base_package = _get_base_package(base, ctx)
    _check_env(check, env)
    python = _get_python_version(env, python)

    org = _get_org(org_name, ctx)
    dd_site = org.get('site')
    dd_url = org.get('dd_url')
    log_url = org.get('log_url')

    api_key = _get_api_key(org, ctx)
    profile_memory = _check_profile_memory(profile_memory, python, api_key)

    if not dev and ctx.obj['repo_choice'] != 'core':
        echo_warning('Be sure to run environment with --dev for extras or custom integrations.')

    echo_waiting(f'Setting up environment `{env}`... ', nl=False)
    config, metadata, error = start_environment(check, env)

    if error:
        _handle_error(error, check, env, metadata)
    echo_success('success!')

    agent_ver = _get_agent_ver(ctx, python, agent)
    env_type = _get_env_type(metadata, agent_ver, check, env)
    agent_build = _get_agent_build(ctx, agent_ver, env_type)
    if agent_build == 'datadog/agent:6':
        echo_warning('The Docker image for Agent 6 only ships with Python 2, will use that instead.')
        python = 2

    interface = _get_interface(env_type, check, env, metadata)
    env_vars = _get_env_vars(env_vars, metadata, dogstatsd, profile_memory, check, on_ci)
    _add_memory_profile_options_to_instances(profile_memory, config, metadata, on_ci, env)

    environment = interface(
        check,
        env,
        base_package,
        config,
        env_vars,
        metadata,
        agent_build,
        api_key,
        dd_site,
        dd_url,
        log_url,
        python,
        not bool(agent),
        dogstatsd,
    )
    return environment, metadata, python


def _start_agent(environment, check, env, metadata, python):
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


def _run_start_commands(metadata, environment, check, env):
    ran_start_commnad = False
    start_commands = metadata.get('start_commands', [])

    # for example, to install some tools inside container:
    # export DDEV_AGENT_START_COMMAND="bash -c 'apt update && apt install -y vim less'"
    extra_commands = os.getenv('DDEV_AGENT_START_COMMAND', None)
    if extra_commands:
        start_commands.append(extra_commands)

    if start_commands:
        ran_start_commnad = True
        echo_waiting('Running extra start-up commands... ', nl=False)

        for command in start_commands:
            result = environment.exec_command(command, capture=True)
            if result.code:
                click.echo()
                echo_failure('An error occurred running "{}". Exit code: {}'.format(str(command), result.code))
                echo_failure(result.stdout + result.stderr, indent=True)
                echo_waiting('Stopping the environment...')
                stop_environment(check, env, metadata=metadata)
                echo_waiting('Stopping the Agent...')
                environment.stop_agent()
                environment.remove_config()
                abort()

        echo_success('success!')
    return ran_start_commnad


def _run_post_install_commands(metadata, environment, check, env):
    ran_post_install_commands = False
    post_install_commands = metadata.get('post_install_commands', [])
    if post_install_commands:
        ran_post_install_commands = True
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
    return ran_post_install_commands


def _reload(environment, check, env, metadata):
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


def _start_sampling(environment):
    environment.metadata['sampling_start_time'] = time.time()

    echo_waiting('Updating metadata... ', nl=False)
    environment.write_config()
    echo_success('success!')


def _perform_updates(base, dev, environment, check):
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
    return dev or base


def _get_base_package(base, ctx):
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
    return base_package


def _check_env(check, env):
    envs = get_available_envs(check, e2e_only=True)

    if env not in envs:
        echo_failure(f'`{env}` is not an available environment.')
        echo_info('Available environments for {}:\n    {}'.format(check, '\n    '.join(envs)))
        echo_info(f'You can also use `ddev env ls {check}` to see available environments.')
        abort()


def _get_python_version(env, python):
    env_python_version = get_active_env_python_version(env)
    if not python:
        # Make the environment Python specifier influence the Agent
        python = env_python_version or DEFAULT_PYTHON_VERSION
    elif env_python_version and env_python_version != int(python):
        echo_warning(
            'The local environment `{}` does not match the expected Python. The Agent will use Python {}. '
            'To influence the Agent Python version, use the `-py/--python` option.'.format(env, python)
        )
    return python


def _get_org(org_name, ctx):
    if not org_name:
        org_name = ctx.obj['org']
    if org_name not in ctx.obj['orgs']:
        echo_failure(f'Org `{org_name}` is not defined in your config.')
        abort()
    org = ctx.obj['orgs'].get(org_name, {})
    return org


def _get_api_key(org, ctx):
    api_key = org.get('api_key') or ctx.obj['dd_api_key']
    if api_key is None:
        echo_warning(
            'Environment variable DD_API_KEY does not exist; a well-formatted '
            'fake API key will be used instead. You can also set the API key '
            'by doing `ddev config set dd_api_key`.'
        )
    return api_key


def _check_profile_memory(profile_memory, python, api_key):
    if profile_memory and python < 3:
        profile_memory = False
        echo_warning('Collecting metrics about memory usage is only supported on Python 3+.')

    if profile_memory and not api_key:
        profile_memory = False
        echo_warning('No API key is set; collecting metrics about memory usage will be disabled.')
    return profile_memory


def _handle_error(error, check, env, metadata):
    if 'does not support this platform' in error:
        echo_warning(error)
        abort(code=0)
    else:
        echo_failure('failed!')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort(error)


def _get_agent_ver(ctx, python, agent):
    # TODO: remove this legacy fallback lookup in any future major version bump
    legacy_fallback = os.path.expanduser(ctx.obj.get('agent', ''))
    if os.path.isdir(legacy_fallback):
        legacy_fallback = ''

    fallback = os.getenv('DDEV_E2E_AGENT') or legacy_fallback
    # DDEV_E2E_AGENT_PY2 overrides DDEV_E2E_AGENT when starting a Python 2 environment
    if python == 2 and os.getenv('DDEV_E2E_AGENT_PY2'):
        fallback = os.getenv('DDEV_E2E_AGENT_PY2')
    agent_ver = agent or fallback
    return agent_ver


def _get_agent_build(ctx, agent_ver, env_type):
    agent_build = ctx.obj.get('agents', {}).get(
        agent_ver,
        # TODO: remove this legacy fallback lookup in any future major version bump
        ctx.obj.get(f'agent{agent_ver}', agent_ver),
    )
    if isinstance(agent_build, dict):
        agent_build = agent_build.get(env_type, env_type)

    return agent_build


def _get_interface(env_type, check, env, metadata):
    interface = derive_interface(env_type)
    if interface is None:
        echo_failure(f'`{env_type}` is an unsupported environment type.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort()
    return interface


def _get_env_type(metadata, agent_ver, check, env):
    env_type = metadata['env_type']
    if env_type not in E2E_SUPPORTED_TYPES and agent_ver.isdigit():
        echo_failure('Configuration for default Agents are only for Docker. You must specify the full build.')
        echo_waiting('Stopping the environment...')
        stop_environment(check, env, metadata=metadata)
        abort()
    return env_type


def _get_env_vars(env_vars, metadata, dogstatsd, profile_memory, check, on_ci):
    env_vars = dict(ev.split('=', 1) for ev in env_vars)
    for key, value in metadata.get('env_vars', {}).items():
        env_vars.setdefault(key, value)

        # Enable logs agent by default if the environment is mounting logs, see:
        # https://github.com/DataDog/integrations-core/pull/5346
        if key.startswith('DDEV_E2E_ENV_TEMP_DIR_DD_LOG_'):
            env_vars.setdefault('DD_LOGS_ENABLED', 'true')

    if dogstatsd:
        env_vars['DD_DOGSTATSD_NON_LOCAL_TRAFFIC'] = 'true'
        env_vars['DD_DOGSTATSD_METRICS_STATS_ENABLE'] = 'true'

    if profile_memory:
        env_vars['DD_TRACEMALLOC_DEBUG'] = '1'
        env_vars['DD_TRACEMALLOC_INCLUDE'] = check

        if on_ci:
            env_vars.setdefault('DD_AGGREGATOR_STOP_TIMEOUT', '10')
            env_vars.setdefault('DD_FORWARDER_STOP_TIMEOUT', '10')
    return env_vars


def _add_memory_profile_options_to_instances(profile_memory, config, metadata, on_ci, env):
    instances = config
    if profile_memory:
        try:
            branch = get_current_branch()
        except Exception:
            branch = 'unknown'
            echo_warning(f'Unable to detect the current Git branch, defaulting to `{branch}`.')

        plat = platform.system()
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
    return instances
