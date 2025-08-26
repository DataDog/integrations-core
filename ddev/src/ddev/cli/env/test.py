# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.utils.hatch import Environment


@click.command('test')
@click.argument('intg_name', metavar='INTEGRATION')
@click.argument('environment', required=False)
@click.argument('pytest_args', nargs=-1)
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
@click.option('--junit', is_flag=True, hidden=True)
@click.option('--python-filter', envvar='PYTHON_FILTER', hidden=True)
@click.option('--new-env', is_flag=True, hidden=True)
@click.pass_context
def test_command(
    ctx: click.Context,
    *,
    intg_name: str,
    environment: str | None,
    pytest_args: tuple[str, ...],
    local_dev: bool,
    local_base: bool,
    agent_build: str | None,
    extra_env_vars: tuple[str, ...],
    junit: bool,
    python_filter: str | None,
    new_env: bool,
):
    """
    Test environments.

    This runs the end-to-end tests.

    If no ENVIRONMENT is specified, `active` is selected which will test all environments
    that are currently running. You may choose `all` to test all environments whether or not
    they are running.

    Testing active environments will not stop them after tests complete. Testing environments
    that are not running will start and stop them automatically.

    See these docs for to pass ENVIRONMENT and PYTEST_ARGS:

    \b
    https://datadoghq.dev/integrations-core/testing/
    """
    from functools import partial

    from ddev.cli.env.start import start
    from ddev.cli.env.stop import stop
    from ddev.cli.test import test
    from ddev.config.constants import AppEnvVars
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import E2EMetadata
    from ddev.utils.ci import running_in_ci
    from ddev.utils.hatch import HatchCommandError, list_environment_names
    from ddev.utils.structures import EnvVars

    app: Application = ctx.obj
    integration = app.repo.integrations.get(intg_name)

    storage = EnvDataStorage(app.data_dir)
    active_envs = storage.get_environments(integration.name)

    if environment is None:
        environment = 'all' if (not active_envs or running_in_ci()) else 'active'

    if environment == 'active':
        env_names = active_envs
    else:
        try:
            env_names = list_environment_names(
                app.platform,
                integration,
                filters=[
                    is_e2e_environment,
                    partial(uses_python_version, python_filter=python_filter),
                    partial(uses_platform, platform=app.platform.name),
                    partial(is_selected_environment, environment_name=environment),
                ],
            )
        except HatchCommandError as error:
            app.abort(f'Failed to list environments for `{integration.name}`:\n{error}')

    if not env_names:
        app.display_info(f"Selected target {integration.name!r} disabled by e2e-env option.")
        return

    app.display_header(integration.display_name)

    active = set(active_envs)
    for env_name in env_names:
        env_active = env_name in active
        ctx.invoke(
            start,
            intg_name=intg_name,
            environment=env_name,
            local_dev=local_dev,
            local_base=local_base,
            agent_build=agent_build,
            extra_env_vars=extra_env_vars,
            hide_help=True,
            ignore_state=env_active,
        )

        env_data = storage.get(integration.name, env_name)
        metadata = env_data.read_metadata()
        try:
            env_vars = metadata.get(E2EMetadata.ENV_VARS, {})
            env_vars[AppEnvVars.REPO] = app.repo.name

            with EnvVars(env_vars):
                ctx.invoke(
                    test,
                    target_spec=f'{intg_name}:{env_name}',
                    pytest_args=pytest_args,
                    junit=junit,
                    hide_header=True,
                    e2e=True,
                )
        finally:
            ctx.invoke(stop, intg_name=intg_name, environment=env_name, ignore_state=env_active)


def is_e2e_environment(environment: Environment) -> bool:
    return environment.e2e_env


def uses_python_version(environment: Environment, python_filter: str | None) -> bool:
    return python_filter is None or environment.python == python_filter


def uses_platform(environment: Environment, platform: str) -> bool:
    return not environment.platforms or platform in environment.platforms


def is_selected_environment(environment: Environment, environment_name: str) -> bool:
    return environment.name == environment_name or environment_name == 'all'
