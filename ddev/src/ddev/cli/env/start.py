# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command(short_help='Start an environment')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment')
@click.option('--dev', 'local_dev', is_flag=True, help='Install the local version of the integration')
@click.option(
    '--base',
    'local_base',
    is_flag=True,
    help='Install the local version of the base package, implicitly enabling the `--dev` option',
)
@click.option(
    '--agent',
    '-a',
    'agent_build',
    help=(
        'The Agent build to use e.g. a Docker image like `datadog/agent:latest`. You can '
        'also use the name of an Agent defined in the `agents` configuration section.'
    ),
)
@click.option(
    '-e',
    'extra_env_vars',
    multiple=True,
    help='Environment variables to pass to the Agent e.g. -e DD_URL=app.datadoghq.com -e DD_API_KEY=foobar',
)
@click.option('--dogstatsd', is_flag=True, hidden=True)
@click.option('--hide-help', is_flag=True, hidden=True)
@click.option('--ignore-state', is_flag=True, hidden=True)
@click.pass_context
def start(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str,
    local_dev: bool,
    local_base: bool,
    agent_build: str | None,
    extra_env_vars: tuple[str, ...],
    dogstatsd: bool,
    hide_help: bool,
    ignore_state: bool,
):
    """
    Start an environment.
    """
    import json
    import os
    from contextlib import suppress

    from datadog_checks.dev._env import deserialize_data

    from ddev.e2e.agent import get_agent_interface
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import DEFAULT_AGENT_TYPE, E2EEnvVars, E2EMetadata
    from ddev.e2e.run import E2EEnvironmentRunner
    from ddev.utils.fs import Path, temp_directory

    app: Application = ctx.obj
    integration = app.repo.integrations.get(intg_name)
    env_data = EnvDataStorage(app.data_dir).get(integration.name, environment)
    runner = E2EEnvironmentRunner(environment, app.verbosity)

    # Do as much error checking as possible before attempting to start the environment
    if env_data.exists():
        if ignore_state:
            return

        app.abort(f'Environment `{environment}` for integration `{integration.name}` is already running')

    local_packages: dict[Path, str] = {}
    if local_base:
        features = '[db,deps,http,json,kube]'
        if (base_package_path := (app.repo.path / 'datadog_checks_base')).is_dir():
            local_packages[base_package_path] = features
        else:
            for repo_name, repo_path in app.config.repos.items():
                if repo_name == app.repo.name:
                    continue
                elif (base_package_path := (Path(repo_path).expand() / 'datadog_checks_base')).is_dir():
                    local_packages[base_package_path] = features
                    break
            else:
                app.abort('Unable to find a local version of the base package')

        # When using multiple namespaced packages it is required that they are all
        # installed in the same way (normal versus editable)
        local_dev = True

    # Install the integration after the base package for the following reasons:
    # 1. We want the dependencies of the integration in question to take precedence
    # 2. The rare, ephemeral situation where a new version of the base package is
    #    required but is not yet released
    if local_dev:
        local_packages[integration.path] = '[deps]'

    app.display_header(f'Starting: {environment}')

    with temp_directory() as temp_dir:
        result_file = temp_dir / 'result.json'
        env_vars = {E2EEnvVars.RESULT_FILE: str(result_file)}

        with integration.path.as_cwd(env_vars=env_vars), runner.start() as command:
            process = app.platform.run_command(command)
            if process.returncode:
                app.abort(code=process.returncode)

        if not result_file.is_file():  # no cov
            app.abort(f'No E2E result file found: {result_file}')

        result = json.loads(result_file.read_text())

    metadata = result['metadata']

    # TODO Remove once we have migrated the `docker_run` function
    if serialized_volumes := metadata.get(E2EMetadata.ENV_VARS, {}).get(E2EEnvVars.DOCKER_VOLUMES):
        volumes = metadata.get(E2EMetadata.DOCKER_VOLUMES, [])
        volumes.extend(deserialize_data(serialized_volumes))
        metadata[E2EMetadata.DOCKER_VOLUMES] = volumes

    env_data.write_metadata(metadata)

    config = result['config']
    env_data.write_config(config)

    agent_type = metadata.get(E2EMetadata.AGENT_TYPE, DEFAULT_AGENT_TYPE)
    agent = get_agent_interface(agent_type)(app.platform, integration, environment, metadata, env_data.config_file)

    if not agent_build:
        agent_build = (
            os.getenv(E2EEnvVars.AGENT_BUILD_PY2 if agent.python_version[0] == 2 else E2EEnvVars.AGENT_BUILD)
            or app.config.agent.config.get(agent_type)
            or ''
        )

    agent_env_vars = _get_agent_env_vars(app.config.org.config, metadata, extra_env_vars, dogstatsd)

    try:
        agent.start(agent_build=agent_build, local_packages=local_packages, env_vars=agent_env_vars)
    except Exception as e:
        from ddev.cli.env.stop import stop

        app.display_critical(f'Unable to start the Agent: {e}')
        with suppress(Exception):
            ctx.invoke(stop, intg_name=intg_name, environment=environment)

        app.abort()

    if not hide_help:
        app.output()
        app.display_pair('Stop environment', app.style_info(f'ddev env stop {intg_name} {environment}'))
        app.display_pair('Execute tests', app.style_info(f'ddev env test {intg_name} {environment}'))
        app.display_pair('Check status', app.style_info(f'ddev env agent {intg_name} {environment} status'))
        app.display_pair('Trigger run', app.style_info(f'ddev env agent {intg_name} {environment} check'))
        app.display_pair('Reload config', app.style_info(f'ddev env reload {intg_name} {environment}'))
        app.display_pair('Manage config', app.style_info('ddev env config'))
        app.display_pair('Config file', f'[link={env_data.config_file}]{env_data.config_file}[/]')


def _get_agent_env_vars(org_config, metadata, extra_env_vars, dogstatsd):
    from ddev.e2e.constants import DEFAULT_DOGSTATSD_PORT, E2EEnvVars, E2EMetadata

    # Use the environment variables defined by tests as defaults so tooling can override them
    env_vars: dict[str, str] = metadata.get('env_vars', {}).copy()

    if api_key := org_config.get('api_key'):
        env_vars['DD_API_KEY'] = api_key

    if site := org_config.get('site'):
        env_vars['DD_SITE'] = site

    # Custom core Agent intake
    if dd_url := org_config.get('dd_url'):
        env_vars['DD_DD_URL'] = dd_url

    # Custom logs Agent intake
    if log_url := org_config.get('log_url'):
        env_vars['DD_LOGS_CONFIG_DD_URL'] = log_url

    # TODO: remove the CLI flag and exclusively rely on the metadata flag
    if metadata.get('dogstatsd') or dogstatsd:
        env_vars['DD_DOGSTATSD_PORT'] = str(DEFAULT_DOGSTATSD_PORT)
        env_vars['DD_DOGSTATSD_NON_LOCAL_TRAFFIC'] = 'true'
        env_vars['DD_DOGSTATSD_METRICS_STATS_ENABLE'] = 'true'

    # Enable logs Agent by default if the environment is mounting logs
    if any(ev.startswith(E2EEnvVars.LOGS_DIR_PREFIX) for ev in metadata.get(E2EMetadata.ENV_VARS, {})):
        env_vars.setdefault('DD_LOGS_ENABLED', 'true')

    env_vars.update(ev.split('=', maxsplit=1) for ev in extra_env_vars)

    return env_vars
