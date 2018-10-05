# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .constants import TESTABLE_FILE_EXTENSIONS, get_root
from .git import files_changed
from .utils import get_testable_checks
from ..subprocess import run_command
from ..utils import chdir, path_join

STYLE_ENVS = {
    'flake8',
}


def get_tox_envs(checks, style=False, benchmark=False, every=False, changed_only=False, sort=False):
    testable_checks = get_testable_checks()
    # Run `get_changed_checks` at most once because git calls are costly
    changed_checks = get_changed_checks() if not checks or changed_only else None

    if not checks:
        checks = sorted(testable_checks & changed_checks)

    checks_seen = set()
    for check in checks:
        check, _, envs_selected = check.partition(':')

        if (
            check in checks_seen
            or check not in testable_checks
            or (changed_only and check not in changed_checks)
        ):
            continue
        else:
            checks_seen.add(check)

        envs_selected = envs_selected.split(',') if envs_selected else []
        envs_available = get_available_tox_envs(check, sort=sort)

        if style:
            envs_selected[:] = [
                e for e in envs_available
                if e in STYLE_ENVS
            ]
        elif benchmark:
            envs_selected[:] = [
                e for e in envs_available
                if 'bench' in e
            ]
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
                    e for e in envs_available
                    if 'bench' not in e
                ]

        yield check, envs_selected


def get_available_tox_envs(check, sort=False):
    with chdir(path_join(get_root(), check)):
        env_list = run_command('tox --listenvs', capture='out').stdout

    env_list = [e.strip() for e in env_list.splitlines()]

    if sort:
        env_list.sort()

        # Put benchmarks after regular test envs
        benchmark_envs = []

        for e in env_list:
            if 'bench' in e:
                benchmark_envs.append(e)

        for e in benchmark_envs:
            env_list.remove(e)
            env_list.append(e)

        # Put style checks at the end always
        for style_type in STYLE_ENVS:
            try:
                env_list.remove(style_type)
                env_list.append(style_type)
            except ValueError:
                pass

    return env_list


def coverage_sources(check):
    # All paths are relative to each tox.ini
    if check == 'datadog_checks_base':
        package_path = 'datadog_checks/base'
    elif check == 'datadog_checks_dev':
        package_path = 'datadog_checks/dev'
    else:
        package_path = 'datadog_checks/{}'.format(check)

    return package_path, 'tests'


def pytest_coverage_sources(*checks):
    return ' '.join(
        ' '.join(
            '--cov={}'.format(source) for source in coverage_sources(check)
        )
        for check in checks
    )


def testable_files(files):
    """
    Given a list of files, return the files that have an extension listed in TESTABLE_FILE_EXTENSIONS
    """
    return [f for f in files if f.endswith(TESTABLE_FILE_EXTENSIONS)]


def get_changed_checks():
    # Get files that changed compared to `master`
    changed_files = files_changed()

    # Filter by files that can influence the testing of a check
    changed_files[:] = testable_files(changed_files)

    return {line.split('/')[0] for line in changed_files}
