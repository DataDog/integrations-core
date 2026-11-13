# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

from ddev.testing.selection import TestCommand, parse_envs, parse_pytest_args

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command('test', cls=TestCommand)
@click.argument('intg_name', metavar='INTEGRATION')
@click.option('--envs', callback=parse_envs, help='Comma-separated names or matrix aliases, or all or active')
@click.option(
    '--pytest-args', default='', callback=parse_pytest_args, help='Pytest arguments, parsed with POSIX quoting'
)
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
        'The Agent build to use e.g. a Docker image like `registry.datadoghq.com/agent:latest`. You can '
        'also use the name of an Agent defined in the `agents` configuration section.'
    ),
)
@click.option(
    '-e',
    'extra_env_vars',
    multiple=True,
    help='Environment variables to pass to the Agent e.g. -e DD_URL=app.datadoghq.com -e DD_API_KEY=foobar',
)
@click.option('--recreate', '-r', is_flag=True, help='Recreate environments from scratch')
@click.option(
    '--ignore-teardown-errors',
    is_flag=True,
    help='Warn on automatic cleanup errors after testing; cleanup before recreating an environment stays fatal',
)
@click.option('--junit', is_flag=True, hidden=True)
@click.option('--python-filter', envvar='PYTHON_FILTER', hidden=True)
@click.option('--new-env', is_flag=True, hidden=True)
@click.pass_context
def test_command(
    ctx: click.Context,
    *,
    intg_name: str,
    envs: tuple[str, ...] | None,
    pytest_args: tuple[str, ...],
    local_dev: bool,
    local_base: bool,
    agent_build: str | None,
    extra_env_vars: tuple[str, ...],
    recreate: bool,
    ignore_teardown_errors: bool,
    junit: bool,
    python_filter: str | None,
    new_env: bool,
):
    """
    Test environments.

    This runs the end-to-end tests.

    With no --envs selection, test active environments, or all environments if none
    are active or when running in CI. Use --envs all to test every eligible environment.
    Use --envs active to test only environments that are already running.

    Testing active environments will not stop them after tests complete. Testing environments
    that are not running will start and stop them automatically.

    For example: ddev env test postgres --envs all --pytest-args='-m "not flaky"'

    See the testing documentation:

    \b
    https://datadoghq.dev/integrations-core/testing/
    """
    from ddev.cli.env.start import start
    from ddev.cli.env.stop import stop
    from ddev.cli.test import test
    from ddev.config.constants import AppEnvVars
    from ddev.e2e.config import EnvDataStorage
    from ddev.e2e.constants import E2EMetadata
    from ddev.testing.selection import e2e_pytest_args, load_environment_catalog, validate_target
    from ddev.utils.ci import running_in_ci
    from ddev.utils.structures import EnvVars

    app: Application = ctx.obj
    validate_target(intg_name, 'ddev env test')
    e2e_pytest_args(pytest_args)
    if envs and len(envs) > 1 and {'all', 'active'}.intersection(envs):
        raise click.UsageError('Use --envs all or --envs active alone, not with named environments.')
    integration = app.repo.integrations.get(intg_name)

    storage = EnvDataStorage(app.data_dir)
    active_envs = storage.get_environments(integration.name)

    if envs is None:
        envs = ('all',) if (not active_envs or running_in_ci()) else ('active',)

    catalog = load_environment_catalog(integration)
    if envs == ('active',):
        names = catalog.resolve(active_envs)
    elif envs == ('all',):
        names = list(catalog.environments)
    else:
        names = catalog.resolve(envs)
    env_names, excluded = catalog.select(names, mode='e2e_env', platform=app.platform.name, python_filter=python_filter)
    for name, reason in excluded.items():
        app.display_info(f'Excluded {integration.name}:{name} by {reason}.')
    if not env_names:
        app.display_info(f'No eligible environments selected for {integration.name}.')
        return

    app.display_header(integration.display_name)

    active = set(active_envs)
    for env_index, env_name in enumerate(env_names):
        env_active = env_name in active

        # If recreating and environment is already active, stop it first to get a fresh environment
        if recreate and env_active:
            ctx.invoke(stop, intg_name=intg_name, environment=env_name, ignore_state=False)

        ctx.invoke(
            start,
            intg_name=intg_name,
            environment=env_name,
            local_dev=local_dev,
            local_base=local_base,
            agent_build=agent_build,
            extra_env_vars=extra_env_vars,
            hide_help=True,
            ignore_state=env_active and not recreate,
        )

        env_data = storage.get(integration.name, env_name)
        metadata = env_data.read_metadata()
        test_succeeded = False
        try:
            env_vars = metadata.get(E2EMetadata.ENV_VARS, {})
            env_vars[AppEnvVars.REPO] = app.repo.name

            with EnvVars(env_vars):
                # Pass through DDEV_TEST_ENABLE_TRACING since ctx.invoke bypasses envvar parsing
                ddtrace_env = os.environ.get(AppEnvVars.TEST_ENABLE_TRACING, '')
                ddtrace = ddtrace_env.lower() in ('1', 'true', 'yes')
                ctx.invoke(
                    test,
                    target_spec=intg_name,
                    envs=(env_name,),
                    pytest_args=pytest_args,
                    recreate=recreate,
                    junit=junit,
                    hide_header=True,
                    e2e=True,
                    ddtrace=ddtrace,
                )
                test_succeeded = True
        finally:
            try:
                ctx.invoke(stop, intg_name=intg_name, environment=env_name, ignore_state=env_active)
            except Exception as error:
                if not ignore_teardown_errors:
                    raise
                # Opting in also accepts bugs in `stop` so cleanup cannot mask test results.
                warning = f'Automatic teardown failed for `{intg_name}:{env_name}` ({error!r}).'
                if test_succeeded and env_index < len(env_names) - 1:
                    warning += ' The next environment may fail to start if cleanup was incomplete.'
                app.display_warning(warning)
