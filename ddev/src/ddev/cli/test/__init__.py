# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application
    from ddev.integration.core import Integration
    from ddev.utils.fs import Path


def fix_coverage_report(report_file: Path):
    target_dir = report_file.parent.name
    report = report_file.read_bytes()

    # Make every target's `tests` directory path unique so they don't get combined in UI
    report = report.replace(b'"tests/', f'"{target_dir}/tests/'.encode('utf-8'))

    report_file.write_bytes(report)


epilog = '''
Examples

\b
List possible environments for postgres:
ddev test -l postgres

\b
Run only unit tests:
ddev test postgres:py3.11-9.6 -- -m unit

\b
Run specific test in multiple environments:
ddev test postgres:py3.11-9.6,py3.11-16.0 -- -k test_my_special_test
'''


@click.command(epilog=epilog)
@click.argument('target_spec', required=False)
@click.argument('pytest_args', nargs=-1)
@click.option('--lint', '-s', is_flag=True, help='Run only lint & style checks')
@click.option('--fmt', '-fs', is_flag=True, help='Run only the code formatter')
@click.option('--bench', '-b', is_flag=True, help='Run only benchmarks')
@click.option('--latest', is_flag=True, help='Only verify support of new product versions')
@click.option('--cov', '-c', 'coverage', is_flag=True, help='Measure code coverage')
@click.option('--compat', is_flag=True, help='Check compatibility with the minimum allowed Agent version')
@click.option('--ddtrace', is_flag=True, envvar='DDEV_TEST_ENABLE_TRACING', help='Enable tracing during test execution')
@click.option('--memray', is_flag=True, help='Measure memory usage during test execution')
@click.option('--recreate', '-r', is_flag=True, help='Recreate environments from scratch')
@click.option('--list', '-l', 'list_envs', is_flag=True, help='Show available test environments')
@click.option('--python-filter', envvar='PYTHON_FILTER', hidden=True)
@click.option('--junit', is_flag=True, hidden=True)
@click.option('--hide-header', is_flag=True, hidden=True)
@click.option('--e2e', is_flag=True, hidden=True)
@click.pass_obj
def test(
    app: Application,
    target_spec: str | None,
    pytest_args: tuple[str, ...],
    lint: bool,
    fmt: bool,
    bench: bool,
    latest: bool,
    coverage: bool,
    compat: bool,
    ddtrace: bool,
    memray: bool,
    recreate: bool,
    list_envs: bool,
    python_filter: str | None,
    junit: bool,
    hide_header: bool,
    e2e: bool,
):
    """
    Run unit and integration tests.

    Please see these docs for to pass TARGET_SPEC and PYTEST_ARGS:

    \b
    https://datadoghq.dev/integrations-core/testing/
    """
    import json
    import os
    import sys

    from ddev.repo.constants import PYTHON_VERSION
    from ddev.testing.constants import EndToEndEnvVars, TestEnvVars
    from ddev.testing.hatch import get_hatch_env_vars
    from ddev.utils.ci import running_in_ci

    if target_spec is None:
        target_spec = 'changed'

    target_name, _, environments = target_spec.partition(':')

    # target name -> target
    targets: dict[str, Integration] = {}
    if target_name == 'changed':
        for integration in app.repo.integrations.iter_changed():
            if integration.is_testable:
                targets[integration.name] = integration
    else:
        try:
            integration = app.repo.integrations.get(target_name)
        except OSError:
            app.abort(f'Unknown target: {target_name}')

        if integration.is_testable:
            targets[integration.name] = integration

    if not targets:
        app.abort('No testable targets found')

    if list_envs:
        multiple_targets = len(targets) > 1
        for target in targets.values():
            with target.path.as_cwd():
                if multiple_targets:
                    app.display_header(target.display_name)

                app.platform.check_command([sys.executable, '-m', 'hatch', 'env', 'show'])

        return

    in_ci = running_in_ci()

    # Also recreate the environment in the `compat` mode to make sure we are using the right base
    # check version.
    if compat:
        recreate = True

    global_env_vars: dict[str, str] = get_hatch_env_vars(verbosity=app.verbosity + 1)

    # Disable unnecessary output from Docker
    global_env_vars['DOCKER_CLI_HINTS'] = 'false'

    api_key = app.config.org.config.get('api_key')
    if api_key and not (lint or fmt):
        global_env_vars['DD_API_KEY'] = api_key

    # Only enable certain functionality when running standard tests
    standard_tests = not (lint or fmt or bench or latest)

    # Keep track of environments so that they can first be removed if requested
    chosen_environments = []

    base_command = [sys.executable, '-m', 'hatch', 'env', 'run']
    if environments and not standard_tests:
        app.abort('Cannot specify environments when using specific functionality like linting')
    elif lint:
        chosen_environments.append('lint')
        base_command.extend(('--env', 'lint', '--', 'all'))
    elif fmt:
        chosen_environments.append('lint')
        base_command.extend(('--env', 'lint', '--', 'fmt'))
    elif bench:
        filter_data = json.dumps({'benchmark-env': True})
        base_command.extend(('--filter', filter_data, '--', 'benchmark'))
    elif latest:
        filter_data = json.dumps({'latest-env': True})
        base_command.extend(('--filter', filter_data, '--', 'test', '--run-latest-metrics'))
    else:
        if environments:
            for env_name in environments.split(','):
                chosen_environments.append(env_name)
                base_command.extend(('--env', env_name))
        else:
            chosen_environments.append('default')
            base_command.append('--ignore-compat')

        if python_filter:
            filter_data = json.dumps({'python': python_filter})
            base_command.extend(('--filter', filter_data))

        base_command.extend(('--', 'test-cov' if coverage else 'test'))

        if app.verbosity <= 0:
            base_command.extend(('--tb', 'short'))

        if memray:
            if app.platform.windows:
                app.abort('Memory profiling with `memray` is not supported on Windows')

            base_command.append('--memray')

        if e2e:
            base_command.extend(('-m', 'e2e'))
            global_env_vars[EndToEndEnvVars.PARENT_PYTHON] = sys.executable

    app.display_debug(f'Targets: {", ".join(targets)}')
    for target in targets.values():
        if not hide_header:
            app.display_header(target.display_name)

        command = base_command.copy()
        env_vars = global_env_vars.copy()

        if standard_tests:
            if ddtrace and (target.is_integration or target.name == 'datadog_checks_base'):
                # TODO: remove this once we drop Python 2
                if app.platform.windows and (
                    (python_filter and python_filter != PYTHON_VERSION)
                    or not all(env_name.startswith('py3') for env_name in chosen_environments)
                ):
                    app.display_warning('Tracing is only supported on Python 3 on Windows')
                else:
                    command.append('--ddtrace')
                    env_vars['DDEV_TRACE_ENABLED'] = 'true'
                    env_vars['DD_PROFILING_ENABLED'] = 'true'
                    env_vars['DD_SERVICE'] = os.environ.get('DD_SERVICE', 'ddev-integrations')
                    env_vars['DD_ENV'] = os.environ.get('DD_ENV', 'ddev-integrations')

            if junit:
                # In order to handle multiple environments the report files must contain the environment name.
                # Hatch injects the `HATCH_ENV_ACTIVE` environment variable, see:
                # https://hatch.pypa.io/latest/plugins/environment/reference/#hatch.env.plugin.interface.EnvironmentInterface.get_env_vars
                command.extend(('--junit-xml', f'.junit/test-{"e2e" if e2e else "unit"}-$HATCH_ENV_ACTIVE.xml'))
                # Test results class prefix
                command.extend(('--junit-prefix', target.name))

            if (
                compat
                and target.is_package
                and target.is_integration
                and target.minimum_base_package_version is not None
            ):
                env_vars[TestEnvVars.BASE_PACKAGE_VERSION] = target.minimum_base_package_version

        command.extend(pytest_args)

        with target.path.as_cwd(env_vars=env_vars):
            app.display_debug(f'Command: {command}')

            if recreate:
                if bench or latest:
                    variable = 'benchmark-env' if bench else 'latest-env'
                    env_data = json.loads(
                        app.platform.check_command_output([sys.executable, '-m', 'hatch', 'env', 'show', '--json'])
                    )
                    for env_name, env_config in env_data.items():
                        if env_config.get(variable, False):
                            app.platform.check_command([sys.executable, '-m', 'hatch', 'env', 'remove', env_name])
                else:
                    for env_name in chosen_environments:
                        app.platform.check_command([sys.executable, '-m', 'hatch', 'env', 'remove', env_name])

            app.platform.check_command(command)
            if standard_tests and coverage:
                app.display_header('Coverage report')
                app.platform.check_command([sys.executable, '-m', 'coverage', 'report', '--rcfile=../.coveragerc'])

                if in_ci:
                    app.platform.check_command(
                        [sys.executable, '-m', 'coverage', 'xml', '-i', '--rcfile=../.coveragerc']
                    )
                    fix_coverage_report(target.path / 'coverage.xml')
                else:
                    (target.path / '.coverage').remove()

            if compat:
                # We destroy the environment since we edited it
                for env_name in chosen_environments:
                    app.platform.check_command([sys.executable, '-m', 'hatch', 'env', 'remove', env_name])
