# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re
from fnmatch import fnmatch

from ..fs import chdir, file_exists, path_join, read_file_binary, write_file_binary
from ..structures import EnvVars
from ..subprocess import run_command
from .commands.console import abort, echo_debug, echo_info, echo_success
from .constants import NON_TESTABLE_FILES, TESTABLE_FILE_PATTERNS, get_root
from .dependencies import read_check_base_dependencies
from .e2e import get_active_checks, get_configured_envs
from .git import files_changed
from .utils import (
    complete_set_root,
    get_hatch_file,
    get_metric_sources,
    get_testable_checks,
    get_valid_checks,
    get_valid_integrations,
)

STYLE_CHECK_ENVS = {'flake8', 'style'}
STYLE_ENVS = {'flake8', 'style', 'format_style'}
PYTHON_MAJOR_PATTERN = r'py(\d)'


def complete_envs(ctx, args, incomplete):
    complete_set_root(args)
    return sorted(e for e in get_available_tox_envs(args[-1], e2e_only=True) if e.startswith(incomplete))


# this test makes more sense under tooling/utils, but that causes circular import
def complete_active_checks(ctx, args, incomplete):
    complete_set_root(args)
    return [k for k in get_active_checks() if k.startswith(incomplete)]


def complete_configured_envs(ctx, args, incomplete):
    complete_set_root(args)
    return [e for e in get_configured_envs(args[-1]) if e.startswith(incomplete)]


def get_test_envs(
    checks,
    style=False,
    format_style=False,
    benchmark=False,
    every=False,
    changed_only=False,
    sort=False,
    e2e_tests_only=False,
    latest=False,
):
    testable_checks = get_testable_checks()
    # Run `get_changed_checks` at most once because git calls are costly
    changed_checks = get_changed_checks() if not checks or changed_only else None

    if not checks:
        checks = sorted(testable_checks & changed_checks)

    checks_seen = set()

    env_filter = os.environ.get("TOX_SKIP_ENV")
    env_filter_re = re.compile(env_filter) if env_filter is not None else None

    for check in checks:
        check, _, envs_selected = check.partition(':')
        echo_debug(f"Getting tox envs for `{check}:{envs_selected}`")

        if check in checks_seen:
            echo_debug(f"`{check}` already evaluated, skipping")
            continue
        elif check not in testable_checks:
            echo_debug(f"`{check}` is not testable, skipping")
            continue
        elif changed_only and check not in changed_checks:
            echo_debug(f"`{check}` does not have changes, skipping")
            continue
        else:
            checks_seen.add(check)

        envs_selected = envs_selected.split(',') if envs_selected else []
        if file_exists(get_hatch_file(check)):
            select_hatch_envs(
                check,
                envs_selected,
                style,
                format_style,
                benchmark,
                every,
                sort,
                e2e_tests_only,
                latest,
                env_filter_re,
            )
        else:
            select_tox_envs(
                check,
                envs_selected,
                style,
                format_style,
                benchmark,
                every,
                sort,
                e2e_tests_only,
                latest,
                env_filter_re,
            )

        echo_debug(f"Selected environments: {envs_selected}")
        yield check, envs_selected


def get_available_envs(check, sort=False, e2e_only=False, e2e_tests_only=False):
    if file_exists(get_hatch_file(check)):
        return get_available_hatch_envs(check, sort=sort, e2e_only=e2e_only, e2e_tests_only=e2e_tests_only)
    else:
        return list(get_available_tox_envs(check, sort=sort, e2e_only=e2e_only, e2e_tests_only=e2e_tests_only))


def get_available_tox_envs(check, sort=False, e2e_only=False, e2e_tests_only=False):
    if e2e_tests_only:
        tox_command = 'tox --listenvs-all -v'
    elif e2e_only:
        tox_command = 'tox --listenvs-all'
    else:
        tox_command = 'tox --listenvs'

    with chdir(path_join(get_root(), check)):
        output = run_command(tox_command, capture='out')

    if output.code != 0:
        abort(f'STDOUT: {output.stdout}\nSTDERR: {output.stderr}')

    env_list = [e.strip() for e in output.stdout.splitlines()]

    if e2e_tests_only:
        envs = []
        for line in env_list:
            if '->' in line:
                env, _, description = line.partition('->')
                if 'e2e ready' in description.lower():
                    envs.append(env.strip())

        return envs

    if e2e_only:
        sort = True

    if sort:
        env_list.sort()

        # Put benchmarks after regular test envs
        benchmark_envs = []

        for e in env_list:
            if 'bench' in e:
                benchmark_envs.append(e)

        for e in benchmark_envs:
            env_list.remove(e)
            if not e2e_only:
                env_list.append(e)

        # Put style checks at the end always
        for style_type in STYLE_ENVS:
            try:
                env_list.remove(style_type)
                if not e2e_only:
                    env_list.append(style_type)
            except ValueError:
                pass

        if e2e_only:
            # No need for unit tests as they wouldn't set up a real environment
            unit_envs = []

            for e in env_list:
                if e.endswith('unit'):
                    unit_envs.append(e)

            for e in unit_envs:
                env_list.remove(e)

    return env_list


def select_tox_envs(
    check,
    envs_selected,
    style,
    format_style,
    benchmark,
    every,
    sort,
    e2e_tests_only,
    latest,
    env_filter_re,
):
    envs_available = get_available_tox_envs(check, sort=sort, e2e_only=latest, e2e_tests_only=e2e_tests_only)

    if format_style:
        envs_selected[:] = [e for e in envs_available if 'format_style' in e]
    elif style:
        envs_selected[:] = [e for e in envs_available if e in STYLE_CHECK_ENVS]
    elif benchmark:
        envs_selected[:] = [e for e in envs_available if 'bench' in e]
    elif latest:
        envs_selected[:] = [e for e in envs_available if e == 'latest']
    else:
        if every:
            envs_selected[:] = envs_available
        elif envs_selected:
            available = set(envs_selected) & set(envs_available)
            selected = []

            # Retain order and remove duplicates
            for e in envs_selected:
                # TODO: support globs or regex
                if e in available:
                    selected.append(e)
                    available.remove(e)

            envs_selected[:] = selected
        else:
            envs_selected[:] = [
                e for e in envs_available if 'bench' not in e and 'format_style' not in e and e != 'latest'
            ]

    if env_filter_re:
        envs_selected[:] = [e for e in envs_selected if not env_filter_re.match(e)]


def get_hatch_env_data(check):
    with chdir(path_join(get_root(), check), env_vars=EnvVars({'NO_COLOR': '1'})):
        return json.loads(run_command(['hatch', 'env', 'show', '--json'], capture='out').stdout)


def get_available_hatch_envs(check, sort=False, e2e_only=False, e2e_tests_only=False):
    environments = get_hatch_env_data(check)
    if e2e_only:
        return {env_name: config for env_name, config in environments.items() if config.get('e2e-env', False)}
    elif e2e_tests_only:
        return {
            env_name: config
            for env_name, config in environments.items()
            if config.get('e2e-env', False) and config.get('test-env', False)
        }
    else:
        return environments


def select_hatch_envs(
    check,
    envs_selected,
    style,
    format_style,
    benchmark,
    every,
    sort,
    e2e_tests_only,
    latest,
    env_filter_re,
):
    if style or format_style:
        envs_selected[:] = ['lint']
    elif benchmark:
        envs_selected[:] = [
            env_name
            for env_name, config in get_available_hatch_envs(check, e2e_tests_only=e2e_tests_only).items()
            if config.get('benchmark-env', False)
        ]
    elif latest:
        envs_selected[:] = [
            env_name
            for env_name, config in get_available_hatch_envs(check, e2e_tests_only=e2e_tests_only).items()
            if env_name == 'latest' or config.get('latest-env', False)
        ]
    elif not envs_selected:
        envs_selected[:] = [
            env_name
            for env_name, config in get_available_hatch_envs(check, e2e_tests_only=e2e_tests_only).items()
            if config.get('test-env', False)
        ]
        if not e2e_tests_only:
            envs_selected.append('lint')

    if env_filter_re:
        envs_selected[:] = [e for e in envs_selected if not env_filter_re.match(e)]


def display_check_envs(checks, changed_only):
    tox_checks = []
    hatch_checks = []
    for check in checks:
        if file_exists(get_hatch_file(check)):
            hatch_checks.append(check)
        else:
            tox_checks.append(check)

    if tox_checks:
        check_envs = get_test_envs(checks, every=True, sort=True, changed_only=changed_only)
        for check, envs in check_envs:
            echo_success(f'`{check}`:')
            for e in envs:
                echo_info(f'    {e}')

    if hatch_checks:
        for check in checks:
            with chdir(path_join(get_root(), check)):
                run_command(['hatch', 'env', 'show'])


def prepare_test_commands(
    check,
    env_names,
    env_vars,
    force_base_min,
    force_base_unpinned,
    force_env_rebuild,
    verbose,
    style,
    format_style,
    benchmark,
):
    if file_exists(get_hatch_file(check)):
        return prepare_hatch_test_commands(
            check,
            env_names,
            env_vars,
            force_base_min,
            force_base_unpinned,
            force_env_rebuild,
            verbose,
            style,
            format_style,
            benchmark,
        )
    else:
        return prepare_tox_test_commands(
            check,
            env_names,
            env_vars,
            force_base_min,
            force_base_unpinned,
            force_env_rebuild,
            verbose,
            style,
            format_style,
            benchmark,
        )


def prepare_tox_test_commands(
    check,
    env_names,
    env_vars,
    force_base_min,
    force_base_unpinned,
    force_env_rebuild,
    verbose,
    style,
    format_style,
    benchmark,
):
    command = [
        'tox',
        # so users won't get failures for our possibly strict CI requirements
        '--skip-missing-interpreters',
        # so coverage tracks the real locations instead of .tox virtual envs
        '--develop',
        # comma-separated list of environments
        '-e {}'.format(','.join(env_names)),
    ]

    base_or_dev = check.startswith('datadog_checks_')
    if force_base_min and not base_or_dev:
        check_base_dependencies, errors = read_check_base_dependencies(check)
        if errors:
            abort(f'\nError collecting base package dependencies: {errors}')

        spec = check_base_dependencies[check]
        if spec is None:
            abort(f'\nFailed to determine minimum version of package `datadog_checks_base`: {spec}')

        version = spec.split('>=')[-1]

        env_vars['TOX_FORCE_INSTALL'] = f'datadog_checks_base[deps]=={version}'
        env_vars['BASE_PACKAGE_FORCE_VERSION'] = str(version)
    elif force_base_unpinned and not base_or_dev:
        env_vars['TOX_FORCE_UNPINNED'] = 'datadog_checks_base'
        env_vars['BASE_PACKAGE_FORCE_UNPINNED'] = 'true'
    elif (force_base_min or force_base_unpinned) and base_or_dev:
        echo_info(f'Skipping forcing base dependency for check {check}')

    if force_env_rebuild:
        command.append('--recreate')

    if verbose:
        command.append('-' + 'v' * verbose)

    return [command]


def prepare_hatch_test_commands(
    check,
    env_names,
    env_vars,
    force_base_min,
    force_base_unpinned,
    force_env_rebuild,
    verbose,
    style,
    format_style,
    benchmark,
):
    commands = []
    if 'lint' in env_names:
        env_names.remove('lint')
        commands.append(['hatch', 'env', 'run', '--env', 'lint', '--', 'fmt' if format_style else 'all'])

    if env_names:
        command = ['hatch', '-v', 'env', 'run', '--ignore-compat']
        for env_name in env_names:
            command.append('--env')
            command.append(env_name)

        command.append('--')
        command.append('benchmark' if benchmark else 'test')

        commands.insert(0, command)

    base_or_dev = check.startswith('datadog_checks_') or check == 'ddev'
    if force_base_min and not base_or_dev:
        check_base_dependencies, errors = read_check_base_dependencies(check)
        if errors:
            abort(f'\nError collecting base package dependencies: {errors}')

        spec = check_base_dependencies[check]
        if spec is None:
            abort(f'\nFailed to determine minimum version of package `datadog_checks_base`: {spec}')

        version = spec.split('>=')[-1]

        env_vars['BASE_PACKAGE_FORCE_VERSION'] = str(version)
    elif force_base_unpinned and not base_or_dev:
        env_vars['BASE_PACKAGE_FORCE_UNPINNED'] = 'true'
    elif (force_base_min or force_base_unpinned) and base_or_dev:
        echo_info(f'Skipping forcing base dependency for check {check}')

    if force_env_rebuild:
        commands.insert(0, ['hatch', 'env', 'prune'])

    if verbose:
        env_vars['HATCH_VERBOSE'] = str(verbose)

    return commands


def coverage_sources(check):
    # All paths are relative to each tox.ini
    if check == 'datadog_checks_base':
        package_path = 'datadog_checks/base'
    elif check == 'datadog_checks_dev':
        package_path = 'datadog_checks/dev'
    elif check == 'datadog_checks_downloader':
        package_path = 'datadog_checks/downloader'
    else:
        package_path = f'datadog_checks/{check}'

    return package_path, 'tests'


def fix_coverage_report(check, report_file):
    report = read_file_binary(report_file)

    # Make every check's `tests` directory path unique so they don't get combined in UI
    report = report.replace(b'"tests/', f'"{check}/tests/'.encode('utf-8'))

    write_file_binary(report_file, report)


def construct_pytest_options(
    check,
    verbose=0,
    color=None,
    enter_pdb=False,
    debug=False,
    bench=False,
    latest=False,
    coverage=False,
    junit=False,
    marker='',
    test_filter='',
    pytest_args='',
    e2e=False,
    ddtrace=False,
):
    # Prevent no verbosity
    pytest_options = f'--verbosity={verbose or 1}'

    if not verbose:
        pytest_options += ' --tb=short'

    if color is not None:
        pytest_options += ' --color=yes' if color else ' --color=no'

    if enter_pdb:
        # Drop to PDB on first failure, then end test session
        pytest_options += ' --pdb -x'

    if debug:
        pytest_options += ' --log-level=debug -s'

    if bench:
        pytest_options += ' --benchmark-only --benchmark-cprofile=tottime'
    else:
        pytest_options += ' --benchmark-skip'

    if latest:
        pytest_options += ' --run-latest-metrics'

    if ddtrace:
        pytest_options += ' --ddtrace'

    if junit:
        test_group = 'e2e' if e2e else 'unit'
        pytest_options += (
            # junit report file must contain the env name to handle multiple envs
            # $HATCH_ENV_ACTIVE is a Hatch injected variable
            # See https://hatch.pypa.io/latest/plugins/environment/reference/#hatch.env.plugin.interface.EnvironmentInterface.get_env_vars  # noqa
            # $TOX_ENV_NAME is a tox injected variable
            # See https://tox.readthedocs.io/en/latest/config.html#injected-environment-variables
            f' --junit-xml=.junit/test-{test_group}-$HATCH_ENV_ACTIVE$TOX_ENV_NAME.xml'
            # Junit test results class prefix
            f' --junit-prefix={check}'
        )

    if coverage:
        pytest_options += (
            # Located at the root of each repo
            ' --cov-config=../.coveragerc'
            # Use the same .coverage file to aggregate results
            ' --cov-append'
            # Show no coverage report until the end
            ' --cov-report='
            # This will be formatted to the appropriate coverage paths for each package
            ' {}'
        )

    if marker:
        pytest_options += f' -m "{marker}"'

    if test_filter:
        pytest_options += f' -k "{test_filter}"'

    if pytest_args:
        pytest_options += f' {pytest_args}'

    return pytest_options


def pytest_coverage_sources(*checks):
    return ' '.join(' '.join(f'--cov={source}' for source in coverage_sources(check)) for check in checks)


def testable_files(files):
    """
    Given a list of files, return only those that match any of the TESTABLE_FILE_PATTERNS and are
    not blacklisted by NON_TESTABLE_FILES (metrics.yaml, auto_conf.yaml)
    """
    filtered = []

    for f in files:
        if f.endswith(NON_TESTABLE_FILES):
            continue

        match = any(fnmatch(f, pattern) for pattern in TESTABLE_FILE_PATTERNS)
        if match:
            filtered.append(f)

    return filtered


def get_changed_checks():
    """Return set of check names that have changes in testable code."""

    # Get files that changed compared to `master`
    changed_files = files_changed()

    # Filter by files that can influence the testing of a check
    changed_files[:] = testable_files(changed_files)

    return {line.split('/')[0] for line in changed_files}


def get_changed_directories(include_uncommitted=True):
    """Return set of check names that have any changes at all."""
    changed_files = files_changed(include_uncommitted)

    return {line.split('/')[0] for line in changed_files}


def get_active_env_python_version(env):
    match = re.match(PYTHON_MAJOR_PATTERN, env)
    if match:
        return int(match.group(1))


def process_checks_option(check, source=None, validate=False, extend_changed=False):
    # provide common function for determining which check to run validations against
    # `source` determines which method for gathering valid check, default will use `get_valid_checks`
    # `validate` gets applied for specific check names, ensuring the check is included in the default
    #   collection specified by `source`.  If not, it returns an empty list.

    if source is None or source == 'valid_checks':
        get_valid = get_valid_checks
    elif source == 'metrics':
        get_valid = get_metric_sources
    elif source == 'testable':
        get_valid = get_testable_checks
    elif source == 'integrations':
        get_valid = get_valid_integrations
    else:
        get_valid = get_valid_integrations

    if check is None or check.lower() == 'all':
        choice = sorted(get_valid())
    elif check.lower() == 'changed':
        choice = sorted(get_changed_directories(include_uncommitted=False) & get_valid())
        if extend_changed and ('datadog_checks_dev' in choice or 'datadog_checks_base' in choice):
            choice = sorted(get_valid())
    else:
        if validate:
            choice = [check] if check in get_valid() else []
        else:
            choice = [check]

    return choice
