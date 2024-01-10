# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest

from datadog_checks.dev import EnvVars, run_command
from datadog_checks.dev._env import E2E_PREFIX, TESTING_PLUGIN
from datadog_checks.dev.fs import chdir, remove_path

HERE = os.path.dirname(os.path.abspath(__file__))
CORE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HERE))))


@pytest.mark.skipif(sys.version_info[0] == 2, reason='Not supported on Python 2')
@pytest.mark.parametrize(
    'integration_type, installable', [('check', True), ('jmx', True), ('tile', False), ('logs', False)]
)
def test_new_check_test(integration_type, installable):
    check_path = os.path.join(CORE_ROOT, 'my_check')

    try:
        run_command(
            [
                sys.executable,
                '-m',
                'datadog_checks.dev',
                'create',
                '--type',
                integration_type,
                '--quiet',
                '--location',
                CORE_ROOT,
                'My Check',
            ],
            capture=True,
            check=True,
        )
        if installable:
            run_command([sys.executable, '-m', 'pip', 'install', check_path], capture=True, check=True)

            with chdir(check_path):
                ignored_env_vars = [TESTING_PLUGIN, 'PYTEST_ADDOPTS']
                ignored_env_vars.extend(ev for ev in os.environ if ev.startswith(E2E_PREFIX))

                with EnvVars(ignore=ignored_env_vars):
                    run_command([sys.executable, '-m', 'pytest'], capture=True, check=True)

            # We only run style checks on the generated integration. Running the entire test suite would result in tox
            # creating Python environments, which would be too slow with little benefits.
            result = run_command(
                [sys.executable, '-m', 'datadog_checks.dev', 'test', '-s', 'my_check'], capture=True, check=True
            )
            # `ddev test` will not fail if the provided check name doesn't correspond to an existing integration.
            # Instead, it will log a message. So we test for that message to verify style checks ran at all.
            assert 'Nothing to test!' not in result.stdout

            result = run_command(
                [sys.executable, '-m', 'pip', 'uninstall', '-y', 'datadog-my-check'], capture=True, check=True
            )
            # `pip uninstall` is idempotent, so it will not fail if `check_package_name` is incorrect (i.e. the package
            # could not be found). Instead, it will log a warning, so we test for that warning to verify the package was
            # successfully uninstalled.
            # See: https://github.com/pypa/pip/issues/3016
            assert 'WARNING: Skipping' not in result.stdout
    finally:
        remove_path(check_path)
