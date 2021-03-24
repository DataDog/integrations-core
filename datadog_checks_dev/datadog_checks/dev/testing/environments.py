# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

from datadog_checks.dev.testing.utils import get_changed_checks
from datadog_checks.dev.tooling.commands.console import echo_debug, abort
from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.utils import get_testable_checks

from ..subprocess import run_command
from ..utils import chdir, path_join


STYLE_CHECK_ENVS = {'flake8', 'style'}
STYLE_ENVS = {'flake8', 'style', 'format_style'}


def get_tox_envs(
    checks,
    style=False,
    format_style=False,
    benchmark=False,
    every=False,
    changed_only=False,
    sort=False,
    e2e_tests_only=False,
):
    testable_checks = get_testable_checks()
    # Run `get_changed_checks` at most once because git calls are costly
    changed_checks = get_changed_checks() if not checks or changed_only else None

    if not checks:
        checks = sorted(testable_checks & changed_checks)

    checks_seen = set()

    tox_env_filter = os.environ.get("TOX_SKIP_ENV")
    tox_env_filter_re = re.compile(tox_env_filter) if tox_env_filter is not None else None

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
        envs_available = get_available_tox_envs(check, sort=sort, e2e_tests_only=e2e_tests_only)

        if format_style:
            envs_selected[:] = [e for e in envs_available if 'format_style' in e]
        elif style:
            envs_selected[:] = [e for e in envs_available if e in STYLE_CHECK_ENVS]
        elif benchmark:
            envs_selected[:] = [e for e in envs_available if 'bench' in e]
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
                envs_selected[:] = [e for e in envs_available if 'bench' not in e and 'format_style' not in e]

        if tox_env_filter_re:
            envs_selected[:] = [e for e in envs_selected if not tox_env_filter_re.match(e)]

        echo_debug(f"Selected environments: {envs_selected}")
        yield check, envs_selected


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

